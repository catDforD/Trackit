"""
Performance benchmarks for Trackit system.

Tests cover:
- Database query performance
- Agent execution speed
- Cache effectiveness
- Memory usage patterns

Author: Trackit Development
"""

import unittest
import tempfile
import os
import time
import tracemalloc
from datetime import datetime, timedelta

from src.agents.recording_agent import RecordingAgent
from src.agents.query_agent import QueryAgent
from src.database.repository import HabitRepository
from src.database.schema import init_database
from src.config.settings import settings


class TestDatabasePerformance(unittest.TestCase):
    """Test database performance characteristics."""

    def setUp(self):
        """Set up test database with sample data."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        settings.DB_PATH = self.db_path
        init_database()

        self.repo = HabitRepository()

        # Add sample data for performance testing
        self._add_sample_data(100)

    def tearDown(self):
        """Clean up temporary database."""
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def _add_sample_data(self, count):
        """Add sample entries for testing."""
        categories = ["运动", "学习", "睡眠", "情绪", "饮食"]
        moods = ["positive", "neutral", "negative"]

        for i in range(count):
            date = (datetime.now() - timedelta(days=i % 30)).strftime("%Y-%m-%d")
            self.repo.add_entry(
                raw_input=f"测试记录{i}",
                category=categories[i % len(categories)],
                mood=moods[i % len(moods)],
                metrics={"value": i},
                entry_date=date
            )

    def test_insert_performance(self):
        """Test database insert performance."""
        start_time = time.time()

        # Insert 100 entries
        for i in range(100):
            self.repo.add_entry(
                raw_input=f"性能测试{i}",
                category="测试",
                mood="neutral",
                metrics={}
            )

        elapsed = time.time() - start_time

        # Should complete in reasonable time (< 2 seconds for 100 inserts)
        # (Adjusted for real-world disk I/O performance)
        self.assertLess(elapsed, 2.0,
                       f"100 inserts took {elapsed:.3f}s, expected < 2.0s")

        print(f"\n✓ Insert performance: 100 entries in {elapsed:.3f}s "
              f"({100/elapsed:.0f} entries/sec)")

    def test_query_by_date_performance(self):
        """Test date-based query performance."""
        # Warm up
        self.repo.get_entries_by_date(datetime.now().strftime("%Y-%m-%d"))

        # Measure
        start_time = time.time()
        iterations = 100

        for _ in range(iterations):
            self.repo.get_entries_by_date(datetime.now().strftime("%Y-%m-%d"))

        elapsed = time.time() - start_time
        avg_time = elapsed / iterations

        # Each query should be fast (< 10ms)
        self.assertLess(avg_time, 0.01,
                       f"Date query took {avg_time*1000:.2f}ms, expected < 10ms")

        print(f"\n✓ Date query performance: {avg_time*1000:.3f}ms average "
              f"({iterations/elapsed:.0f} queries/sec)")

    def test_query_by_category_performance(self):
        """Test category-based query performance."""
        start_time = time.time()
        iterations = 100

        for _ in range(iterations):
            self.repo.get_entries_by_category("运动")

        elapsed = time.time() - start_time
        avg_time = elapsed / iterations

        self.assertLess(avg_time, 0.01)

        print(f"\n✓ Category query performance: {avg_time*1000:.3f}ms average")

    def test_date_range_query_performance(self):
        """Test date range query performance."""
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")

        start_time = time.time()
        iterations = 100

        for _ in range(iterations):
            self.repo.get_entries_by_date_range(start_date, end_date)

        elapsed = time.time() - start_time
        avg_time = elapsed / iterations

        self.assertLess(avg_time, 0.02)

        print(f"\n✓ Date range query performance: {avg_time*1000:.3f}ms average")

    def test_statistics_query_performance(self):
        """Test statistics aggregation performance."""
        start_time = time.time()
        iterations = 50

        for _ in range(iterations):
            self.repo.get_statistics()

        elapsed = time.time() - start_time
        avg_time = elapsed / iterations

        self.assertLess(avg_time, 0.05)

        print(f"\n✓ Statistics query performance: {avg_time*1000:.3f}ms average")


class TestAgentPerformance(unittest.TestCase):
    """Test agent execution performance."""

    def setUp(self):
        """Set up test database."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        settings.DB_PATH = self.db_path
        init_database()

        self.recording_agent = RecordingAgent()
        self.query_agent = QueryAgent()

        # Add sample data
        repo = HabitRepository()
        for i in range(20):
            repo.add_entry(
                raw_input=f"测试记录{i}",
                category="运动",
                mood="positive",
                metrics={"distance_km": 5.0},
                entry_date=datetime.now().strftime("%Y-%m-%d")
            )

    def tearDown(self):
        """Clean up temporary database."""
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_recording_agent_initialization_time(self):
        """Test RecordingAgent initialization is fast."""
        start_time = time.time()

        for _ in range(10):
            agent = RecordingAgent()

        elapsed = time.time() - start_time

        self.assertLess(elapsed, 0.1)

        print(f"\n✓ RecordingAgent initialization: {elapsed*100:.2f}ms average")

    def test_query_agent_initialization_time(self):
        """Test QueryAgent initialization is fast."""
        start_time = time.time()

        for _ in range(10):
            agent = QueryAgent()

        elapsed = time.time() - start_time

        self.assertLess(elapsed, 0.1)

        print(f"\n✓ QueryAgent initialization: {elapsed*100:.2f}ms average")

    def test_validation_speed(self):
        """Test data validation performance."""
        agent = RecordingAgent()

        start_time = time.time()
        iterations = 100

        for _ in range(iterations):
            agent.validate_extraction("今天跑了5公里")

        elapsed = time.time() - start_time

        # Validation should be reasonably fast even with LLM calls
        # (This test assumes caching is working)
        print(f"\n✓ Validation speed: {elapsed/iterations*1000:.2f}ms average")

    def test_feedback_generation_speed(self):
        """Test feedback generation performance."""
        agent = RecordingAgent()

        test_data = {
            "category": "运动",
            "mood": "positive",
            "metrics": {"distance_km": 5.0}
        }

        start_time = time.time()
        iterations = 1000

        for _ in range(iterations):
            agent._generate_feedback(test_data)

        elapsed = time.time() - start_time
        avg_time = elapsed / iterations

        # Feedback generation should be very fast (< 1ms)
        self.assertLess(avg_time, 0.001)

        print(f"\n✓ Feedback generation: {avg_time*1000:.4f}ms average")

    def test_timeframe_parsing_speed(self):
        """Test timeframe parsing performance."""
        agent = QueryAgent()

        start_time = time.time()
        iterations = 1000

        for _ in range(iterations):
            agent._parse_timeframe("week")

        elapsed = time.time() - start_time
        avg_time = elapsed / iterations

        self.assertLess(avg_time, 0.001)

        print(f"\n✓ Timeframe parsing: {avg_time*1000:.4f}ms average")


class TestMemoryUsage(unittest.TestCase):
    """Test memory usage patterns."""

    def setUp(self):
        """Set up test database."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        settings.DB_PATH = self.db_path
        init_database()

    def tearDown(self):
        """Clean up temporary database."""
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_memory_usage_on_bulk_insert(self):
        """Test memory usage during bulk insert."""
        tracemalloc.start()

        repo = HabitRepository()

        # Baseline
        baseline = tracemalloc.get_traced_memory()[0]

        # Insert 1000 entries
        for i in range(1000):
            repo.add_entry(
                raw_input=f"内存测试{i}",
                category="测试",
                mood="neutral",
                metrics={}
            )

        current = tracemalloc.get_traced_memory()[0]
        used = (current - baseline) / 1024  # Convert to KB

        tracemalloc.stop()

        # Memory usage should be reasonable (< 10MB for 1000 inserts)
        self.assertLess(used, 10240,
                       f"Used {used:.0f}KB for 1000 inserts, expected < 10MB")

        print(f"\n✓ Memory usage: {used:.0f}KB for 1000 entries")

    def test_memory_usage_on_large_query(self):
        """Test memory usage during large queries."""
        repo = HabitRepository()

        # Insert data
        for i in range(100):
            repo.add_entry(
                raw_input=f"查询测试{i}",
                category="测试",
                mood="neutral",
                metrics={}
            )

        tracemalloc.start()

        # Large query
        baseline = tracemalloc.get_traced_memory()[0]
        entries = repo.get_entries_by_date_range(
            "2024-01-01",
            "2030-12-31"
        )
        current = tracemalloc.get_traced_memory()[0]

        used = (current - baseline) / 1024  # KB

        tracemalloc.stop()

        self.assertLess(used, 1024,
                       f"Query used {used:.0f}KB, expected < 1MB")

        print(f"\n✓ Query memory usage: {used:.0f}KB for {len(entries)} entries")


class TestCacheEffectiveness(unittest.TestCase):
    """Test cache performance and effectiveness."""

    def setUp(self):
        """Set up test environment."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        settings.DB_PATH = self.db_path
        init_database()

    def tearDown(self):
        """Clean up."""
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_cache_hit_rate(self):
        """Test cache hit rate for repeated queries."""
        from src.llm.extractors import HabitExtractor

        extractor = HabitExtractor()

        # Clear cache first
        extractor.clear_cache()

        # First call (cache miss)
        start_time = time.time()
        extractor.extract("今天跑了5公里")
        first_call_time = time.time() - start_time

        # Second call (should hit cache)
        start_time = time.time()
        extractor.extract("今天跑了5公里")
        second_call_time = time.time() - start_time

        # Cached call should be significantly faster
        speedup = first_call_time / second_call_time if second_call_time > 0 else float('inf')

        print(f"\n✓ Cache speedup: {speedup:.0f}x "
              f"(first: {first_call_time*1000:.2f}ms, "
              f"cached: {second_call_time*1000:.4f}ms)")

        # Cache should provide at least 10x speedup (usually much more)
        self.assertGreater(speedup, 10)

    def test_cache_stats_tracking(self):
        """Test cache statistics are tracked correctly."""
        from src.llm.extractors import HabitExtractor

        extractor = HabitExtractor()
        extractor.clear_cache()

        # Make some calls
        for _ in range(3):
            extractor.extract("测试输入")

        # Get stats
        stats = extractor.get_cache_stats()

        self.assertIsNotNone(stats)
        self.assertIn("hits", stats)
        self.assertIn("misses", stats)

        print(f"\n✓ Cache stats: {stats['hits']} hits, {stats['misses']} misses, "
              f"hit rate: {stats.get('hit_rate', 0):.1%}")


class PerformanceReportGenerator:
    """Generate performance benchmark reports."""

    @staticmethod
    def generate_report():
        """Generate a comprehensive performance report."""
        print("\n" + "="*70)
        print("TRACKIT PERFORMANCE BENCHMARK REPORT")
        print("="*70)

        # Run database performance tests
        print("\n📊 Database Performance:")
        print("-" * 70)

        suite = unittest.TestLoader().loadTestsFromTestCase(TestDatabasePerformance)
        runner = unittest.TextTestRunner(verbosity=0)
        result = runner.run(suite)

        # Run agent performance tests
        print("\n🤖 Agent Performance:")
        print("-" * 70)

        suite = unittest.TestLoader().loadTestsFromTestCase(TestAgentPerformance)
        runner = unittest.TextTestRunner(verbosity=0)
        result = runner.run(suite)

        # Run memory tests
        print("\n💾 Memory Usage:")
        print("-" * 70)

        suite = unittest.TestLoader().loadTestsFromTestCase(TestMemoryUsage)
        runner = unittest.TextTestRunner(verbosity=0)
        result = runner.run(suite)

        # Run cache tests
        print("\n⚡ Cache Effectiveness:")
        print("-" * 70)

        suite = unittest.TestLoader().loadTestsFromTestCase(TestCacheEffectiveness)
        runner = unittest.TextTestRunner(verbosity=0)
        result = runner.run(suite)

        print("\n" + "="*70)
        print("PERFORMANCE BENCHMARK COMPLETE")
        print("="*70)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--report":
        # Generate full report
        PerformanceReportGenerator.generate_report()
    else:
        # Run specific test suite
        unittest.main()
