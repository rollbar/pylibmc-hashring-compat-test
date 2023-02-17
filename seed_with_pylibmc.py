from util import NUMBER_ITEMS_TO_SEED, MEMCACHED_SERVERS
import pylibmc_test

if __name__ == '__main__':
    client = pylibmc_test.Client(MEMCACHED_SERVERS)
    pylibmc_test.seed_memcached_with_pylibmc(client, NUMBER_ITEMS_TO_SEED)
    print('added %d items to memcached with pylibmc' % NUMBER_ITEMS_TO_SEED)