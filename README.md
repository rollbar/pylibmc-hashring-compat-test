## Running the test

Start up the memcached servers 

```bash
docker compose run --rm memcached
```

Seed data with the ingestion way (pylibmc + uhashring), the new mox way (memcache + uhashring), and the old mox way (memcache hash_ring)

```bash
docker compose run --rm -e NUMBER_ITEMS_TO_SEED=20000 seed_with_ingestion
docker compose run --rm -e NUMBER_ITEMS_TO_SEED=20000 seed_with_hashring
docker compose run --rm -e NUMBER_ITEMS_TO_SEED=20000 seed_with_moxmemcache
docker compose run --rm -e NUMBER_ITEMS_TO_SEED=20000 seed_with_moxapi
```

This will add + create a json dump of the added data in `added_data/`, which will be used when trying to pull up the keys later. 


Using the current mox setup, try to get keys written by ingestion, hash_ring, and mox 

```bash
➜  memcache-test git:(nodejs-compat) ✗  docker compose run -e NUMBER_ITEMS_TO_SEED=1000 mox_memcache_test

Searching with mox memcached client
[PYLIBMC SEEDED] Searched for 1000 keys, found 1000
[HASHRING SEEDED] Searched for 1000 keys, found 822
[MOX SEEDED] Searched for 1000 keys, found 1000
----------
----------
```

Using the current ingestion setup, try to get keys written by ingestion, hash_ring, and mox 

```bash
➜  memcache-test git:(nodejs-compat) ✗  docker compose run -e NUMBER_ITEMS_TO_SEED=1000 ingestion_memcache_test

Searching with ingestion python3 client
[PYLIBMC SEEDED] Searched for 1000 keys, found 1000
[HASHRING SEEDED] Searched for 1000 keys, found 822
[MOX SEEDED] Searched for 1000 keys, found 1000
----------
```

Using the old mox setup, try to get keys written by ingestion, hash_ring, and mox 

```bash
➜  memcache-test git:(nodejs-compat) ✗  docker compose run -e NUMBER_ITEMS_TO_SEED=1000 hashring

Searching with hash_ring memcached client
[PYLIBMC SEEDED] Searched for 1000 keys, found 813
[HASHRING SEEDED] Searched for 1000 keys, found 1000
[MOX SEEDED] Searched for 1000 keys, found 823
----------
```

Using the moxapi setup, try to get keys written by ingestion, hash_ring, and mox 
```bash
➜  memcache-test git:(nodejs-compat) ✗  docker compose run -e NUMBER_ITEMS_TO_SEED=20000 moxapi_memcache_test
Searching mox keys
have not searched all keys yet, sleeping 0.5s
Searching ingestion keys
have not searched all keys yet, sleeping 0.5s
Searching old mox seeded keys
have not searched all keys yet, sleeping 0.5s
[MOX SEEDED] Searched for 1000 keys, found 303
[OLD MOX SEEDED] Searched for 1000 keys, found 303
[INGESTION SEEDED] Searched for 1000 keys, found 317
```

