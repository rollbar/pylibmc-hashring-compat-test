from __future__ import print_function
import os
import json 

NUMBER_ITEMS_TO_SEED = int(os.getenv('NUMBER_ITEMS_TO_SEED', 100))

MEMCACHED_SERVERS = ['memcached1', 'memcached2', 'memcached3']
MEMCACHED_SERVERS_FMT = [(server, 1) for server in MEMCACHED_SERVERS]

INGESTION_SEEDED_MC_DUMP_FILE = 'added_data/ingestion_added_data-%d.json'
HASHRING_SEEDED_MC_DUMP_FILE = 'added_data/hash_ring_added_data-%d.json'
MOX_SEEDED_MC_DUMP_FILE = 'added_data/mox_added_data-%d.json'


def load_hash_ring_test_data(num_values): 
    data = {}
    with open(HASHRING_SEEDED_MC_DUMP_FILE % num_values, 'r') as inf:
        data = json.load(inf)
    return data

def load_pylibmc_test_data(num_values):
    data = {}
    with open(INGESTION_SEEDED_MC_DUMP_FILE % num_values, 'r') as hr_data:
        data = json.load(hr_data)
    return data

def run_and_report(client):
    pylibmc_test_data = load_pylibmc_test_data(NUMBER_ITEMS_TO_SEED)
    hash_ring_test_data = load_hash_ring_test_data(NUMBER_ITEMS_TO_SEED)

    pylibmc_results = client.get_multi(pylibmc_test_data.keys())
    print("[PYLIBMC SEEDED] Searched for %d keys, found %d" % (len(pylibmc_test_data), len(pylibmc_results)))

    hashring_results = client.get_multi(hash_ring_test_data.keys())
    print("[HASHRING SEEDED] Searched for %d keys, found %d" % (len(hash_ring_test_data), len(hashring_results)))