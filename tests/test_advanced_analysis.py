"""
Unit tests for advanced analysis features.

Tests for:
- DataExporter: CSV/JSON export functionality
- AnalysisAgent: Advanced query processing
- Complex queries and filters

Author: Trackit Development
"""

import unittest
import tempfile
import os
import json
import csv
from datetime import datetime, timedelta

from src.analysis.exporter import DataExporter
from src.agents.analysis_agent import AnalysisAgent
from src.database.repository import HabitRepository
from src.database.schema import DatabaseSchema


class TestDataExporter(unittest.TestCase):
    """Test cases for DataExporter class."""

    def setUp(self):
        """Set up test fixtures with temporary database."""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
        self.temp_db.close()

        # Initialize database schema
        self.schema = DatabaseSchema(self.temp_db.name)
        self.schema.create_schema()

        # Create repository and exporter
        self.repository = HabitRepository(self.temp_db.name)
        self.exporter = DataExporter(repository=self.repository)

        # Add test data
        self._add_test_data()

    def tearDown(self):
        """Clean up temporary database and export files."""
        if os.path.exists(self.temp_db.name):
            os.remove(self.temp_db.name)

        # Clean up test export files
        for fname in ['test_export.csv', 'test_export.json', 'test_export_sport.csv']:
            if os.path.exists(fname):
                os.remove(fname)

    def _add_test_data(self):
        """Add sample test data to the database."""
        base_date = datetime.now() - timedelta(days=10)

        for day in range(10):
            current_date = (base_date + timedelta(days=day)).strftime('%Y-%m-%d')

            self.repository.add_entry(
                raw_input=f"Test entry {day}",
                category='运动' if day % 2 == 0 else '学习',
                mood='positive' if day % 3 == 0 else 'neutral',
                metrics={"value": day * 10, "distance_km": day % 5 + 1},
                entry_date=current_date
            )

    def test_initialization(self):
        """Test exporter initialization."""
        self.assertIsNotNone(self.exporter.repository)

    def test_to_csv_basic(self):
        """Test basic CSV export."""
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            count = self.exporter.to_csv(tmp_path)

            self.assertGreater(count, 0)
            self.assertTrue(os.path.exists(tmp_path))
            self.assertGreater(os.path.getsize(tmp_path), 0)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_to_csv_with_filters(self):
        """Test CSV export with filters."""
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            count = self.exporter.to_csv(tmp_path, category='运动')

            # Verify file was created
            self.assertTrue(os.path.exists(tmp_path))

            # Verify CSV content
            with open(tmp_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                for row in rows:
                    self.assertEqual(row['category'], '运动')
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_to_json_basic(self):
        """Test basic JSON export."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            count = self.exporter.to_json(tmp_path)

            self.assertGreater(count, 0)
            self.assertTrue(os.path.exists(tmp_path))
            self.assertGreater(os.path.getsize(tmp_path), 0)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_to_json_structure(self):
        """Test JSON export structure."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            self.exporter.to_json(tmp_path)

            # Read and verify JSON structure
            with open(tmp_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.assertIn('export_info', data)
            self.assertIn('entries', data)
            self.assertIsInstance(data['entries'], list)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_to_dict(self):
        """Test export to dictionary format."""
        data = self.exporter.to_dict()

        self.assertIn('summary', data)
        self.assertIn('entries', data)
        self.assertIsInstance(data['entries'], list)
        self.assertGreater(len(data['entries']), 0)

    def test_to_dict_with_filters(self):
        """Test export to dict with filters."""
        data = self.exporter.to_dict(category='运动')

        # Verify filtering worked
        for entry in data['entries']:
            self.assertEqual(entry['category'], '运动')

    def test_to_dataframe_dict(self):
        """Test export in DataFrame-ready format."""
        data = self.exporter.to_dataframe_dict()

        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

        # Check that metrics are flattened
        first_entry = data[0]
        self.assertIn('id', first_entry)
        self.assertIn('category', first_entry)

    def test_export_with_date_range(self):
        """Test export with date range filter."""
        base_date = datetime.now() - timedelta(days=10)
        start_date = (base_date + timedelta(days=2)).strftime('%Y-%m-%d')
        end_date = (base_date + timedelta(days=5)).strftime('%Y-%m-%d')

        count = self.exporter.to_csv("test_date_range.csv",
                                     start_date=start_date,
                                     end_date=end_date)

        self.assertGreater(count, 0)

        # Clean up
        if os.path.exists("test_date_range.csv"):
            os.remove("test_date_range.csv")


class TestAnalysisAgent(unittest.TestCase):
    """Test cases for AnalysisAgent class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
        self.temp_db.close()

        # Initialize database
        self.schema = DatabaseSchema(self.temp_db.name)
        self.schema.create_schema()

        self.repository = HabitRepository(self.temp_db.name)
        self.agent = AnalysisAgent(repository=self.repository)

        # Add test data
        self._add_test_data()

    def tearDown(self):
        """Clean up temporary database."""
        if os.path.exists(self.temp_db.name):
            os.remove(self.temp_db.name)

    def _add_test_data(self):
        """Add sample test data."""
        base_date = datetime.now() - timedelta(days=14)

        for day in range(14):
            current_date = (base_date + timedelta(days=day)).strftime('%Y-%m-%d')

            # Weekend: exercise, Weekday: study
            is_weekend = (base_date + timedelta(days=day)).weekday() >= 5

            self.repository.add_entry(
                raw_input=f"Entry {day}",
                category='运动' if is_weekend else '学习',
                mood='positive' if day % 2 == 0 else 'neutral',
                metrics={"value": day * 10},
                entry_date=current_date
            )

    def test_initialization(self):
        """Test agent initialization."""
        self.assertIsNotNone(self.agent.repository)
        self.assertIsNotNone(self.agent.analyzer)
        self.assertIsNotNone(self.agent.detector)
        self.assertIsNotNone(self.agent.visualizer)
        self.assertIsNotNone(self.agent.exporter)

    def test_pattern_query(self):
        """Test pattern detection query."""
        result = self.agent.execute("有什么规律吗？")

        self.assertTrue(result['success'])
        self.assertIn('response', result)
        self.assertIn('data', result)

    def test_trend_query(self):
        """Test trend analysis query."""
        result = self.agent.execute("最近趋势怎么样？")

        self.assertTrue(result['success'])
        self.assertIn('response', result)
        self.assertIn('data', result)

    def test_insights_query(self):
        """Test comprehensive insights query."""
        result = self.agent.execute("给我一些分析和建议")

        self.assertTrue(result['success'])
        self.assertIn('response', result)
        self.assertIn('data', result)

    def test_export_query(self):
        """Test data export query."""
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = self.agent.execute("导出数据", filename=tmp_path)

            self.assertTrue(result['success'])
            self.assertIn('count', result['data'])
            self.assertTrue(os.path.exists(tmp_path))
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_custom_query_with_filters(self):
        """Test custom query with filters."""
        result = self.agent.execute(
            "查询数据",
            category='运动'
        )

        self.assertTrue(result['success'])
        self.assertIn('response', result)

    def test_get_analysis_report(self):
        """Test comprehensive analysis report."""
        report = self.agent.get_analysis_report(weeks=2)

        self.assertIn('generated_at', report)
        self.assertIn('weekly_statistics', report)
        self.assertIn('patterns', report)
        self.assertIn('streaks', report)
        self.assertIn('trends', report)
        self.assertIn('insights', report)


class TestAdvancedAnalysisIntegration(unittest.TestCase):
    """Integration tests for advanced analysis features."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
        self.temp_db.close()

        # Initialize database
        self.schema = DatabaseSchema(self.temp_db.name)
        self.schema.create_schema()

        self.repository = HabitRepository(self.temp_db.name)
        self.agent = AnalysisAgent(repository=self.repository)
        self.exporter = DataExporter(repository=self.repository)

        # Add comprehensive test data
        self._add_comprehensive_data()

    def tearDown(self):
        """Clean up temporary database and files."""
        if os.path.exists(self.temp_db.name):
            os.remove(self.temp_db.name)

        for fname in ['test_integration.csv', 'test_integration.json']:
            if os.path.exists(fname):
                os.remove(fname)

    def _add_comprehensive_data(self):
        """Add comprehensive test data."""
        base_date = datetime.now() - timedelta(days=21)

        for week in range(3):
            for day in range(7):
                current_date = (base_date + timedelta(days=week*7 + day))

                # Create pattern: weekend exercise
                if current_date.weekday() >= 5:
                    self.repository.add_entry(
                        raw_input=f"Weekend workout W{week}D{day}",
                        category='运动',
                        mood='positive',
                        metrics={"distance_km": (week + 1) * 2},
                        entry_date=current_date.strftime('%Y-%m-%d')
                    )
                else:
                    self.repository.add_entry(
                        raw_input=f"Weekday study W{week}D{day}",
                        category='学习',
                        mood='neutral',
                        metrics={"duration_min": 60},
                        entry_date=current_date.strftime('%Y-%m-%d')
                    )

    def test_full_export_and_analysis_workflow(self):
        """Test complete export and analysis workflow."""
        # 1. Export data
        csv_count = self.exporter.to_csv("test_integration.csv")
        self.assertGreater(csv_count, 0)

        json_count = self.exporter.to_json("test_integration.json")
        self.assertEqual(csv_count, json_count)

        # 2. Analyze patterns
        result = self.agent.execute("有什么规律吗？")
        self.assertTrue(result['success'])

        # 3. Get comprehensive report
        report = self.agent.get_analysis_report(weeks=3)
        self.assertEqual(report['period_weeks'], 3)

        # 4. Export with filters
        filtered_count = self.exporter.to_dict(category='运动')
        self.assertGreater(filtered_count['summary']['total_entries'], 0)

    def test_multiple_query_types(self):
        """Test multiple query types in sequence."""
        queries = [
            "有什么规律吗？",
            "最近趋势怎么样？",
            "给我一些分析和建议"
        ]

        for query in queries:
            result = self.agent.execute(query)
            self.assertTrue(result['success'], f"Query failed: {query}")
            self.assertIn('response', result)

    def test_export_format_consistency(self):
        """Test that different export formats contain consistent data."""
        # Export to both formats
        dict_data = self.exporter.to_dict()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            self.exporter.to_json(tmp_path)

            with open(tmp_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)

            # Compare entry counts
            self.assertEqual(
                dict_data['summary']['total_entries'],
                json_data['export_info']['total_entries']
            )
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
