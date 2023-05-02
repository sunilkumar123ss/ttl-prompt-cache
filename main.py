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

