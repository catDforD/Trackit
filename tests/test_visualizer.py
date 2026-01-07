"""
Unit tests for visualization module.

Tests for HabitVisualizer including:
- Matplotlib static visualizations
- Plotly interactive visualizations
- Data export functions

Author: Trackit Development
"""

import unittest
import tempfile
import os
from datetime import datetime, timedelta

import matplotlib.pyplot as plt

from src.analysis.visualizer import HabitVisualizer
from src.database.repository import HabitRepository
from src.database.schema import DatabaseSchema


class TestHabitVisualizer(unittest.TestCase):
    """Test cases for HabitVisualizer class."""

    def setUp(self):
        """Set up test fixtures with temporary database."""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
        self.temp_db.close()

        # Initialize database schema
        self.schema = DatabaseSchema(self.temp_db.name)
        self.schema.create_schema()

        # Create repository and visualizer
        self.repository = HabitRepository(self.temp_db.name)
        self.visualizer = HabitVisualizer(repository=self.repository)

        # Add test data
        self._add_test_data()

    def tearDown(self):
        """Clean up temporary database and close figures."""
        if os.path.exists(self.temp_db.name):
            os.remove(self.temp_db.name)

        # Close all matplotlib figures
        plt.close('all')

    def _add_test_data(self):
        """Add sample test data to the database."""
        base_date = datetime.now() - timedelta(days=14)

        # Add 2 weeks of sample data
        for day in range(14):
            current_date = (base_date + timedelta(days=day)).strftime('%Y-%m-%d')

            # Add entries with different categories and moods
            categories = ['运动', '学习', '睡眠', '情绪']
            moods = ['positive', 'neutral', 'negative']

            for i in range(2):
                self.repository.add_entry(
                    raw_input=f"Test entry {day}-{i}",
                    category=categories[day % len(categories)],
                    mood=moods[day % len(moods)],
                    metrics={"value": day * 10 + i, "distance_km": day % 5 + 1},
                    entry_date=current_date
                )

    def test_initialization(self):
        """Test visualizer initialization."""
        self.assertIsNotNone(self.visualizer.repository)
        self.assertIsNotNone(self.visualizer.analyzer)

    def test_plot_weekly_summary_basic(self):
        """Test basic weekly summary chart creation."""
        fig = self.visualizer.plot_weekly_summary()

        self.assertIsInstance(fig, plt.Figure)
        self.assertIsNotNone(fig)

        # Should have 2x2 subplots
        axes = fig.get_axes()
        self.assertEqual(len(axes), 4)

    def test_plot_weekly_summary_with_week(self):
        """Test weekly summary with specific week."""
        current_week = datetime.now().strftime('%Y-W%W')
        fig = self.visualizer.plot_weekly_summary(week_iso=current_week)

        self.assertIsInstance(fig, plt.Figure)

    def test_plot_weekly_summary_empty_week(self):
        """Test weekly summary with future week (no data)."""
        future_week = "2030-W01"
        fig = self.visualizer.plot_weekly_summary(week_iso=future_week)

        self.assertIsInstance(fig, plt.Figure)
        # Should create a figure even with no data

    def test_plot_weekly_summary_save(self):
        """Test saving weekly summary chart."""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            fig = self.visualizer.plot_weekly_summary(save_path=tmp_path)

            # Check if file was created
            self.assertTrue(os.path.exists(tmp_path))
            self.assertGreater(os.path.getsize(tmp_path), 0)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_plot_comparison_basic(self):
        """Test basic period comparison chart."""
        # Use two consecutive weeks
        current_week = datetime.now().strftime('%Y-W%W')
        last_week_num = datetime.now().isocalendar()[1] - 1
        last_week = f"{datetime.now().year}-W{last_week_num:02d}"

        fig = self.visualizer.plot_comparison(last_week, current_week)

        self.assertIsInstance(fig, plt.Figure)
        # Should have 2x2 subplots
        axes = fig.get_axes()
        self.assertEqual(len(axes), 4)

    def test_plot_comparison_with_category(self):
        """Test period comparison with category filter."""
        current_week = datetime.now().strftime('%Y-W%W')
        last_week_num = datetime.now().isocalendar()[1] - 1
        last_week = f"{datetime.now().year}-W{last_week_num:02d}"

        fig = self.visualizer.plot_comparison(
            last_week,
            current_week,
            category='运动'
        )

        self.assertIsInstance(fig, plt.Figure)

    def test_plot_comparison_save(self):
        """Test saving comparison chart."""
        current_week = datetime.now().strftime('%Y-W%W')
        last_week_num = datetime.now().isocalendar()[1] - 1
        last_week = f"{datetime.now().year}-W{last_week_num:02d}"

        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            fig = self.visualizer.plot_comparison(
                last_week, current_week,
                save_path=tmp_path
            )

            # Check if file was created
            self.assertTrue(os.path.exists(tmp_path))
            self.assertGreater(os.path.getsize(tmp_path), 0)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_plot_trend_basic(self):
        """Test basic trend chart."""
        fig = self.visualizer.plot_trend(weeks=2)

        self.assertIsInstance(fig, plt.Figure)
        # Should have 1 subplot
        axes = fig.get_axes()
        self.assertEqual(len(axes), 1)

    def test_plot_trend_with_category(self):
        """Test trend chart with category filter."""
        fig = self.visualizer.plot_trend(
            category='运动',
            weeks=2
        )

        self.assertIsInstance(fig, plt.Figure)

    def test_plot_trend_with_metric(self):
        """Test trend chart with specific metric."""
        fig = self.visualizer.plot_trend(
            category='运动',
            metric='distance_km',
            weeks=2
        )

        self.assertIsInstance(fig, plt.Figure)

    def test_plot_trend_save(self):
        """Test saving trend chart."""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            fig = self.visualizer.plot_trend(weeks=2, save_path=tmp_path)

            # Check if file was created
            self.assertTrue(os.path.exists(tmp_path))
            self.assertGreater(os.path.getsize(tmp_path), 0)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_plot_weekly_summary_interactive(self):
        """Test interactive weekly summary chart."""
        fig = self.visualizer.plot_weekly_summary_interactive()

        self.assertIsNotNone(fig)
        self.assertEqual(type(fig).__name__, 'Figure')

    def test_plot_weekly_summary_interactive_with_week(self):
        """Test interactive weekly summary with specific week."""
        current_week = datetime.now().strftime('%Y-W%W')
        fig = self.visualizer.plot_weekly_summary_interactive(week_iso=current_week)

        self.assertIsNotNone(fig)

    def test_plot_trend_interactive(self):
        """Test interactive trend chart."""
        fig = self.visualizer.plot_trend_interactive(weeks=2)

        self.assertIsNotNone(fig)
        self.assertEqual(type(fig).__name__, 'Figure')

    def test_plot_trend_interactive_with_category(self):
        """Test interactive trend chart with category."""
        fig = self.visualizer.plot_trend_interactive(
            category='运动',
            weeks=2
        )

        self.assertIsNotNone(fig)

    def test_fig_to_base64(self):
        """Test converting figure to base64."""
        fig = self.visualizer.plot_weekly_summary()
        b64_string = self.visualizer.fig_to_base64(fig)

        self.assertIsInstance(b64_string, str)
        self.assertGreater(len(b64_string), 0)
        # Base64 strings should only contain valid characters
        valid_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")
        self.assertTrue(all(c in valid_chars for c in b64_string))

    def test_export_chart_data(self):
        """Test exporting chart data."""
        data = self.visualizer.export_chart_data()

        self.assertIsInstance(data, dict)
        self.assertIn('week', data)
        self.assertIn('total_entries', data)
        self.assertIn('by_category', data)
        self.assertIn('mood_distribution', data)
        self.assertIn('export_timestamp', data)

    def test_export_chart_data_with_week(self):
        """Test exporting chart data for specific week."""
        current_week = datetime.now().strftime('%Y-W%W')
        data = self.visualizer.export_chart_data(week_iso=current_week)

        self.assertIsInstance(data, dict)
        self.assertEqual(data['week'], current_week)

    def test_multiple_figures_independence(self):
        """Test that multiple figures are independent."""
        fig1 = self.visualizer.plot_weekly_summary()
        fig2 = self.visualizer.plot_trend()

        # Figures should be different objects
        self.assertIsNot(fig1, fig2)

        # Each should have their own axes
        axes1 = fig1.get_axes()
        axes2 = fig2.get_axes()
        self.assertNotEqual(len(axes1), len(axes2))


class TestVisualizationIntegration(unittest.TestCase):
    """Integration tests for visualization with analysis modules."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
        self.temp_db.close()

        # Initialize database
        self.schema = DatabaseSchema(self.temp_db.name)
        self.schema.create_schema()

        self.repository = HabitRepository(self.temp_db.name)
        self.visualizer = HabitVisualizer(repository=self.repository)

        # Add comprehensive test data
        self._add_comprehensive_data()

    def tearDown(self):
        """Clean up temporary database and close figures."""
        if os.path.exists(self.temp_db.name):
            os.remove(self.temp_db.name)
        plt.close('all')

    def _add_comprehensive_data(self):
        """Add comprehensive test data spanning multiple weeks."""
        base_date = datetime.now() - timedelta(days=21)

        # Add 3 weeks of data with patterns
        for week in range(3):
            for day in range(7):
                current_date = (base_date + timedelta(days=week*7 + day))

                # Weekend: more exercise
                if current_date.weekday() >= 5:
                    self.repository.add_entry(
                        raw_input=f"Weekend workout W{week}D{day}",
                        category='运动',
                        mood='positive',
                        metrics={"distance_km": (week + 1) * 2},
                        entry_date=current_date.strftime('%Y-%m-%d')
                    )
                else:
                    # Weekday: study
                    self.repository.add_entry(
                        raw_input=f"Weekday study W{week}D{day}",
                        category='学习',
                        mood='neutral' if day % 2 == 0 else 'positive',
                        metrics={"duration_min": 60},
                        entry_date=current_date.strftime('%Y-%m-%d')
                    )

    def test_full_visualization_workflow(self):
        """Test complete visualization workflow."""
        # 1. Create weekly summary
        fig_weekly = self.visualizer.plot_weekly_summary()
        self.assertIsNotNone(fig_weekly)

        # 2. Create comparison chart
        week1 = (datetime.now() - timedelta(weeks=1)).strftime('%Y-W%W')
        week2 = datetime.now().strftime('%Y-W%W')
        fig_comparison = self.visualizer.plot_comparison(week1, week2)
        self.assertIsNotNone(fig_comparison)

        # 3. Create trend chart
        fig_trend = self.visualizer.plot_trend(weeks=3)
        self.assertIsNotNone(fig_trend)

        # 4. Create interactive versions
        fig_weekly_int = self.visualizer.plot_weekly_summary_interactive()
        self.assertIsNotNone(fig_weekly_int)

        fig_trend_int = self.visualizer.plot_trend_interactive(weeks=3)
        self.assertIsNotNone(fig_trend_int)

        # 5. Export data
        data = self.visualizer.export_chart_data()
        self.assertIsInstance(data, dict)

    def test_visualization_with_filtering(self):
        """Test visualizations with various filters."""
        # Test with category filter
        fig = self.visualizer.plot_weekly_summary()
        self.assertIsNotNone(fig)

        fig_trend = self.visualizer.plot_trend(category='运动', weeks=3)
        self.assertIsNotNone(fig_trend)

        # Test interactive with filters
        fig_int = self.visualizer.plot_trend_interactive(
            category='运动',
            metric='distance_km',
            weeks=3
        )
        self.assertIsNotNone(fig_int)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
