import hashlib
import json
import re
import uuid

import memcache
from uhashring import HashRing
import util 

MAX_KEY_LENGTH = 64
DEAD_RETRY = 5

def _parse_aliases(servers):
    parsed_servers = []
    parsed_aliases = []

    for server in servers:
        alias_match = re.search('\\((.*)\\)\\s?$', server)
        if alias_match:
            server = server[:alias_match.start()]
            alias = alias_match.group(1)
        else:
            alias = server

        parsed_servers.append(server)
        parsed_aliases.append(alias)

    return (parsed_servers, parsed_aliases)


class MemcacheRingWithServerAlias(memcache.Client):
    """Extends python-memcache so it uses consistent hashing to distribute the keys.

    It supports server aliases, so that consistent hashing returns the same key mapping
    in all environments, regardless of DNS or tunnel configurations.

    Key / node assignments are based on the alias, not the real URL used to connect
    to the node. In order for all the services to use the same key / node assignments
    for memcache, we ensure the aliases always match in all environments, even if the
    URLs used to reach the servers are different.

    The server / alias pairs are specified in the format
    `real.example.com:12345(alias.example.com:11211)`

    If an alias is not specified, it is assumed to be the same as the server URL, so
    the following is also valid:
    `memcached01.example.com:11211`.

    The class is a modified version of :class:`hash_ring.memcache_ring.MemcacheRing`.
    """

    def __init__(self, servers, *k, **kw):
        servers, aliases = _parse_aliases(servers)

        memcache.Client.__init__(self, servers, *k, **kw)

        self.server_mapping = {}
        nodes = {}
        for server_alias, server_obj in zip(aliases, self.servers):
            self.server_mapping[server_alias] = server_obj
            nodes[server_alias] = {
                "hostname": server_obj.ip,
                "port": server_obj.port,
                "weight": server_obj.weight,
                "instance": server_obj,
            }

        self.hash_ring = HashRing(nodes, hash_fn="ketama")

    def _get_server(self, key):
        if type(key) == tuple:
            return memcache.Client._get_server(key)

        for i in range(self._SERVER_RETRIES):
            for node in self.hash_ring.range(key):
                server_obj = node["instance"]
                if server_obj.connect():
                    return server_obj, key

        return None, None


class MoxMemcacheClient(MemcacheRingWithServerAlias):
    # Datadog APM attributes
    _service_name = "mox-memcache"
    _resource_group = "memcache"
    _trace_operation_name = "memcache.operation"

    def __init__(self, server_list):
        self.min_compress_len = 1024

        # NOTE(kshep): MemcacheRing needs a bare list of servers, so trip off the weights
        #              That is, rather than [('mem2', 1), ('dal05mem2', 1)]
        #              we just want ['mem2', 'dal05mem2']
        #
        # TODO(kshep): Refactor this so we can actually specify memcached server weights
        mr_server_list = list(zip(*server_list)[0])
        super(MoxMemcacheClient, self).__init__(mr_server_list,
                                                server_max_key_length=MAX_KEY_LENGTH,
                                                dead_retry=DEAD_RETRY)

    def _hash_key(self, key, key_prefix=''):
        # always hash keys so we don't have control characters in them
        key = hashlib.sha256(key_prefix + key).hexdigest()
        return key

    def _get(self, cmd, key):
        key = self._hash_key(key)
        return super(MoxMemcacheClient, self)._get(cmd, key)

    def _set(self, cmd, key, val, time, min_compress_len=0, noreply=False):
        key = self._hash_key(key)
        min_compress_len = min_compress_len or self.min_compress_len
        return super(MoxMemcacheClient, self)._set(
            cmd, key, val, time, min_compress_len=min_compress_len, noreply=noreply)

    def get(self, key, *args, **kwargs):
        return super(MoxMemcacheClient, self).get(key, *args, **kwargs)

    def set(self, key, *args, **kwargs):
        return super(MoxMemcacheClient, self).set(key, *args, **kwargs)

    def get_multi(self, keys, key_prefix=''):

        key_mapping = {}
        new_keys = []

        for orig_key in keys:
            new_key = self._hash_key(orig_key, key_prefix=key_prefix)
            new_keys.append(new_key)

            key_mapping[new_key] = orig_key

        try:
            result = super(MoxMemcacheClient, self).get_multi(new_keys, key_prefix=key_prefix)
        except memcache._ConnectionDeadError:
            # log.warning('Memcache connection died, retrying')
            self.forget_dead_hosts()
            try:
                result = super(MoxMemcacheClient, self).get_multi(new_keys, key_prefix=key_prefix)
            except memcache._ConnectionDeadError:
                # log.error('Could not use memcache connection, returning empty list')
                result = {}

        return {key_mapping[orig_key]: value for orig_key, value in result.items()}

    def set_multi(self, mapping, time=0, key_prefix='', min_compress_len=0, noreply=False):
        key_mapping = {}
        new_mapping = {}

        for orig_key, value in mapping.items():
            new_key = self._hash_key(orig_key, key_prefix=key_prefix)
            new_mapping[new_key] = value
            key_mapping[new_key] = orig_key
        try:
            result = super(MoxMemcacheClient, self).set_multi(new_mapping,
                                                            time=time,
                                                            key_prefix=key_prefix,
                                                            min_compress_len=min_compress_len,
                                                            noreply=noreply)
        except memcache._ConnectionDeadError:
            # log.warning('Memcache connection died, retrying')
            self.forget_dead_hosts()
            try:
                result = super(MoxMemcacheClient, self).set_multi(new_mapping,
                                                                time=time,
                                                                key_prefix=key_prefix,
                                                                min_compress_len=min_compress_len,
                                                                noreply=noreply)
            except memcache._ConnectionDeadError:
                # log.error('Could not use memcache connection, returning empty list')
                result = []

        return [key_mapping[orig_key] for orig_key in result]

    def delete(self, key, time=0, noreply=False):
        key = self._hash_key(key)
        return super(MoxMemcacheClient, self).delete(key, time=time, noreply=noreply)

    def delete_multi(self, keys, time=0, key_prefix='', noreply=False):
        keys = map(self._hash_key, keys)
        return super(MoxMemcacheClient, self).delete_multi(keys, time=time, key_prefix=key_prefix, noreply=noreply)


def seed_memcached_with_mox(cache_client, num_values):
    data = {}
    for i in range(num_values): 
        key = str(uuid.uuid4()) + '-uhashring'
        data[key] = i
    cache_client.set_multi(data)
    with open(util.MOX_SEEDED_MC_DUMP_FILE % num_values, 'w') as hr_data:
        json.dump(data, hr_data)

if __name__ == "__main__": 
    print("\nSearching with mox memcached client")
    client = MoxMemcacheClient(util.MEMCACHED_SERVERS_FMT)
    util.run_and_report(client)
    print("----------\n")