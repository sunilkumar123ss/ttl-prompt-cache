# TTL prompt cache

A local SQLite cache demonstration with canonical request keys, expiration, upserts, and hit/miss reporting. Cached outputs are supplied by the caller; no model is called.

~~~sh
python3 main.py --input example.json
python3 main.py --input example.json --db demo.sqlite
python3 -m unittest -v
~~~

Keys hash namespace, model, the full prompt, and sorted generation parameters. Include every context element that changes the response in the prompt/parameters; use namespaces for version invalidation and tenant separation. Expiration is exclusive: an entry at its expiration time is a miss. Explicit timestamps in the fixture make the example reproducible; omitted timestamps use the current clock. Hit/miss counters cover the current process, while entries can persist.

SQLite stores response values as plaintext. Hashing keys is not encryption, access control, or privacy protection. This is a single-process educational cache; it does not supply distributed eviction, stampede prevention, or tenant authentication. Invalid later operations do not roll back earlier committed operations.

## Scope

This is an educational implementation with synthetic fixtures. Run the tests and inspect the documented limits before adapting it.

## Repository checks

```sh
python3 verify.py
```

This runs the isolated test suite, synthetic example, and CLI help. The included GitHub Actions workflow repeats these checks when the repository is published. No hosted CI result is claimed by the local verification report.
