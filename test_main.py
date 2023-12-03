import tempfile
import unittest
from pathlib import Path
from main import PromptCache, cache_key, execute


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.cache = PromptCache()
        self.addCleanup(self.cache.close)

    def test_ttl_boundary_and_null_value(self):
        self.cache.put("key", None, 5, 100)
        self.assertTrue(self.cache.get("key", 104.99)["hit"])
        self.assertFalse(self.cache.get("key", 105)["hit"])
        self.assertEqual(self.cache.expire(105), 1)
        self.assertEqual(self.cache.stats(105)["session_misses"], 1)

    def test_complete_context_and_canonical_parameters(self):
        a = cache_key("m", "question", {"b": 2, "a": 1})
        self.assertEqual(a, cache_key("m", "question", {"a": 1, "b": 2}))
        self.assertNotEqual(a, cache_key("m", "question", {"a": 1, "b": 2}, "v2"))
        self.assertNotEqual(a, cache_key("m2", "question", {"a": 1, "b": 2}))

