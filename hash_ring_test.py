import hash_ring 
import memcache
import hashlib
import json
import uuid

import util


MAX_KEY_LENGTH = 64
DEAD_RETRY = 5
SERVER_GROUPS = {'default', 'raw'}
CACHE_MISS = '<cache-miss>'


class MemcacheClient(hash_ring.MemcacheRing):
    # Datadog APM attributes
    _service_name = "mox-memcache"
    _resource_group = "memcache"
    _trace_operation_name = "memcache.operation"

    def __init__(self, server_list):
        self.min_compress_len = 1024

        mr_server_list = list(zip(*server_list)[0])
        super(MemcacheClient, self).__init__(mr_server_list,
                                                server_max_key_length=MAX_KEY_LENGTH,
                                                dead_retry=DEAD_RETRY)

    def _hash_key(self, key, key_prefix=''):
        # always hash keys so we don't have control characters in them
        key = hashlib.sha256(key_prefix + key).hexdigest()
        return key

    def _get(self, cmd, key):
        key = self._hash_key(key)
        return super(MemcacheClient, self)._get(cmd, key)

    def _set(self, cmd, key, val, time, min_compress_len=0, noreply=False):
        key = self._hash_key(key)
        min_compress_len = min_compress_len or self.min_compress_len
        return super(MemcacheClient, self)._set(
            cmd, key, val, time, min_compress_len=min_compress_len, noreply=noreply)

    def get(self, key, *args, **kwargs):
        return super(MemcacheClient, self).get(key, *args, **kwargs)

    def set(self, key, *args, **kwargs):
        return super(MemcacheClient, self).set(key, *args, **kwargs)

    def get_multi(self, keys, key_prefix=''):
        key_mapping = {}
        new_keys = []

        for orig_key in keys:
            new_key = self._hash_key(orig_key, key_prefix=key_prefix)
            new_keys.append(new_key)

            key_mapping[new_key] = orig_key

        try:
            result = super(MemcacheClient, self).get_multi(new_keys, key_prefix=key_prefix)
        except memcache._ConnectionDeadError:
            self.forget_dead_hosts()
            try:
                result = super(MemcacheClient, self).get_multi(new_keys, key_prefix=key_prefix)
            except memcache._ConnectionDeadError:
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
            result = super(MemcacheClient, self).set_multi(new_mapping,
                                                            time=time,
                                                            key_prefix=key_prefix,
                                                            min_compress_len=min_compress_len,
                                                            noreply=noreply)
        except memcache._ConnectionDeadError:
            self.forget_dead_hosts()
            try:
                result = super(MemcacheClient, self).set_multi(new_mapping,
                                                                time=time,
                                                                key_prefix=key_prefix,
                                                                min_compress_len=min_compress_len,
                                                                noreply=noreply)
            except memcache._ConnectionDeadError:
                result = []

        return [key_mapping[orig_key] for orig_key in result]

    def delete(self, key, time=0, noreply=False):
        key = self._hash_key(key)
        return super(MemcacheClient, self).delete(key, time=time, noreply=noreply)

    def delete_multi(self, keys, time=0, key_prefix='', noreply=False):
        keys = map(self._hash_key, keys)
        return super(MemcacheClient, self).delete_multi(keys, time=time, key_prefix=key_prefix, noreply=noreply)

def seed_memcached_with_hashring(cache_client, num_values):
    data = {}
    for i in range(num_values): 
        key = str(uuid.uuid4()) + '-hashring'
        data[key] = i
    cache_client.set_multi(data)
    with open(util.HASHRING_SEEDED_MC_DUMP_FILE % num_values, 'w') as hr_data:
        json.dump(data, hr_data)


if __name__ == "__main__": 
    print("\nSearching with hash_ring memcached client")
    client = MemcacheClient(util.MEMCACHED_SERVERS_FMT)
    util.run_and_report(client)
    print("----------\n")

