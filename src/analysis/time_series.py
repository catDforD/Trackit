"""
Time series analysis module for Trackit.

This module provides time-based statistical analysis and trend detection
for habit tracking data using Pandas.

Key Features:
- Weekly statistics aggregation
- Trend analysis with moving averages
- Period-over-period comparison
- Time-based filtering and grouping

Author: Trackit Development
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date, timedelta
from collections import defaultdict

from src.database.repository import HabitRepository


class TimeSeriesAnalyzer:
    """
    Time series analyzer for habit tracking data.

    This class provides methods for analyzing temporal patterns in habit data,
    including weekly statistics, trend analysis, and period comparisons.

    Attributes:
        repository: HabitRepository instance for data access

    Example:
        >>> analyzer = TimeSeriesAnalyzer()
        >>> stats = analyzer.weekly_statistics(category="运动")
        >>> print(stats["total_count"])
        15
    """

    def __init__(self, repository: Optional[HabitRepository] = None):
        """
        Initialize the time series analyzer.

        Args:
            repository: HabitRepository instance. If None, creates a new one.
        """
        self.repository = repository or HabitRepository()

    def _entries_to_dataframe(
        self,
        entries: List[Dict[str, Any]]
    ) -> pd.DataFrame:
        """
        Convert database entries to a Pandas DataFrame.

        Args:
            entries: List of entry dictionaries from the database

        Returns:
            DataFrame with parsed datetime and metrics columns
        """
        if not entries:
            return pd.DataFrame()

        # Convert to DataFrame
        df = pd.DataFrame(entries)

        # Parse date column
        df['date'] = pd.to_datetime(df['date'])

        # Extract metrics from JSON
        metrics_df = pd.json_normalize(df['metrics'])
        df = pd.concat([df.drop('metrics', axis=1), metrics_df], axis=1)

        # Add useful time columns
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month
        df['week'] = df['date'].dt.isocalendar().week
        df['day_of_week'] = df['date'].dt.dayofweek
        df['day_name'] = df['date'].dt.day_name()
        df['iso_week'] = df['date'].dt.strftime('%Y-W%W')

        return df

    def weekly_statistics(
        self,
        week_iso: Optional[str] = None,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate weekly statistics for habit entries.

        Args:
            week_iso: ISO week string (e.g., "2026-W02"). If None, uses current week.
            category: Optional category filter (e.g., "运动", "学习")

        Returns:
            Dictionary containing:
                - week: ISO week identifier
                - total_entries: Total number of entries
                - by_category: Count per category
                - by_day: Count per day of week
                - mood_distribution: Mood counts (positive/neutral/negative)
                - metrics_summary: Summary of numerical metrics
                - entries: List of entry data

        Example:
            >>> stats = analyzer.weekly_statistics(week_iso="2026-W02")
            >>> print(f"Total entries: {stats['total_entries']}")
            Total entries: 23
        """
        # Use current week if not specified
        if week_iso is None:
            week_iso = datetime.now().strftime('%Y-W%W')

        # Get entries for the week
        entries = self.repository.get_entries_by_week(week_iso)

        if not entries:
            return {
                "week": week_iso,
                "total_entries": 0,
                "by_category": {},
                "by_day": {},
                "mood_distribution": {},
                "metrics_summary": {},
                "entries": []
            }

        # Convert to DataFrame
        df = self._entries_to_dataframe(entries)

        # Basic statistics
        result = {
            "week": week_iso,
            "total_entries": len(df),
        }

        # Count by category
        if category:
            df_filtered = df[df['category'] == category]
            result['by_category'] = {category: len(df_filtered)}
        else:
            result['by_category'] = df['category'].value_counts().to_dict()

        # Count by day of week
        by_day = df.groupby('day_name')['category'].count().to_dict()
        # Reorder by day of week
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        result['by_day'] = {
            day: by_day.get(day, 0) for day in day_order if day in by_day
        }

        # Mood distribution
        result['mood_distribution'] = df['mood'].value_counts().to_dict()

        # Metrics summary (numerical columns)
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        metrics_summary = {}

        for col in numeric_cols:
            if col not in ['id', 'year', 'month', 'week', 'day_of_week']:
                try:
                    metrics_summary[col] = {
                        'count': df[col].notna().sum(),
                        'mean': float(df[col].mean()) if df[col].notna().any() else None,
                        'sum': float(df[col].sum()) if df[col].notna().any() else None,
                        'min': float(df[col].min()) if df[col].notna().any() else None,
                        'max': float(df[col].max()) if df[col].notna().any() else None,
                    }
                except (TypeError, ValueError):
                    pass

        result['metrics_summary'] = metrics_summary

        # Include raw entries for reference
        result['entries'] = entries

        return result

    def trend_analysis(
        self,
        category: Optional[str] = None,
        metric: Optional[str] = None,
        window: int = 7,
        weeks: int = 4
    ) -> Dict[str, Any]:
        """
        Analyze trends over time using moving averages.

        Args:
            category: Optional category filter
            metric: Specific metric to analyze (e.g., "distance_km")
            window: Moving average window size in days
            weeks: Number of weeks to analyze

        Returns:
            Dictionary containing:
                - daily_data: Daily values and moving averages
                - trend_direction: 'increasing', 'decreasing', or 'stable'
                - trend_strength: Coefficient of determination (R²)
                - summary: Statistical summary

        Example:
            >>> trend = analyzer.trend_analysis(
            ...     category="运动",
            ...     metric="distance_km",
            ...     window=7
            ... )
            >>> print(f"Trend: {trend['trend_direction']}")
            Trend: increasing
        """
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(weeks=weeks)

        # Get entries
        entries = self.repository.get_entries_by_date_range(
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            category=category
        )

        if not entries:
            return {
                "daily_data": [],
                "trend_direction": "insufficient_data",
                "trend_strength": 0,
                "summary": {}
            }

        # Convert to DataFrame
        df = self._entries_to_dataframe(entries)

        # Group by date
        if metric and metric in df.columns:
            # Sum the metric per day
            daily = df.groupby('date')[metric].sum().reset_index()
        else:
            # Count entries per day
            daily = df.groupby('date').size().reset_index(name='count')
            metric = 'count'

        # Rename metric column to 'value'
        daily = daily.rename(columns={metric: 'value'})

        # Calculate moving average
        daily['moving_avg'] = daily['value'].rolling(
            window=window,
            min_periods=1
        ).mean()

        # Calculate trend direction using linear regression
        if len(daily) >= 2:
            x = np.arange(len(daily))
            y = daily['value'].values

            # Simple linear regression
            coefficients = np.polyfit(x, y, 1)
            slope = coefficients[0]

            # Calculate R-squared
            y_pred = np.polyval(coefficients, x)
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

            # Determine trend direction
            if abs(slope) < 0.01:
                trend_direction = "stable"
            elif slope > 0:
                trend_direction = "increasing"
            else:
                trend_direction = "decreasing"
        else:
            trend_direction = "insufficient_data"
            r_squared = 0

        # Prepare daily data for output
        daily_data = []
        for _, row in daily.iterrows():
            daily_data.append({
                "date": row['date'].strftime('%Y-%m-%d'),
                "value": float(row['value']) if pd.notna(row['value']) else None,
                "moving_avg": float(row['moving_avg']) if pd.notna(row['moving_avg']) else None,
            })

        return {
            "daily_data": daily_data,
            "trend_direction": trend_direction,
            "trend_strength": float(r_squared),
            "summary": {
                "metric": metric,
                "window_days": window,
                "period_days": len(daily),
                "mean_value": float(daily['value'].mean()) if len(daily) > 0 else 0,
                "max_value": float(daily['value'].max()) if len(daily) > 0 else 0,
                "min_value": float(daily['value'].min()) if len(daily) > 0 else 0,
            }
        }

    def compare_periods(
        self,
        period1: str,
        period2: str,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compare statistics between two periods (e.g., weeks).

        Args:
            period1: ISO week string for period 1 (e.g., "2026-W01")
            period2: ISO week string for period 2 (e.g., "2026-W02")
            category: Optional category filter

        Returns:
            Dictionary containing:
                - period1_stats: Statistics for period 1
                - period2_stats: Statistics for period 2
                - change: Absolute and percentage changes
                - improvement: Boolean indicating if metrics improved

        Example:
            >>> comparison = analyzer.compare_periods("2026-W01", "2026-W02")
            >>> print(f"Entries increased by {comparison['change']['total_entries_percent']}%")
            Entries increased by 25.0%
        """
        # Get statistics for both periods
        stats1 = self.weekly_statistics(week_iso=period1, category=category)
        stats2 = self.weekly_statistics(week_iso=period2, category=category)

        # Calculate changes
        change = {}
        improvement = {}

        # Compare total entries
        count1 = stats1['total_entries']
        count2 = stats2['total_entries']

        change['total_entries'] = count2 - count1
        change['total_entries_percent'] = (
            ((count2 - count1) / count1 * 100) if count1 > 0 else 0
        )

        # Compare by category
        all_categories = set(
            list(stats1.get('by_category', {}).keys()) +
            list(stats2.get('by_category', {}).keys())
        )

        change['by_category'] = {}
        for cat in all_categories:
            count1_cat = stats1.get('by_category', {}).get(cat, 0)
            count2_cat = stats2.get('by_category', {}).get(cat, 0)

            change['by_category'][cat] = {
                'absolute': count2_cat - count1_cat,
                'percent': ((count2_cat - count1_cat) / count1_cat * 100) if count1_cat > 0 else 0
            }

        # Compare mood distribution
        moods = ['positive', 'neutral', 'negative']
        change['mood_distribution'] = {}

        for mood in moods:
            count1_mood = stats1.get('mood_distribution', {}).get(mood, 0)
            count2_mood = stats2.get('mood_distribution', {}).get(mood, 0)

            change['mood_distribution'][mood] = {
                'period1': count1_mood,
                'period2': count2_mood,
                'absolute': count2_mood - count1_mood,
            }

        # Compare metrics
        metrics1 = stats1.get('metrics_summary', {})
        metrics2 = stats2.get('metrics_summary', {})

        all_metrics = set(
            list(metrics1.keys()) +
            list(metrics2.keys())
        )

        change['metrics'] = {}
        for metric_name in all_metrics:
            m1 = metrics1.get(metric_name, {})
            m2 = metrics2.get(metric_name, {})

            sum1 = m1.get('sum', 0)
            sum2 = m2.get('sum', 0)

            change['metrics'][metric_name] = {
                'period1_sum': sum1,
                'period2_sum': sum2,
                'absolute': sum2 - sum1,
                'percent': ((sum2 - sum1) / sum1 * 100) if sum1 > 0 else 0
            }

        # Determine overall improvement
        improvement['total_entries'] = change['total_entries'] >= 0
        improvement['positive_mood'] = (
            change['mood_distribution'].get('positive', {}).get('absolute', 0) >= 0
        )

        return {
            "period1": period1,
            "period2": period2,
            "period1_stats": stats1,
            "period2_stats": stats2,
            "change": change,
            "improvement": improvement
        }

    def get_daily_summary(
        self,
        days: int = 30,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get daily summary of entries for the last N days.

        Args:
            days: Number of days to include
            category: Optional category filter

        Returns:
            List of daily summaries, each containing:
                - date: Date string
                - count: Number of entries
                - categories: Breakdown by category
                - moods: Mood distribution
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days-1)  # -1 to include end_date

        entries = self.repository.get_entries_by_date_range(
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            category=category
        )

        if not entries:
            return []

        df = self._entries_to_dataframe(entries)

        daily_summaries = []

        for day in pd.date_range(start=start_date, end=end_date, freq='D'):
            day_df = df[df['date'] == day]

            if len(day_df) > 0:
                summary = {
                    "date": day.strftime('%Y-%m-%d'),
                    "count": len(day_df),
                    "categories": day_df['category'].value_counts().to_dict(),
                    "moods": day_df['mood'].value_counts().to_dict(),
                }
            else:
                summary = {
                    "date": day.strftime('%Y-%m-%d'),
                    "count": 0,
                    "categories": {},
                    "moods": {},
                }

            daily_summaries.append(summary)

        return daily_summaries


if __name__ == "__main__":
    # Test the analyzer
    print("Time Series Analyzer Test")
    print("=" * 50)

    analyzer = TimeSeriesAnalyzer()

    # Test weekly statistics
    print("\n1. Weekly Statistics Test:")
    stats = analyzer.weekly_statistics()
    print(f"   Total entries: {stats['total_entries']}")
    print(f"   By category: {stats['by_category']}")

    # Test trend analysis
    print("\n2. Trend Analysis Test:")
    trend = analyzer.trend_analysis(window=7, weeks=4)
    print(f"   Trend direction: {trend['trend_direction']}")
    print(f"   Trend strength (R²): {trend['trend_strength']:.3f}")

    # Test period comparison
    print("\n3. Period Comparison Test:")
    # Get current and last week
    current_week = datetime.now().strftime('%Y-W%W')
    last_week_num = datetime.now().isocalendar()[1] - 1
    last_week = f"{datetime.now().year}-W{last_week_num:02d}"

    comparison = analyzer.compare_periods(last_week, current_week)
    print(f"   Change in entries: {comparison['change']['total_entries']}")
    print(f"   Change percent: {comparison['change']['total_entries_percent']:.1f}%")

    print("\n✓ All tests completed!")
