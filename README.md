## Running the test

Start up the memcached servers 

```bash
docker compose run --rm memcached
```

Seed data both with pylibmc and hashring

```bash
docker compose run --rm -e NUMBER_ITEMS_TO_SEED=1000 seed_with_hashring
docker compose run --rm -e NUMBER_ITEMS_TO_SEED=1000 seed_with_pylibmc
```

This will add + create a json dump of the added data in `added_data/`, which will be used when trying to pull up the keys later. 


Try to get data with hashring/python-memcached client and with the pylibmc client 

```bash
memcache-test git:(main) docker compose run -e NUMBER_ITEMS_TO_SEED=1000 hashring

Searching with hash_ring memcached client
[PYLIBMC SEEDED] Searched for 1000 keys, found 312
[HASHRING SEEDED] Searched for 1000 keys, found 1000
----------
```

```bash
docker compose run -e NUMBER_ITEMS_TO_SEED=1000 pylibmc

Searching with pylibmc client
[PYLIBMC SEEDED] Searched for 1000 keys, found 1000
[HASHRING SEEDED] Searched for 1000 keys, found 332
----------
```