import mox_memcache_test
from util import NUMBER_ITEMS_TO_SEED, MEMCACHED_SERVERS_FMT

if __name__ == '__main__':
    client = mox_memcache_test.MoxMemcacheClient(MEMCACHED_SERVERS_FMT)
    mox_memcache_test.seed_memcached_with_mox(client, NUMBER_ITEMS_TO_SEED)
    print('added %d items to memcached with uhashring' % NUMBER_ITEMS_TO_SEED)