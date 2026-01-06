"""
Unit tests for database layer.

Tests the schema and repository modules without requiring external dependencies.

Author: Trackit Development
"""

import unittest
import os
import tempfile
from src.database.schema import DatabaseSchema, init_database
from src.database.repository import HabitRepository


class TestDatabaseSchema(unittest.TestCase):
    """Test database schema creation and management."""

    def setUp(self):
        """Set up test database with temporary file."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.schema = DatabaseSchema(self.db_path)

    def tearDown(self):
        """Clean up temporary database file."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_create_schema(self):
        """Test that schema is created successfully."""
        self.schema.create_schema()
        info = self.schema.get_schema_info()
        self.assertIn('entries', info['tables'])
        self.assertIn('weekly_reports', info['tables'])

    def test_indexes_created(self):
        """Test that indexes are created."""
        self.schema.create_schema()
        info = self.schema.get_schema_info()
        # Should have indexes on date, category, mood
        index_names = info['indexes']
        self.assertTrue(any('date' in idx for idx in index_names))
        self.assertTrue(any('category' in idx for idx in index_names))
        self.assertTrue(any('mood' in idx for idx in index_names))


class TestHabitRepository(unittest.TestCase):
    """Test habit repository operations."""

    def setUp(self):
        """Set up test database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.schema = DatabaseSchema(self.db_path)
        self.schema.create_schema()
        self.repo = HabitRepository(self.db_path)

    def tearDown(self):
        """Clean up temporary database file."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_add_entry(self):
        """Test adding a new entry."""
        entry_id = self.repo.add_entry(
            raw_input="今天跑了5公里",
            category="运动",
            mood="positive",
            metrics={"distance_km": 5.0}
        )
        self.assertGreater(entry_id, 0)

    def test_get_entry_by_id(self):
        """Test retrieving an entry by ID."""
        entry_id = self.repo.add_entry(
            raw_input="今天跑了5公里",
            category="运动",
            mood="positive",
            metrics={"distance_km": 5.0}
        )
        entry = self.repo.get_entry_by_id(entry_id)
        self.assertIsNotNone(entry)
        self.assertEqual(entry['category'], '运动')
        self.assertEqual(entry['mood'], 'positive')
        self.assertEqual(entry['metrics']['distance_km'], 5.0)

    def test_get_entries_by_date(self):
        """Test retrieving entries by date."""
        # Add multiple entries for the same date
        date = "2026-01-10"
        self.repo.add_entry(
            raw_input="今天跑了5公里",
            category="运动",
            mood="positive",
            metrics={"distance_km": 5.0},
            entry_date=date
        )
        self.repo.add_entry(
            raw_input="今天学习了2小时",
            category="学习",
            mood="neutral",
            metrics={"duration_min": 120},
            entry_date=date
        )

        entries = self.repo.get_entries_by_date(date)
        self.assertEqual(len(entries), 2)

    def test_get_statistics(self):
        """Test getting statistics."""
        # Add some test data
        self.repo.add_entry(
            raw_input="今天跑了5公里",
            category="运动",
            mood="positive",
            metrics={"distance_km": 5.0}
        )
        self.repo.add_entry(
            raw_input="今天心情不好",
            category="情绪",
            mood="negative",
            metrics={}
        )

        stats = self.repo.get_statistics()
        self.assertEqual(stats['total_entries'], 2)
        self.assertIn('运动', stats['by_category'])
        self.assertIn('情绪', stats['by_category'])


class TestDatabaseIntegration(unittest.TestCase):
    """Integration tests for database operations."""

    def setUp(self):
        """Set up test database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.db_path = self.temp_db.name

    def tearDown(self):
        """Clean up temporary database file."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_full_workflow(self):
        """Test complete workflow: init, add, retrieve."""
        # Initialize
        schema = init_database(self.db_path)
        repo = HabitRepository(self.db_path)

        # Add entry
        entry_id = repo.add_entry(
            raw_input="今天跑了5公里，感觉不错",
            category="运动",
            mood="positive",
            metrics={"distance_km": 5.0, "duration_min": 30}
        )

        # Retrieve
        entry = repo.get_entry_by_id(entry_id)
        self.assertEqual(entry['category'], '运动')
        self.assertEqual(entry['metrics']['distance_km'], 5.0)

        # Get stats
        stats = repo.get_statistics()
        self.assertEqual(stats['total_entries'], 1)


if __name__ == '__main__':
    unittest.main()
