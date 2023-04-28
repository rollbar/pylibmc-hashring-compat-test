from __future__ import print_function
import os
import json 

NUMBER_ITEMS_TO_SEED = int(os.getenv('NUMBER_ITEMS_TO_SEED', 100))

MEMCACHED_SERVERS = ['memcached1', 'memcached2', 'memcached3']
MEMCACHED_SERVERS_FMT = [(server, 1) for server in MEMCACHED_SERVERS]

INGESTION_SEEDED_MC_DUMP_FILE = 'added_data/ingestion_added_data-%d.json'
HASHRING_SEEDED_MC_DUMP_FILE = 'added_data/hash_ring_added_data-%d.json'
MOX_SEEDED_MC_DUMP_FILE = 'added_data/mox_added_data-%d.json'


def load_test_data(file_path, num_items): 
    data = {}
    try: 
        with open(file_path % num_items, 'r') as inf:
            data = json.load(inf)
        return data
    except: 
        print("ERROR: unable to open file %s, returning empty dictionary" % file_path )
        return {}

def run_and_report(client):
    pylibmc_test_data = load_test_data(INGESTION_SEEDED_MC_DUMP_FILE,  NUMBER_ITEMS_TO_SEED)
    hash_ring_test_data = load_test_data(HASHRING_SEEDED_MC_DUMP_FILE, NUMBER_ITEMS_TO_SEED)
    mox_test_data = load_test_data(MOX_SEEDED_MC_DUMP_FILE, NUMBER_ITEMS_TO_SEED)

    pylibmc_results = client.get_multi(pylibmc_test_data.keys())
    print("[PYLIBMC SEEDED] Searched for %d keys, found %d" % (len(pylibmc_test_data), len(pylibmc_results)))

    hashring_results = client.get_multi(hash_ring_test_data.keys())
    print("[HASHRING SEEDED] Searched for %d keys, found %d" % (len(hash_ring_test_data), len(hashring_results)))

    mox_results = client.get_multi(mox_test_data.keys())
    print("[MOX SEEDED] Searched for %d keys, found %d" % (len(mox_test_data), len(mox_results)))