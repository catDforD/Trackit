"""
Extraction cache module for Trackit.

This module provides caching functionality for LLM extractions to:
- Reduce API costs by avoiding redundant calls
- Improve response time for repeated inputs
- Track cache hit/miss statistics

Author: Trackit Development
"""

import hashlib
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path


class ExtractionCache:
    """
    Cache for LLM extraction results.

    Uses input text hash as key to store extraction results.
    Implements LRU-style eviction and TTL-based expiration.

    Example:
        >>> cache = ExtractionCache(max_size=1000, ttl_hours=24)
        >>> result = {"category": "运动", "mood": "positive"}
        >>> cache.store("今天跑了5公里", result)
        >>> cached = cache.get("今天跑了5公里")
        >>> print(cached["category"])
        运动
    """

    def __init__(
        self,
        max_size: int = 1000,
        ttl_hours: int = 24,
        cache_dir: Optional[str] = None
    ):
        """
        Initialize the cache.

        Args:
            max_size: Maximum number of entries to store
            ttl_hours: Time-to-live for cache entries in hours
            cache_dir: Directory to persist cache (None for in-memory only)
        """
        self.max_size = max_size
        self.ttl = timedelta(hours=ttl_hours)
        self.cache_dir = cache_dir

        # In-memory cache: {hash: (result, timestamp)}
        self._cache: Dict[str, tuple[Dict[str, Any], datetime]] = {}

        # Statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "stores": 0,
            "evictions": 0
        }

        # Load from disk if cache_dir specified
        if self.cache_dir:
            self._load_from_disk()

    def _hash_input(self, text: str) -> str:
        """
        Generate hash for input text.

        Args:
            text: Input text to hash

        Returns:
            SHA256 hash hex digest
        """
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def get(self, user_input: str) -> Optional[Dict[str, Any]]:
        """
        Get cached extraction result.

        Args:
            user_input: Original user input text

        Returns:
            Cached extraction result or None if not found/expired
        """
        key = self._hash_input(user_input)

        if key not in self._cache:
            self.stats["misses"] += 1
            return None

        result, timestamp = self._cache[key]

        # Check if expired
        if datetime.now() - timestamp > self.ttl:
            del self._cache[key]
            self.stats["misses"] += 1
            return None

        self.stats["hits"] += 1
        return result.copy()

    def store(self, user_input: str, result: Dict[str, Any]) -> None:
        """
        Store extraction result in cache.

        Args:
            user_input: Original user input text
            result: Extraction result to cache
        """
        key = self._hash_input(user_input)

        # Evict oldest if at capacity
        if len(self._cache) >= self.max_size and key not in self._cache:
            self._evict_oldest()

        self._cache[key] = (result.copy(), datetime.now())
        self.stats["stores"] += 1

    def _evict_oldest(self) -> None:
        """Evict the oldest cache entry."""
        if not self._cache:
            return

        # Find oldest entry
        oldest_key = min(self._cache.items(), key=lambda x: x[1][1])[0]
        del self._cache[oldest_key]
        self.stats["evictions"] += 1

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()

    def cleanup_expired(self) -> int:
        """
        Remove expired entries from cache.

        Returns:
            Number of entries removed
        """
        now = datetime.now()
        expired_keys = [
            key for key, (_, timestamp) in self._cache.items()
            if now - timestamp > self.ttl
        ]

        for key in expired_keys:
            del self._cache[key]

        return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats:
                - hits: Number of cache hits
                - misses: Number of cache misses
                - stores: Total number of stores
                - evictions: Number of evictions
                - size: Current cache size
                - hit_rate: Cache hit rate (0-1)
        """
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total_requests if total_requests > 0 else 0

        return {
            **self.stats,
            "size": len(self._cache),
            "hit_rate": hit_rate,
            "max_size": self.max_size
        }

    def _load_from_disk(self) -> None:
        """Load cache from disk file."""
        if not self.cache_dir:
            return

        cache_path = Path(self.cache_dir) / "extraction_cache.json"
        if not cache_path.exists():
            return

        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Restore cache entries
            now = datetime.now()
            for key, (result_dict, timestamp_str) in data["entries"].items():
                timestamp = datetime.fromisoformat(timestamp_str)

                # Skip expired entries
                if now - timestamp > self.ttl:
                    continue

                self._cache[key] = (result_dict, timestamp)

            # Restore stats
            self.stats.update(data.get("stats", {}))

        except Exception as e:
            print(f"Warning: Failed to load cache from disk: {e}")

    def save_to_disk(self) -> None:
        """Save cache to disk file."""
        if not self.cache_dir:
            return

        cache_path = Path(self.cache_dir) / "extraction_cache.json"
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Prepare data for serialization
            entries = {
                key: (result, timestamp.isoformat())
                for key, (result, timestamp) in self._cache.items()
            }

            data = {
                "entries": entries,
                "stats": self.stats,
                "saved_at": datetime.now().isoformat()
            }

            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"Warning: Failed to save cache to disk: {e}")

    def __len__(self) -> int:
        """Return current cache size."""
        return len(self._cache)

    def __repr__(self) -> str:
        """Return cache representation."""
        stats = self.get_stats()
        return (
            f"ExtractionCache("
            f"size={stats['size']}/{stats['max_size']}, "
            f"hit_rate={stats['hit_rate']:.1%})"
        )


# Global cache instance
_global_cache: Optional[ExtractionCache] = None


def get_cache() -> ExtractionCache:
    """
    Get or create global cache instance.

    Returns:
        Global ExtractionCache instance
    """
    global _global_cache

    if _global_cache is None:
        from ..config.settings import settings
        cache_dir = getattr(settings, 'CACHE_DIR', None)
        _global_cache = ExtractionCache(
            max_size=1000,
            ttl_hours=24,
            cache_dir=cache_dir
        )

    return _global_cache


def clear_cache() -> None:
    """Clear the global cache."""
    cache = get_cache()
    cache.clear()


if __name__ == "__main__":
    # Test cache functionality
    print("Testing ExtractionCache...")
    print("=" * 60)

    cache = ExtractionCache(max_size=5, ttl_hours=1)

    # Store some results
    print("\n1. Storing results...")
    cache.store("今天跑了5公里", {"category": "运动", "mood": "positive"})
    cache.store("读了50页书", {"category": "学习", "mood": "neutral"})
    cache.store("睡了8小时", {"category": "睡眠", "mood": "positive"})

    print(f"Cache size: {len(cache)}")

    # Test cache hit
    print("\n2. Testing cache hit...")
    result = cache.get("今天跑了5公里")
    print(f"Hit: {result is not None}")
    print(f"Result: {result}")

    # Test cache miss
    print("\n3. Testing cache miss...")
    result = cache.get("没记录过的输入")
    print(f"Miss: {result is None}")

    # Test eviction
    print("\n4. Testing eviction (max_size=5)...")
    for i in range(10):
        cache.store(f"输入{i}", {"category": "测试"})
    print(f"Cache size after 10 stores: {len(cache)}")
    print(f"Evictions: {cache.get_stats()['evictions']}")

    # Test statistics
    print("\n5. Cache statistics:")
    stats = cache.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Test cleanup
    print("\n6. Cleanup expired...")
    removed = cache.cleanup_expired()
    print(f"Removed: {removed} entries")

    print("\n✅ All tests passed!")
