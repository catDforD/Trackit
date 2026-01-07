"""
Unit tests for analysis modules.

Tests for:
- TimeSeriesAnalyzer: Time-based statistics and trend analysis
- PatternDetector: Pattern recognition algorithms

Author: Trackit Development
"""

import unittest
import tempfile
import os
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pandas as pd
import numpy as np

from src.analysis.time_series import TimeSeriesAnalyzer
from src.analysis.patterns import PatternDetector
from src.database.repository import HabitRepository
from src.database.schema import DatabaseSchema


class TestTimeSeriesAnalyzer(unittest.TestCase):
    """Test cases for TimeSeriesAnalyzer class."""

    def setUp(self):
        """Set up test fixtures with temporary database."""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
        self.temp_db.close()

        # Initialize database schema
        self.schema = DatabaseSchema(self.temp_db.name)
        self.schema.create_schema()

        # Create repository and analyzer
        self.repository = HabitRepository(self.temp_db.name)
        self.analyzer = TimeSeriesAnalyzer(self.repository)

        # Add test data
        self._add_test_data()

    def tearDown(self):
        """Clean up temporary database."""
        if os.path.exists(self.temp_db.name):
            os.remove(self.temp_db.name)

    def _add_test_data(self):
        """Add sample test data to the database."""
        base_date = datetime.now() - timedelta(days=14)

        # Add 2 weeks of sample data
        for day in range(14):
            current_date = (base_date + timedelta(days=day)).strftime('%Y-%m-%d')

            # Add 2-3 entries per day
            for i in range(2):
                categories = ['运动', '学习', '睡眠', '情绪']
                moods = ['positive', 'neutral', 'negative']

                self.repository.add_entry(
                    raw_input=f"Test entry {day}-{i}",
                    category=categories[day % len(categories)],
                    mood=moods[day % len(moods)],
                    metrics={"value": day * 10 + i},
                    entry_date=current_date
                )

    def test_initialization(self):
        """Test analyzer initialization."""
        self.assertIsNotNone(self.analyzer.repository)
        self.assertIsInstance(self.analyzer.repository, HabitRepository)

    def test_entries_to_dataframe(self):
        """Test conversion of entries to DataFrame."""
        entries = self.repository.get_all_entries(limit=5)
        df = self.analyzer._entries_to_dataframe(entries)

        self.assertIsInstance(df, pd.DataFrame)
        self.assertGreater(len(df), 0)
        self.assertIn('date', df.columns)
        self.assertIn('category', df.columns)
        self.assertIn('mood', df.columns)

    def test_entries_to_dataframe_empty(self):
        """Test DataFrame conversion with empty data."""
        df = self.analyzer._entries_to_dataframe([])

        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 0)

    def test_weekly_statistics_basic(self):
        """Test basic weekly statistics."""
        stats = self.analyzer.weekly_statistics()

        self.assertIsInstance(stats, dict)
        self.assertIn('total_entries', stats)
        self.assertIn('by_category', stats)
        self.assertIn('mood_distribution', stats)
        self.assertGreater(stats['total_entries'], 0)

    def test_weekly_statistics_with_category_filter(self):
        """Test weekly statistics with category filter."""
        stats = self.analyzer.weekly_statistics(category='运动')

        self.assertIsInstance(stats, dict)
        # Should only have filtered category in by_category
        if stats['total_entries'] > 0:
            self.assertIn('运动', stats['by_category'])

    def test_weekly_statistics_empty_week(self):
        """Test weekly statistics with future week (no data)."""
        future_week = "2030-W01"
        stats = self.analyzer.weekly_statistics(week_iso=future_week)

        self.assertEqual(stats['total_entries'], 0)
        self.assertEqual(stats['by_category'], {})

    def test_trend_analysis_basic(self):
        """Test basic trend analysis."""
        trend = self.analyzer.trend_analysis(window=7, weeks=2)

        self.assertIsInstance(trend, dict)
        self.assertIn('daily_data', trend)
        self.assertIn('trend_direction', trend)
        self.assertIn('trend_strength', trend)
        self.assertIn('summary', trend)

        # Should have some data
        self.assertGreater(len(trend['daily_data']), 0)

    def test_trend_analysis_with_category(self):
        """Test trend analysis with category filter."""
        trend = self.analyzer.trend_analysis(
            category='运动',
            window=7,
            weeks=2
        )

        self.assertIsInstance(trend, dict)
        self.assertIn('trend_direction', trend)

    def test_trend_analysis_no_data(self):
        """Test trend analysis with period containing no data."""
        trend = self.analyzer.trend_analysis(weeks=0)

        # Should handle gracefully
        self.assertEqual(trend['trend_direction'], 'insufficient_data')

    def test_compare_periods_basic(self):
        """Test period comparison."""
        # Use two consecutive weeks
        current_week = datetime.now().strftime('%Y-W%W')
        last_week_num = datetime.now().isocalendar()[1] - 1
        last_week = f"{datetime.now().year}-W{last_week_num:02d}"

        comparison = self.analyzer.compare_periods(last_week, current_week)

        self.assertIsInstance(comparison, dict)
        self.assertIn('period1_stats', comparison)
        self.assertIn('period2_stats', comparison)
        self.assertIn('change', comparison)
        self.assertIn('improvement', comparison)

    def test_compare_periods_change_calculation(self):
        """Test change calculation in period comparison."""
        week1 = "2026-W01"
        week2 = "2026-W02"

        comparison = self.analyzer.compare_periods(week1, week2)

        # Should have change data
        self.assertIn('total_entries', comparison['change'])
        self.assertIn('total_entries_percent', comparison['change'])

    def test_compare_periods_with_category(self):
        """Test period comparison with category filter."""
        current_week = datetime.now().strftime('%Y-W%W')
        last_week_num = datetime.now().isocalendar()[1] - 1
        last_week = f"{datetime.now().year}-W{last_week_num:02d}"

        comparison = self.analyzer.compare_periods(
            last_week,
            current_week,
            category='运动'
        )

        self.assertIsInstance(comparison, dict)

    def test_get_daily_summary(self):
        """Test daily summary retrieval."""
        summary = self.analyzer.get_daily_summary(days=7)

        self.assertIsInstance(summary, list)
        self.assertEqual(len(summary), 7)  # Should have exactly 7 days

        # Check structure of first day
        if len(summary) > 0:
            self.assertIn('date', summary[0])
            self.assertIn('count', summary[0])
            self.assertIn('categories', summary[0])
            self.assertIn('moods', summary[0])

    def test_get_daily_summary_with_category(self):
        """Test daily summary with category filter."""
        summary = self.analyzer.get_daily_summary(days=7, category='运动')

        self.assertIsInstance(summary, list)
        self.assertEqual(len(summary), 7)


class TestPatternDetector(unittest.TestCase):
    """Test cases for PatternDetector class."""

    def setUp(self):
        """Set up test fixtures with temporary database."""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
        self.temp_db.close()

        # Initialize database schema
        self.schema = DatabaseSchema(self.temp_db.name)
        self.schema.create_schema()

        # Create repository and detector
        self.repository = HabitRepository(self.temp_db.name)
        self.detector = PatternDetector(repository=self.repository)

        # Add test data
        self._add_test_data()

    def tearDown(self):
        """Clean up temporary database."""
        if os.path.exists(self.temp_db.name):
            os.remove(self.temp_db.name)

    def _add_test_data(self):
        """Add sample test data with patterns."""
        base_date = datetime.now() - timedelta(days=21)

        # Add 3 weeks of data with patterns
        for day in range(21):
            current_date = (base_date + timedelta(days=day))
            date_str = current_date.strftime('%Y-%m-%d')

            # Weekend pattern: more exercise on weekends
            is_weekend = current_date.weekday() >= 5

            if is_weekend:
                # Add exercise on weekends with positive mood
                self.repository.add_entry(
                    raw_input=f"Weekend workout {day}",
                    category='运动',
                    mood='positive',
                    metrics={"distance_km": 5.0},
                    entry_date=date_str
                )
            else:
                # Add study on weekdays
                self.repository.add_entry(
                    raw_input=f"Weekday study {day}",
                    category='学习',
                    mood='neutral' if day % 3 != 0 else 'positive',
                    metrics={"duration_min": 60},
                    entry_date=date_str
                )

    def test_initialization(self):
        """Test detector initialization."""
        self.assertIsNotNone(self.detector.repository)
        self.assertIsNotNone(self.detector.analyzer)

    def test_detect_day_of_week_patterns_basic(self):
        """Test basic day-of-week pattern detection."""
        patterns = self.detector.detect_day_of_week_patterns(weeks=3)

        self.assertIsInstance(patterns, dict)
        self.assertIn('best_day', patterns)
        self.assertIn('worst_day', patterns)
        self.assertIn('most_active_day', patterns)
        self.assertIn('day_analysis', patterns)
        self.assertIn('patterns', patterns)

    def test_detect_day_of_week_patterns_with_category(self):
        """Test day-of-week patterns with category filter."""
        patterns = self.detector.detect_day_of_week_patterns(
            weeks=3,
            category='运动'
        )

        self.assertIsInstance(patterns, dict)
        self.assertIsNotNone(patterns['most_active_day'])

    def test_detect_day_of_week_patterns_no_data(self):
        """Test pattern detection with no data."""
        patterns = self.detector.detect_day_of_week_patterns(weeks=0)

        # Should handle gracefully
        self.assertEqual(patterns['best_day'], None)
        self.assertEqual(len(patterns['patterns']), 0)

    def test_detect_streaks_basic(self):
        """Test basic streak detection."""
        streaks = self.detector.detect_streaks(days=21)

        self.assertIsInstance(streaks, dict)
        self.assertIn('current_streak', streaks)
        self.assertIn('longest_streak', streaks)
        self.assertIn('streak_history', streaks)
        self.assertIn('streak_dates', streaks)

    def test_detect_streaks_with_category(self):
        """Test streak detection with category filter."""
        streaks = self.detector.detect_streaks(
            category='运动',
            days=21
        )

        self.assertIsInstance(streaks, dict)
        self.assertGreaterEqual(streaks['current_streak'], 0)

    def test_detect_streaks_no_data(self):
        """Test streak detection with no data."""
        streaks = self.detector.detect_streaks(days=0)

        self.assertEqual(streaks['current_streak'], 0)
        self.assertEqual(streaks['longest_streak'], 0)

    def test_detect_correlations_basic(self):
        """Test basic correlation detection."""
        correlations = self.detector.detect_correlations(weeks=3)

        self.assertIsInstance(correlations, dict)
        self.assertIn('correlations', correlations)
        self.assertIn('mood_after_activity', correlations)
        self.assertIn('activity_pairs', correlations)

    def test_detect_correlations_mood_analysis(self):
        """Test mood analysis after activities."""
        correlations = self.detector.detect_correlations(weeks=3)

        mood_after = correlations['mood_after_activity']
        self.assertIsInstance(mood_after, dict)

        # Check structure of mood data
        for activity, data in mood_after.items():
            self.assertIn('total', data)
            self.assertIn('positive', data)
            self.assertIn('positive_rate', data)

    def test_get_insights_basic(self):
        """Test comprehensive insight generation."""
        insights = self.detector.get_insights(weeks=2)

        self.assertIsInstance(insights, dict)
        self.assertIn('summary', insights)
        self.assertIn('day_patterns', insights)
        self.assertIn('streaks', insights)
        self.assertIn('correlations', insights)
        self.assertIn('recommendations', insights)

    def test_get_insights_structure(self):
        """Test structure of insights output."""
        insights = self.detector.get_insights(weeks=2)

        # Summary should be a string
        self.assertIsInstance(insights['summary'], str)

        # Recommendations should be a list
        self.assertIsInstance(insights['recommendations'], list)

        # Each recommendation should be a string
        for rec in insights['recommendations']:
            self.assertIsInstance(rec, str)


class TestAnalysisIntegration(unittest.TestCase):
    """Integration tests for analysis modules."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
        self.temp_db.close()

        # Initialize database
        self.schema = DatabaseSchema(self.temp_db.name)
        self.schema.create_schema()

        self.repository = HabitRepository(self.temp_db.name)
        self.analyzer = TimeSeriesAnalyzer(self.repository)
        self.detector = PatternDetector(self.repository)

    def tearDown(self):
        """Clean up temporary database."""
        if os.path.exists(self.temp_db.name):
            os.remove(self.temp_db.name)

    def test_full_analysis_workflow(self):
        """Test complete analysis workflow."""
        # Add test data
        base_date = datetime.now() - timedelta(days=14)

        for day in range(14):
            date_str = (base_date + timedelta(days=day)).strftime('%Y-%m-%d')

            # Add entries
            for i in range(2):
                self.repository.add_entry(
                    raw_input=f"Entry {day}-{i}",
                    category='运动' if day % 2 == 0 else '学习',
                    mood='positive' if i % 2 == 0 else 'neutral',
                    metrics={"value": day * 10 + i},
                    entry_date=date_str
                )

        # Run all analyses
        stats = self.analyzer.weekly_statistics()
        trend = self.analyzer.trend_analysis(window=7, weeks=2)
        patterns = self.detector.detect_day_of_week_patterns(weeks=2)
        streaks = self.detector.detect_streaks(days=14)

        # Verify all succeed
        self.assertGreater(stats['total_entries'], 0)
        self.assertGreater(len(trend['daily_data']), 0)
        self.assertIsNotNone(patterns['best_day'])
        self.assertGreaterEqual(streaks['current_streak'], 0)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
