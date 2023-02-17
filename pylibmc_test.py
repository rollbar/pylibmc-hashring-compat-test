import pylibmc
import hashlib
import uuid
import json

import util

class Client:
    def __init__(self, servers):
        self.client = pylibmc.Client(servers, 
                                     binary=True,
                                     behaviors={"tcp_nodelay": True, "ketama": True})
    
    def _hash_key(self, key, key_prefix=''):
        # always hash keys so we don't have control characters in them
        full_key = key_prefix + key
        key = hashlib.sha256(full_key.encode('utf-8')).hexdigest()
        return key

    def get(self, key):
        return self.client.get(self._hash_key(key))
    
    def get_multi(self, keys, key_prefix=''):
        key_mapping = {}
        new_keys = []

        for orig_key in keys:
            new_key = self._hash_key(orig_key, key_prefix=key_prefix)
            new_keys.append(new_key)

            key_mapping[new_key] = orig_key
        
        result = self.client.get_multi(new_keys, key_prefix=key_prefix)

        return {key_mapping[orig_key]: value for orig_key, value in result.items()}

    def set_multi(self, mapping, time=0, key_prefix=''):
        key_mapping = {}
        new_mapping = {}

        for orig_key, value in mapping.items():
            new_key = self._hash_key(orig_key, key_prefix=key_prefix)
            new_mapping[new_key] = value
            key_mapping[new_key] = orig_key
        
        result = self.client.set_multi(new_mapping)
        return [key_mapping[orig_key] for orig_key in result]


def seed_memcached_with_pylibmc(cache_client, num_values):
    data = {}
    for i in range(num_values): 
        key = str(uuid.uuid4()) + '-pylibmc'
        data[key] = i
    cache_client.set_multi(data)
    with open(util.PYLIBMC_SEEDED_MC_DUMP_FILE % num_values, 'w') as hr_data:
        json.dump(data, hr_data)


if __name__ == '__main__': 
    print("\nSearching with pylibmc client")
    client = Client(util.MEMCACHED_SERVERS)
    util.run_and_report(client)
    print("----------\n")
    
    