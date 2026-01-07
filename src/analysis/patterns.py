"""
Pattern detection module for Trackit.

This module provides pattern recognition algorithms for habit tracking data,
including day-of-week patterns, streaks detection, and correlation analysis.

Key Features:
- Day of week pattern detection (e.g., "Wednesdays are typically low mood")
- Habit streak detection (e.g., "7 days in a row")
- Cross-category correlation analysis (e.g., "exercise leads to better mood")

Author: Trackit Development
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from scipy import stats

from src.database.repository import HabitRepository
from .time_series import TimeSeriesAnalyzer


class PatternDetector:
    """
    Pattern detector for habit tracking data.

    This class identifies recurring patterns in habit data, such as:
    - Day-of-week patterns (certain days have different behavior)
    - Streaks (consecutive days of activity)
    - Correlations between different habits (e.g., exercise → mood)

    Attributes:
        repository: HabitRepository instance for data access
        analyzer: TimeSeriesAnalyzer for statistical analysis

    Example:
        >>> detector = PatternDetector()
        >>> patterns = detector.detect_day_of_week_patterns()
        >>> print(patterns['best_day'])
        'Saturday'
    """

    def __init__(
        self,
        repository: Optional[HabitRepository] = None,
        analyzer: Optional[TimeSeriesAnalyzer] = None
    ):
        """
        Initialize the pattern detector.

        Args:
            repository: HabitRepository instance. If None, creates a new one.
            analyzer: TimeSeriesAnalyzer instance. If None, creates a new one.
        """
        self.repository = repository or HabitRepository()
        self.analyzer = analyzer or TimeSeriesAnalyzer(repository)

    def detect_day_of_week_patterns(
        self,
        weeks: int = 4,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Detect patterns based on day of the week.

        Analyzes data to find patterns like:
        - "Wednesdays typically have lower mood"
        - "Exercise is most common on weekends"
        - "You're most productive on Tuesdays"

        Args:
            weeks: Number of weeks to analyze
            category: Optional category filter

        Returns:
            Dictionary containing:
                - best_day: Day with highest positive metrics
                - worst_day: Day with lowest positive metrics
                - most_active_day: Day with most entries
                - least_active_day: Day with fewest entries
                - day_analysis: Detailed analysis per day
                - patterns: List of discovered patterns in natural language

        Example:
            >>> patterns = detector.detect_day_of_week_patterns(weeks=4)
            >>> for pattern in patterns['patterns']:
            ...     print(pattern)
            You're most active on Saturdays
            Mood tends to be lowest on Wednesdays
        """
        # Get data for the specified period
        end_date = datetime.now()
        start_date = end_date - timedelta(weeks=weeks)

        entries = self.repository.get_entries_by_date_range(
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            category=category
        )

        if not entries:
            return {
                "best_day": None,
                "worst_day": None,
                "most_active_day": None,
                "least_active_day": None,
                "day_analysis": {},
                "patterns": []
            }

        # Convert to DataFrame
        df = self.analyzer._entries_to_dataframe(entries)

        # Analyze by day of week
        day_analysis = {}

        for day_num in range(7):
            day_name = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
                       'Friday', 'Saturday', 'Sunday'][day_num]

            day_df = df[df['day_of_week'] == day_num]

            if len(day_df) > 0:
                # Calculate metrics for this day
                positive_count = len(day_df[day_df['mood'] == 'positive'])
                total_count = len(day_df)
                positive_rate = positive_count / total_count if total_count > 0 else 0

                day_analysis[day_name] = {
                    "count": total_count,
                    "positive_rate": positive_rate,
                    "positive_count": positive_count,
                    "neutral_count": len(day_df[day_df['mood'] == 'neutral']),
                    "negative_count": len(day_df[day_df['mood'] == 'negative']),
                    "avg_entries_per_week": total_count / weeks,
                }
            else:
                day_analysis[day_name] = {
                    "count": 0,
                    "positive_rate": 0,
                    "positive_count": 0,
                    "neutral_count": 0,
                    "negative_count": 0,
                    "avg_entries_per_week": 0,
                }

        # Find best and worst days
        best_day = max(day_analysis.items(),
                      key=lambda x: x[1]['positive_rate'])[0] if day_analysis else None
        worst_day = min(day_analysis.items(),
                       key=lambda x: x[1]['positive_rate'])[0] if day_analysis else None

        # Find most and least active days
        most_active_day = max(day_analysis.items(),
                             key=lambda x: x[1]['count'])[0] if day_analysis else None
        least_active_day = min(day_analysis.items(),
                              key=lambda x: x[1]['count'])[0] if day_analysis else None

        # Generate natural language patterns
        patterns = []

        if most_active_day and day_analysis[most_active_day]['count'] > 0:
            patterns.append(
                f"You're most active on {most_active_day}s "
                f"(avg {day_analysis[most_active_day]['avg_entries_per_week']:.1f} entries/week)"
            )

        if least_active_day and day_analysis[least_active_day]['count'] < \
           day_analysis[most_active_day]['count']:
            patterns.append(
                f"You're least active on {least_active_day}s "
                f"(avg {day_analysis[least_active_day]['avg_entries_per_week']:.1f} entries/week)"
            )

        if best_day and worst_day and best_day != worst_day:
            best_rate = day_analysis[best_day]['positive_rate']
            worst_rate = day_analysis[worst_day]['positive_rate']

            if best_rate > worst_rate + 0.1:  # Significant difference
                patterns.append(
                    f"Mood tends to be best on {best_day}s ({best_rate*100:.0f}% positive)"
                )
                patterns.append(
                    f"Mood tends to be lowest on {worst_day}s ({worst_rate*100:.0f}% positive)"
                )

        return {
            "best_day": best_day,
            "worst_day": worst_day,
            "most_active_day": most_active_day,
            "least_active_day": least_active_day,
            "day_analysis": day_analysis,
            "patterns": patterns
        }

    def detect_streaks(
        self,
        category: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Detect streaks (consecutive days with entries).

        Finds patterns like:
        - "You exercised for 7 days in a row"
        - "Longest streak: 14 days"
        - "Current streak: 3 days"

        Args:
            category: Optional category filter
            days: Number of days to look back

        Returns:
            Dictionary containing:
                - current_streak: Current consecutive days
                - longest_streak: Longest streak in period
                - streak_history: List of all streaks
                - streak_dates: Date ranges for each streak

        Example:
            >>> streaks = detector.detect_streaks(category="运动")
            >>> print(f"Current streak: {streaks['current_streak']} days")
            Current streak: 5 days
        """
        # Get data for the specified period
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        entries = self.repository.get_entries_by_date_range(
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            category=category
        )

        if not entries:
            return {
                "current_streak": 0,
                "longest_streak": 0,
                "streak_history": [],
                "streak_dates": []
            }

        # Convert to DataFrame
        df = self.analyzer._entries_to_dataframe(entries)

        # Get unique dates with entries
        dates_with_entries = sorted(df['date'].unique())

        # Find streaks
        streaks = []
        current_streak_start = dates_with_entries[0]

        for i in range(1, len(dates_with_entries)):
            # Check if this date is consecutive to the previous one
            prev_date = dates_with_entries[i - 1]
            curr_date = dates_with_entries[i]

            if (curr_date - prev_date).days == 1:
                # Still in a streak
                continue
            else:
                # Streak ended
                streak_end = prev_date
                streak_length = (streak_end - current_streak_start).days + 1
                streaks.append({
                    "start": current_streak_start.strftime('%Y-%m-%d'),
                    "end": streak_end.strftime('%Y-%m-%d'),
                    "length": streak_length
                })
                current_streak_start = curr_date

        # Don't forget the last streak
        streak_end = dates_with_entries[-1]
        streak_length = (streak_end - current_streak_start).days + 1
        streaks.append({
            "start": current_streak_start.strftime('%Y-%m-%d'),
            "end": streak_end.strftime('%Y-%m-%d'),
            "length": streak_length
        })

        # Find longest streak
        longest_streak = max([s['length'] for s in streaks]) if streaks else 0

        # Calculate current streak
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        # Check if there's an entry today or yesterday
        current_streak = 0
        if dates_with_entries:
            last_entry_date = dates_with_entries[-1]

            if last_entry_date.date() == today or last_entry_date.date() == yesterday:
                # We're in a streak - count backwards from today
                check_date = today
                while any(d.date() == check_date for d in dates_with_entries):
                    current_streak += 1
                    check_date -= timedelta(days=1)

        return {
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "streak_history": streaks,
            "streak_dates": [
                f"{s['start']} to {s['end']} ({s['length']} days)"
                for s in streaks
            ]
        }

    def detect_correlations(
        self,
        weeks: int = 4
    ) -> Dict[str, Any]:
        """
        Detect correlations between different habits and metrics.

        Finds patterns like:
        - "Exercise correlates with better mood"
        - "You sleep earlier on days you exercise"
        - "Study time correlates with positive mood"

        Args:
            weeks: Number of weeks to analyze

        Returns:
            Dictionary containing:
                - correlations: List of significant correlations
                - mood_after_activity: Mood patterns after specific activities
                - activity_pairs: Pairs of activities that often occur together

        Example:
            >>> correlations = detector.detect_correlations()
            >>> for corr in correlations['correlations']:
            ...     print(corr)
            Exercise correlates with better mood (r=0.65)
        """
        # Get data for the specified period
        end_date = datetime.now()
        start_date = end_date - timedelta(weeks=weeks)

        entries = self.repository.get_entries_by_date_range(
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d')
        )

        if not entries:
            return {
                "correlations": [],
                "mood_after_activity": {},
                "activity_pairs": []
            }

        # Convert to DataFrame
        df = self.analyzer._entries_to_dataframe(entries)

        correlations = []

        # 1. Analyze mood after different activities
        mood_after_activity = {}

        for category in df['category'].unique():
            if pd.isna(category):
                continue

            category_df = df[df['category'] == category]
            total = len(category_df)
            positive = len(category_df[category_df['mood'] == 'positive'])
            positive_rate = positive / total if total > 0 else 0

            mood_after_activity[category] = {
                "total": total,
                "positive": positive,
                "positive_rate": positive_rate
            }

            # Only report significant findings
            if total >= 3 and positive_rate >= 0.7:
                correlations.append(
                    f"{category} correlates with good mood "
                    f"({positive_rate*100:.0f}% positive, {total} occurrences)"
                )

        # 2. Find activity pairs that occur on the same day
        daily_categories = df.groupby('date')['category'].apply(list).reset_index()
        daily_categories['category_set'] = daily_categories['category'].apply(set)

        activity_pairs = []
        pair_counts = defaultdict(int)

        for cat_set in daily_categories['category_set']:
            for cat1 in cat_set:
                for cat2 in cat_set:
                    if cat1 < cat2:  # Avoid duplicates and self-pairs
                        pair_counts[(cat1, cat2)] += 1

        # Filter for significant pairs (occur together at least 3 times)
        for (cat1, cat2), count in pair_counts.items():
            if count >= 3:
                activity_pairs.append({
                    "activities": f"{cat1} + {cat2}",
                    "co_occurrence_count": count
                })

        # Sort by frequency
        activity_pairs.sort(key=lambda x: x['co_occurrence_count'], reverse=True)

        # 3. Generate insights about activity pairs
        for pair in activity_pairs[:5]:  # Top 5 pairs
            activities = pair['activities']
            count = pair['co_occurrence_count']
            correlations.append(
                f"{activities} often occur together ({count} times)"
            )

        return {
            "correlations": correlations,
            "mood_after_activity": mood_after_activity,
            "activity_pairs": activity_pairs
        }

    def get_insights(
        self,
        weeks: int = 2
    ) -> Dict[str, Any]:
        """
        Get a comprehensive insight summary combining all pattern detections.

        This is a convenience method that runs all pattern detection
        algorithms and combines the results into actionable insights.

        Args:
            weeks: Number of weeks to analyze

        Returns:
            Dictionary containing:
                - summary: High-level insights
                - day_patterns: Day-of-week patterns
                - streaks: Streak information
                - correlations: Correlation insights
                - recommendations: Actionable recommendations

        Example:
            >>> insights = detector.get_insights(weeks=2)
            >>> print(insights['summary'])
            You've been maintaining good consistency with a 5-day streak!
        """
        # Run all pattern detections
        day_patterns = self.detect_day_of_week_patterns(weeks=weeks)
        streaks = self.detect_streaks(days=weeks*7)
        correlations = self.detect_correlations(weeks=weeks)

        # Generate summary
        summary_parts = []

        if streaks['current_streak'] >= 3:
            summary_parts.append(
                f"You're on a {streaks['current_streak']}-day streak!"
            )

        if streaks['longest_streak'] >= 7:
            summary_parts.append(
                f"Your longest streak was {streaks['longest_streak']} days"
            )

        if day_patterns['best_day']:
            summary_parts.append(
                f"You tend to be in the best mood on {day_patterns['best_day']}s"
            )

        summary = " | ".join(summary_parts) if summary_parts else "Keep tracking to see patterns!"

        # Generate recommendations
        recommendations = []

        # Streak-based recommendations
        if streaks['current_streak'] == 0:
            recommendations.append("Start small - record just one habit today")
        elif streaks['current_streak'] < streaks['longest_streak']:
            recommendations.append(
                f"You're close to your record! Your longest streak was "
                f"{streaks['longest_streak']} days"
            )

        # Day-of-week based recommendations
        if day_patterns['worst_day']:
            recommendations.append(
                f"Be extra mindful on {day_patterns['worst_day']}s - "
                f"that's typically your lowest mood day"
            )

        # Correlation-based recommendations
        for corr in correlations['correlations'][:3]:
            if 'correlates with good mood' in corr:
                # Extract activity name
                activity = corr.split('correlates')[0].strip()
                recommendations.append(
                    f"Consider doing more {activity} - it seems to boost your mood!"
                )

        return {
            "summary": summary,
            "day_patterns": day_patterns,
            "streaks": streaks,
            "correlations": correlations,
            "recommendations": recommendations
        }


if __name__ == "__main__":
    # Test the pattern detector
    print("Pattern Detector Test")
    print("=" * 50)

    detector = PatternDetector()

    # Test day-of-week patterns
    print("\n1. Day of Week Patterns:")
    patterns = detector.detect_day_of_week_patterns(weeks=4)
    print(f"   Best day: {patterns['best_day']}")
    print(f"   Worst day: {patterns['worst_day']}")
    print(f"   Most active: {patterns['most_active_day']}")
    print("\n   Discovered patterns:")
    for pattern in patterns['patterns']:
        print(f"   - {pattern}")

    # Test streaks
    print("\n2. Streak Detection:")
    streaks = detector.detect_streaks(days=30)
    print(f"   Current streak: {streaks['current_streak']} days")
    print(f"   Longest streak: {streaks['longest_streak']} days")

    # Test correlations
    print("\n3. Correlation Analysis:")
    correlations = detector.detect_correlations(weeks=4)
    print("   Found correlations:")
    for corr in correlations['correlations'][:5]:
        print(f"   - {corr}")

    # Test comprehensive insights
    print("\n4. Comprehensive Insights:")
    insights = detector.get_insights(weeks=2)
    print(f"   Summary: {insights['summary']}")
    print("\n   Recommendations:")
    for rec in insights['recommendations']:
        print(f"   - {rec}")

    print("\n✓ All tests completed!")
