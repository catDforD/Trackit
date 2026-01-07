"""
Integration tests for Trackit system.

Tests cover:
- End-to-end workflows (record → query)
- Error handling across the system
- Edge cases and boundary conditions
- Multi-user scenarios
- Data persistence and integrity

Author: Trackit Development
"""

import unittest
import tempfile
import os
import time
from datetime import datetime, timedelta

from src.agents.recording_agent import RecordingAgent
from src.agents.query_agent import QueryAgent
from src.database.schema import init_database
from src.database.repository import HabitRepository
from src.config.settings import settings


class TestEndToEndWorkflows(unittest.TestCase):
    """Test complete user workflows."""

    def setUp(self):
        """Set up test database and agents."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        settings.DB_PATH = self.db_path
        init_database()

        self.recording_agent = RecordingAgent()
        self.query_agent = QueryAgent()

    def tearDown(self):
        """Clean up temporary database."""
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_complete_record_then_query_workflow(self):
        """Test recording habits then querying them."""
        # Record multiple habits using direct database insertion (no API needed)
        repo = HabitRepository()
        habits_data = [
            ("今天跑了5公里，感觉不错", "运动", "positive", {"distance_km": 5.0}),
            ("学习了3小时Python", "学习", "neutral", {"duration_hours": 3.0}),
            ("心情很好", "情绪", "positive", {}),
            ("今天睡了8小时", "睡眠", "neutral", {"hours": 8})
        ]

        successful_records = 0
        for raw_input, category, mood, metrics in habits_data:
            try:
                entry_id = repo.add_entry(
                    raw_input=raw_input,
                    category=category,
                    mood=mood,
                    metrics=metrics
                )
                if entry_id > 0:
                    successful_records += 1
            except Exception as e:
                # If database insertion fails, that's a test failure
                self.fail(f"Database insertion failed: {e}")

        # All should succeed
        self.assertEqual(successful_records, len(habits_data))

        # Verify records exist
        all_entries = repo.get_all_entries()
        self.assertGreater(len(all_entries), 0)

    def test_record_multiple_times_same_category(self):
        """Test recording multiple entries of the same category."""
        # Use direct database insertion (no API needed)
        # Use unique category to avoid conflicts with existing data
        unique_category = f"运动测试_{id(self)}"
        repo = HabitRepository()
        today = datetime.now().strftime("%Y-%m-%d")

        for i in range(5):
            repo.add_entry(
                raw_input=f"运动记录{i+1}",
                category=unique_category,
                mood="positive",
                metrics={"distance_km": 3.0 + i},
                entry_date=today
            )

        # Query should find all entries with this unique category
        entries = repo.get_entries_by_category(unique_category)
        self.assertEqual(len(entries), 5)

    def test_record_across_multiple_days(self):
        """Test recording habits across multiple days."""
        repo = HabitRepository()

        # Use unique category
        unique_category = f"多日测试_{id(self)}"

        # Record for past 7 days
        for i in range(7):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            repo.add_entry(
                raw_input=f"第{7-i}天的运动",
                category=unique_category,
                mood="positive",
                metrics={"distance_km": 5.0},
                entry_date=date
            )

        # Query date range
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")

        entries = repo.get_entries_by_date_range(start_date, end_date, category=unique_category)
        self.assertGreaterEqual(len(entries), 7)  # At least 7, might be more from previous tests

    def test_error_recovery_workflow(self):
        """Test system recovers from errors gracefully."""
        agent = RecordingAgent()

        # Try empty input
        result = agent.execute(user_input="")
        self.assertFalse(result["success"])
        self.assertIn("不能为空", result["error"])

        # Try whitespace input
        result = agent.execute(user_input="   ")
        self.assertFalse(result["success"])

        # Valid input after errors should still work
        repo = HabitRepository()
        entry_id = repo.add_entry(
            raw_input="测试记录",
            category="测试",
            mood="neutral",
            metrics={}
        )
        self.assertIsNotNone(entry_id)


class TestErrorHandling(unittest.TestCase):
    """Test error handling across the system."""

    def setUp(self):
        """Set up test database."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        settings.DB_PATH = self.db_path
        init_database()

    def tearDown(self):
        """Clean up temporary database."""
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_recording_agent_error_types(self):
        """Test different error types are properly identified."""
        agent = RecordingAgent()

        # Empty input
        result = agent.execute(user_input="")
        self.assertEqual(result.get("error_type"), "validation_error")

        # Check error message is user-friendly
        self.assertIsNotNone(result.get("error"))
        self.assertTrue(len(result["error"]) > 0)

    def test_query_agent_handles_empty_database(self):
        """Test query agent handles empty database gracefully."""
        agent = QueryAgent()

        # Query on empty database
        result = agent.execute(query="我这周运动了几次？")

        # Should return success=False or handle gracefully
        self.assertIsInstance(result, dict)
        self.assertIn("success", result)

    def test_repository_invalid_date_format(self):
        """Test repository handles invalid date formats."""
        repo = HabitRepository()

        # This should not crash
        entries = repo.get_entries_by_date("invalid-date")
        self.assertEqual(len(entries), 0)

    def test_concurrent_access_simulation(self):
        """Test simulated concurrent access."""
        repo = HabitRepository()

        # Simulate multiple rapid additions
        entry_ids = []
        for i in range(10):
            entry_id = repo.add_entry(
                raw_input=f"并发测试{i}",
                category="测试",
                mood="neutral",
                metrics={}
            )
            entry_ids.append(entry_id)

        # All should succeed
        self.assertEqual(len(entry_ids), 10)
        self.assertTrue(all(eid > 0 for eid in entry_ids))


class TestEdgeCases(unittest.TestCase):
    """Test boundary conditions and edge cases."""

    def setUp(self):
        """Set up test database."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        settings.DB_PATH = self.db_path
        init_database()

    def tearDown(self):
        """Clean up temporary database."""
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_very_long_input(self):
        """Test handling of very long user input."""
        agent = RecordingAgent()

        # Create a very long input
        long_input = "今天运动了 " + "非常好 " * 100 + "！"

        # Should handle gracefully
        result = agent.execute(user_input=long_input)
        self.assertIsInstance(result, dict)
        self.assertIn("success", result)

    def test_special_characters_in_input(self):
        """Test handling of special characters."""
        agent = RecordingAgent()

        # Various special characters
        test_inputs = [
            "今天运动了！@#$%",
            "What about English? 123",
            "混合中文和English 😊",
            "测试\n换行符\t制表符"
        ]

        for test_input in test_inputs:
            result = agent.execute(user_input=test_input)
            self.assertIsInstance(result, dict)

    def test_unicode_emojis(self):
        """Test handling of unicode emojis."""
        repo = HabitRepository()

        # Add entry with emoji in raw_input
        entry_id = repo.add_entry(
            raw_input="今天心情😊很好",
            category="情绪",
            mood="positive",
            metrics={}
        )

        self.assertIsNotNone(entry_id)

        # Retrieve and verify
        entry = repo.get_entry_by_id(entry_id)
        self.assertEqual(entry["raw_input"], "今天心情😊很好")

    def test_empty_metrics(self):
        """Test handling of empty metrics dictionary."""
        repo = HabitRepository()

        entry_id = repo.add_entry(
            raw_input="心情记录",
            category="情绪",
            mood="neutral",
            metrics={}
        )

        self.assertIsNotNone(entry_id)

        entry = repo.get_entry_by_id(entry_id)
        self.assertEqual(entry["metrics"], {})

    def test_large_metric_values(self):
        """Test handling of large metric values."""
        repo = HabitRepository()

        entry_id = repo.add_entry(
            raw_input="超长距离",
            category="运动",
            mood="positive",
            metrics={"distance_km": 999999.99}
        )

        entry = repo.get_entry_by_id(entry_id)
        self.assertAlmostEqual(entry["metrics"]["distance_km"], 999999.99, places=2)

    def test_all_categories(self):
        """Test all defined categories work correctly."""
        repo = HabitRepository()
        categories = ["运动", "学习", "睡眠", "情绪", "饮食", "其他"]

        for category in categories:
            entry_id = repo.add_entry(
                raw_input=f"{category}记录",
                category=category,
                mood="neutral",
                metrics={}
            )
            self.assertIsNotNone(entry_id)

        # Verify all categories are stored
        stored_categories = repo.get_categories()
        for category in categories:
            self.assertIn(category, stored_categories)

    def test_all_mood_types(self):
        """Test all mood types work correctly."""
        repo = HabitRepository()
        moods = ["positive", "neutral", "negative"]

        for mood in moods:
            entry_id = repo.add_entry(
                raw_input=f"{mood}心情",
                category="情绪",
                mood=mood,
                metrics={}
            )
            self.assertIsNotNone(entry_id)

    def test_date_boundaries(self):
        """Test date range boundaries."""
        repo = HabitRepository()

        # Add entries at boundaries
        dates = [
            "2026-01-01",
            "2026-01-31",
            "2026-12-31",
            "2024-02-29",  # Leap year
        ]

        for date in dates:
            entry_id = repo.add_entry(
                raw_input=f"日期测试{date}",
                category="测试",
                mood="neutral",
                metrics={},
                entry_date=date
            )
            self.assertIsNotNone(entry_id)

        # Query should find all
        entries = repo.get_entries_by_date_range("2024-01-01", "2026-12-31")
        self.assertGreaterEqual(len(entries), len(dates))


class TestDataIntegrity(unittest.TestCase):
    """Test data integrity and persistence."""

    def setUp(self):
        """Set up test database."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        settings.DB_PATH = self.db_path
        init_database()

    def tearDown(self):
        """Clean up temporary database."""
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_data_persistence(self):
        """Test data persists across repository instances."""
        # Add entry with first repository instance
        repo1 = HabitRepository()
        entry_id = repo1.add_entry(
            raw_input="持久化测试",
            category="测试",
            mood="neutral",
            metrics={}
        )

        # Create new repository instance (simulating restart)
        repo2 = HabitRepository()
        entry = repo2.get_entry_by_id(entry_id)

        self.assertIsNotNone(entry)
        self.assertEqual(entry["raw_input"], "持久化测试")

    def test_entry_update_doesnt_affect_others(self):
        """Test that operations on one entry don't affect others."""
        repo = HabitRepository()

        # Add multiple entries
        entry_id1 = repo.add_entry(
            raw_input="记录1",
            category="测试",
            mood="positive",
            metrics={}
        )

        entry_id2 = repo.add_entry(
            raw_input="记录2",
            category="测试",
            mood="negative",
            metrics={}
        )

        # Retrieve both
        entry1 = repo.get_entry_by_id(entry_id1)
        entry2 = repo.get_entry_by_id(entry_id2)

        # Verify they are distinct
        self.assertNotEqual(entry1["raw_input"], entry2["raw_input"])
        self.assertNotEqual(entry1["mood"], entry2["mood"])

    def test_statistics_accuracy(self):
        """Test statistics calculations are accurate."""
        repo = HabitRepository()

        # Use unique categories to avoid conflicts
        unique_cat1 = f"统计测试A_{id(self)}"
        unique_cat2 = f"统计测试B_{id(self)}"

        # Add known number of entries
        for i in range(10):
            repo.add_entry(
                raw_input=f"统计测试{i}",
                category=unique_cat1 if i % 2 == 0 else unique_cat2,
                mood="positive" if i % 3 == 0 else "neutral",
                metrics={}
            )

        # Get statistics with filter for our unique categories
        stats_all = repo.get_statistics()

        # Verify our categories are in the statistics
        self.assertIn(unique_cat1, stats_all["by_category"])
        self.assertIn(unique_cat2, stats_all["by_category"])

        # Verify counts for our specific categories
        self.assertEqual(stats_all["by_category"][unique_cat1], 5)
        self.assertEqual(stats_all["by_category"][unique_cat2], 5)


if __name__ == "__main__":
    unittest.main()
