from util import NUMBER_ITEMS_TO_SEED, MEMCACHED_SERVERS
import ingestion_memcache_test

if __name__ == '__main__':
    client = ingestion_memcache_test.MemcachedClient(MEMCACHED_SERVERS)
    ingestion_memcache_test.seed_memcached_with_ingestion(client, NUMBER_ITEMS_TO_SEED)
    print('added %d items to memcached with pylibmc' % NUMBER_ITEMS_TO_SEED)