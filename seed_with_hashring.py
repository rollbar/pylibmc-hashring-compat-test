from util import NUMBER_ITEMS_TO_SEED, MEMCACHED_SERVERS_FMT
import hash_ring_test

if __name__ == '__main__':
    client = hash_ring_test.MemcacheClient(MEMCACHED_SERVERS_FMT)
    hash_ring_test.seed_memcached_with_hashring(client, NUMBER_ITEMS_TO_SEED)
    print('added %d items to memcached with pylibmc' % NUMBER_ITEMS_TO_SEED)
