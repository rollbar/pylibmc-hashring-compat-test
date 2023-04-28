import hashlib
import json
import logging
import re
from builtins import object
import uuid

import pylibmc
from uhashring import HashRing

import util 

log = logging.getLogger(__name__)


class MemcachedClient(object):
    def __init__(self, servers, pool_size=25, global_key_prefix=''):
        """Client for setting and fetching values in memcached. Pickling is turned off by default.

        Parameters:
            servers: list of servers, can be of the format 127.0.0.1:11211 or with aliases
            pool_size: integer. number of available clients for the underlying pylimbc client pool
            global_key_prefix: str. If set, the prefix will be prepended to all keys used for get and set methods
                for this instance, e.g. client.get('test') with global_key_prefix of 'ingestion-' would be fetching
                `ingestion-test` under the hood.
        """
        self.min_compress_len = 1024
        # settings set from here
        # http://sendapatch.se/projects/pylibmc/behaviors.html#failover
        client_behaviors = {
            "tcp_nodelay": True,
            "remove_failed": 1,
            "retry_timeout": 1,
            "dead_timeout": 60,
            "pickle_protocol": 0,
        }
        hash_ring_config = {}
        for server in servers:
            sc = parse_server_config(server)
            mc = pylibmc.Client(
                [sc.get("url")], binary=True, behaviors=client_behaviors
            )
            mc_pool = pylibmc.ClientPool(mc, pool_size)
            hash_ring_config[sc.get("alias")] = {
                "hostname": sc.get("hostname"),
                "port": sc.get("port"),
                "weight": sc.get("weight"),
                "instance": mc_pool,
            }
        self.hash_ring = HashRing(hash_ring_config, hash_fn="ketama")
        self.global_key_prefix = global_key_prefix

    def _hash_key(self, key, key_prefix=""):
        # always hash keys so that we don't have control characters in them
        full_key = self.global_key_prefix + key_prefix + key
        key = hashlib.sha256(full_key.encode("utf-8")).hexdigest()
        return key

    def get(self, key):
        hashed_key = self._hash_key(key)
        pool = self.hash_ring.get_node_instance(hashed_key)
        if pool:
            with pool.reserve() as mc:
                return mc.get(hashed_key)

    def set(self, key, value, **kwargs):
        hashed_key = self._hash_key(key)
        try:
            min_compress_len = kwargs.pop("min_compress_len")
        except KeyError:
            min_compress_len = self.min_compress_len

        pool = self.hash_ring.get_node_instance(hashed_key)
        with pool.reserve() as mc:
            return mc.set(
                hashed_key, value, min_compress_len=min_compress_len, **kwargs
            )

    def get_multi(self, keys, key_prefix=""):
        instance_mapping = {}
        key_mapping = {}

        for orig_key in keys:
            hashed_key = self._hash_key(orig_key, key_prefix=key_prefix)
            key_mapping[hashed_key] = orig_key
            pool = self.hash_ring.get_node_instance(hashed_key)
            if pool:
                if pool in instance_mapping:
                    instance_mapping[pool].add(hashed_key)
                else:
                    instance_mapping[pool] = set([hashed_key])

        try:
            result = {}
            for pool, keys in instance_mapping.items():
                with pool.reserve() as mc:
                    result.update(mc.get_multi(keys, key_prefix=key_prefix))
        except pylibmc.Error:
            log.error("Cound not use memcached connection, returning empty list")
            result = {}

        return {
            key_mapping[orig_key]: value for orig_key, value in list(result.items())
        }

    def set_multi(self, mapping, time=0, key_prefix=""):
        instance_mapping = {}
        key_mapping = {}

        for orig_key, value in mapping.items():
            hashed_key = self._hash_key(orig_key, key_prefix=key_prefix)
            key_mapping[hashed_key] = orig_key
            instance = self.hash_ring.get_node_instance(hashed_key)
            if instance in instance_mapping:
                instance_mapping[instance][hashed_key] = value
            else:
                instance_mapping[instance] = {hashed_key: value}

        try:
            result = []
            for pool, kv in instance_mapping.items():
                with pool.reserve() as mc:
                    result.extend(
                        mc.set_multi(
                            kv,
                            time=time,
                            key_prefix=key_prefix,
                            min_compress_len=0,
                        )
                    )
        except pylibmc.Error as err:
            log.error("Memcache set_multi failed", err)
            result = []

        return [key_mapping[orig_key] for orig_key in result]

    def delete(self, key):
        hashed_key = self._hash_key(key)
        pool = self.hash_ring.get_node_instance(hashed_key)
        if pool:
            with pool.reserve() as mc:
                return mc.delete(hashed_key)

    def delete_multi(self, keys, key_prefix=""):
        instance_mapping = {}
        key_mapping = {}

        for orig_key in keys:
            hashed_key = self._hash_key(orig_key, key_prefix=key_prefix)
            key_mapping[hashed_key] = orig_key
            pool = self.hash_ring.get_node_instance(hashed_key)
            if pool:
                if pool in instance_mapping:
                    instance_mapping[pool].add(hashed_key)
                else:
                    instance_mapping[pool] = set([hashed_key])

        for pool, keys in instance_mapping.items():
            with pool.reserve() as mc:
                mc.delete_multi(keys, key_prefix=key_prefix)


def parse_server_config(server):
    conn_alias, conn, weight = parse_alias_and_weights(server)
    hostname, port = parse_host_and_port(conn)
    return {
        "alias": conn_alias,
        "url": conn,
        "hostname": hostname,
        "port": int(port or 80),
        "weight": int(weight or 1),
    }


def parse_alias_and_weights(server):
    alias_match = re.search("\((.*)\)", server)
    if alias_match:
        conn_alias = alias_match.group(1)
        new_server = server.replace("({})".format(conn_alias), "")
        conn, weight = parse_conn_and_weight(new_server)
    else:
        conn, weight = parse_conn_and_weight(server)
        conn_alias = conn

    return conn_alias, conn, weight


def parse_conn_and_weight(server):
    pair = server.split("/")
    if len(pair) > 1:
        return pair
    else:
        return pair[0], 1


def parse_host_and_port(conn):
    pair = conn.split(":")
    if len(pair) > 1:
        return pair
    else:
        return pair[0], 80

def seed_memcached_with_ingestion(cache_client, num_values):
    data = {}
    for i in range(num_values): 
        key = str(uuid.uuid4()) + '-pylibmc'
        data[key] = i
    cache_client.set_multi(data)
    with open(util.INGESTION_SEEDED_MC_DUMP_FILE % num_values, 'w') as hr_data:
        json.dump(data, hr_data)


if __name__ == '__main__': 
    print("\nSearching with ingestion python3 client")
    client = MemcachedClient(util.MEMCACHED_SERVERS)
    util.run_and_report(client)
    print("----------\n")
    
    