"""
Cache functionality test for Trackit.

Tests the extraction cache system including:
- Basic cache hit/miss
- Batch extraction with cache
- Cache statistics
- Cache eviction

Author: Trackit Development
"""

import os
import sys
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.llm.extractors import HabitExtractor
from src.utils.cache import ExtractionCache


def test_basic_cache():
    """Test basic cache hit/miss functionality."""
    print("\n" + "="*70)
    print("TEST 1: Basic Cache Functionality")
    print("="*70)

    extractor = HabitExtractor(use_cache=True)

    # First call - should hit API
    print("\n1. First extraction (API call expected):")
    start = time.time()
    result1 = extractor.extract("今天跑了5公里，感觉不错")
    elapsed1 = time.time() - start
    print(f"   Category: {result1['category']}")
    print(f"   Cached: {result1.get('cached', False)}")
    print(f"   Time: {elapsed1:.3f}s")

    # Second call - should hit cache
    print("\n2. Second extraction (cache hit expected):")
    start = time.time()
    result2 = extractor.extract("今天跑了5公里，感觉不错")
    elapsed2 = time.time() - start
    print(f"   Category: {result2['category']}")
    print(f"   Cached: {result2.get('cached', False)}")
    print(f"   Time: {elapsed2:.3f}s")
    print(f"   Speedup: {elapsed1/elapsed2:.1f}x faster")

    # Different input - should hit API
    print("\n3. Different input (API call expected):")
    start = time.time()
    result3 = extractor.extract("读了50页书")
    elapsed3 = time.time() - start
    print(f"   Category: {result3['category']}")
    print(f"   Cached: {result3.get('cached', False)}")
    print(f"   Time: {elapsed3:.3f}s")

    # Show cache stats
    stats = extractor.get_cache_stats()
    print(f"\n4. Cache Statistics:")
    print(f"   Size: {stats['size']}")
    print(f"   Hits: {stats['hits']}")
    print(f"   Misses: {stats['misses']}")
    print(f"   Hit Rate: {stats['hit_rate']:.1%}")


def test_batch_extraction():
    """Test batch extraction with caching."""
    print("\n" + "="*70)
    print("TEST 2: Batch Extraction with Cache")
    print("="*70)

    extractor = HabitExtractor(use_cache=True)

    inputs = [
        "今天跑了5公里",
        "读了50页书",
        "睡了8小时",
        "今天跑了5公里",  # Duplicate - should hit cache
        "读了50页书",      # Duplicate - should hit cache
        "心情很好",
    ]

    print(f"\n1. Processing {len(inputs)} inputs (2 duplicates)...")
    result = extractor.batch_extract(inputs, show_progress=True)

    summary = result["summary"]
    print(f"\n2. Batch Summary:")
    print(f"   Total: {summary['total']}")
    print(f"   From Cache: {summary['cached']}")
    print(f"   API Calls: {summary['api_calls']}")
    print(f"   Cache Hit Rate: {summary['cache_hit_rate']:.1%}")

    print(f"\n3. Individual Results:")
    for i, (inp, res) in enumerate(zip(inputs, result["results"])):
        cached = "✓" if res.get("cached") else " "
        print(f"   {cached} [{i+1}] {inp[:20]:20} -> {res['category']}")


def test_cache_stats():
    """Test cache statistics and management."""
    print("\n" + "="*70)
    print("TEST 3: Cache Statistics")
    print("="*70)

    cache = ExtractionCache(max_size=5, ttl_hours=24)
    extractor = HabitExtractor(cache=cache)

    # Add some entries
    print("\n1. Adding 3 entries to cache...")
    extractor.extract("今天跑了5公里")
    extractor.extract("读了50页书")
    extractor.extract("睡了8小时")

    stats = extractor.get_cache_stats()
    print(f"   Cache size: {stats['size']}")
    print(f"   Max size: {stats['max_size']}")

    # Test eviction
    print("\n2. Adding more entries (testing eviction)...")
    extractor.extract("心情很好")
    extractor.extract("没吃早饭")
    extractor.extract("学习2小时")

    stats = extractor.get_cache_stats()
    print(f"   Cache size: {stats['size']} (max: {stats['max_size']})")
    print(f"   Evictions: {stats['evictions']}")


def test_cache_disable():
    """Test extraction with cache disabled."""
    print("\n" + "="*70)
    print("TEST 4: Cache Disabled")
    print("="*70)

    # Create extractor with cache disabled
    extractor = HabitExtractor(use_cache=False)

    print("\n1. First extraction:")
    result1 = extractor.extract("今天跑了5公里")
    print(f"   Category: {result1['category']}")
    print(f"   Cached: {result1.get('cached', False)}")

    print("\n2. Second extraction (same input):")
    result2 = extractor.extract("今天跑了5公里")
    print(f"   Category: {result2['category']}")
    print(f"   Cached: {result2.get('cached', False)}")

    stats = extractor.get_cache_stats()
    print(f"\n3. Cache stats: {stats}")


def test_cache_persistence():
    """Test cache save/load functionality."""
    print("\n" + "="*70)
    print("TEST 5: Cache Persistence")
    print("="*70)

    # Create cache with persistence
    cache_dir = os.path.join(
        os.path.dirname(__file__), "..", "data", "cache_test"
    )
    cache = ExtractionCache(max_size=10, ttl_hours=24, cache_dir=cache_dir)

    extractor = HabitExtractor(cache=cache)

    print("\n1. Adding entries to cache...")
    extractor.extract("今天跑了5公里")
    extractor.extract("读了50页书")

    print(f"   Cache size before save: {len(cache)}")

    # Save to disk
    print("\n2. Saving cache to disk...")
    cache.save_to_disk()

    # Create new cache instance (simulate restart)
    print("\n3. Creating new cache instance (simulating restart)...")
    cache2 = ExtractionCache(max_size=10, ttl_hours=24, cache_dir=cache_dir)
    print(f"   Cache size after load: {len(cache2)}")

    # Test if cache works after load
    print("\n4. Testing cache hit after reload:")
    extractor2 = HabitExtractor(cache=cache2)
    result = extractor2.extract("今天跑了5公里")
    print(f"   Category: {result['category']}")
    print(f"   Cached: {result.get('cached', False)}")

    # Cleanup
    import shutil
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
        print(f"\n5. Cleanup: Removed test cache directory")


def main():
    """Run all cache tests."""
    print("\n" + "="*70)
    print("TRACKIT CACHE FUNCTIONALITY TESTS")
    print("="*70)

    tests = [
        test_basic_cache,
        test_batch_extraction,
        test_cache_stats,
        test_cache_disable,
        test_cache_persistence
    ]

    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*70)
    print("ALL CACHE TESTS COMPLETED")
    print("="*70)


if __name__ == "__main__":
    main()
