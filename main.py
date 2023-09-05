"""Local SQLite cache keyed by complete request context and an explicit TTL."""
import argparse
import hashlib
import json
from pathlib import Path
import math
import sqlite3
import sys
import time


def cache_key(model, prompt, parameters, namespace="v1"):
    if any(not isinstance(x, str) or not x for x in (model, prompt, namespace)):
        raise ValueError("model, prompt, and namespace must be nonempty strings")
    if not isinstance(parameters, dict):
        raise ValueError("parameters must be an object")
    raw = json.dumps([namespace, model, prompt, parameters], sort_keys=True, ensure_ascii=False,
                     separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def finite(value, name):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return value


class PromptCache:
    def __init__(self, path=":memory:"):
        self.connection = sqlite3.connect(path)
        self.connection.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT NOT NULL, expires REAL NOT NULL)")
        self.hits, self.misses = 0, 0

    def put(self, key, value, ttl_seconds, now):
        finite(now, "now")
        finite(ttl_seconds, "ttl_seconds")
        if ttl_seconds <= 0 or not math.isfinite(now + ttl_seconds):
            raise ValueError("ttl_seconds must be positive with a finite expiration")
        encoded = json.dumps(value, allow_nan=False)
        with self.connection:
            self.connection.execute("INSERT INTO cache VALUES (?, ?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, expires=excluded.expires",
                                    (key, encoded, now + ttl_seconds))

    def get(self, key, now):
        finite(now, "now")
        row = self.connection.execute("SELECT value, expires FROM cache WHERE key=?", (key,)).fetchone()
        if row is None or row[1] <= now:
            self.misses += 1
            return {"hit": False, "value": None}
        self.hits += 1
        return {"hit": True, "value": json.loads(row[0]), "expires_at": row[1]}

    def expire(self, now):
        finite(now, "now")
        with self.connection:
            return self.connection.execute("DELETE FROM cache WHERE expires <= ?", (now,)).rowcount

    def stats(self, now):
        finite(now, "now")
        active = self.connection.execute("SELECT count(*) FROM cache WHERE expires > ?", (now,)).fetchone()[0]
        total = self.connection.execute("SELECT count(*) FROM cache").fetchone()[0]
        return {"active_entries": active, "expired_entries": total - active,
                "session_hits": self.hits, "session_misses": self.misses}

    def close(self):
        self.connection.close()


def execute(cache, operations):
    if not isinstance(operations, list):
        raise ValueError("operations must be a list")
    results = []
    for operation in operations:
        if not isinstance(operation, dict):
            raise ValueError("each operation must be an object")
        now = operation.get("now", time.time())
        action = operation["op"]
        if action in ("put", "get"):
            key = cache_key(operation["model"], operation["prompt"], operation.get("parameters", {}),
                            operation.get("namespace", "v1"))
            if action == "put":
                cache.put(key, operation["value"], operation["ttl_seconds"], now)
                result = {"stored": True, "key": key}
            else:
                result = cache.get(key, now)
        elif action == "expire":
            result = {"deleted": cache.expire(now)}
        elif action == "stats":
            result = cache.stats(now)
        else:
            raise ValueError(f"unknown operation: {action}")
        results.append(result)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--db", default=":memory:", help="SQLite path; default is ephemeral")
    args = parser.parse_args()
    cache = None
    try:
        input_path = Path(args.input)
        if not input_path.is_absolute():
            input_path = Path(__file__).resolve().parent / input_path
        with input_path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        cache = PromptCache(args.db)
        print(json.dumps(execute(cache, data["operations"]), indent=2, allow_nan=False))
        return 0
    except (ValueError, KeyError, TypeError, OSError, sqlite3.Error) as error:
        print(f"Cache operation failed: {error}", file=sys.stderr)
        return 2
    finally:
        if cache:
            cache.close()


if __name__ == "__main__":
    sys.exit(main())
