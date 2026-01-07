"""
Data visualization module for Trackit.

This module provides visualization functions for habit tracking data,
including weekly summaries, comparisons, and trend charts.

Supports both:
- Matplotlib: Static publication-quality figures
- Plotly: Interactive web-based visualizations

Key Features:
- Weekly summary charts (4-subplot overview)
- Period comparison charts
- Long-term trend analysis
- Export to PNG, HTML, and JSON

Author: Trackit Development
"""

import matplotlib.pyplot as plt
import matplotlib
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import io
import base64
import json

from src.database.repository import HabitRepository
from .time_series import TimeSeriesAnalyzer

# Use non-interactive backend for matplotlib
matplotlib.use('Agg')


class HabitVisualizer:
    """
    Visualizer for habit tracking data.

    This class provides methods to create various visualizations
    for habit data, including weekly summaries, comparisons, and trends.

    Attributes:
        repository: HabitRepository instance for data access
        analyzer: TimeSeriesAnalyzer for statistical analysis

    Example:
        >>> visualizer = HabitVisualizer()
        >>> fig = visualizer.plot_weekly_summary("2026-W02")
        >>> fig.savefig('weekly_summary.png')
    """

    def __init__(
        self,
        repository: Optional[HabitRepository] = None,
        analyzer: Optional[TimeSeriesAnalyzer] = None
    ):
        """
        Initialize the visualizer.

        Args:
            repository: HabitRepository instance. If None, creates a new one.
            analyzer: TimeSeriesAnalyzer instance. If None, creates a new one.
        """
        self.repository = repository or HabitRepository()
        self.analyzer = analyzer or TimeSeriesAnalyzer(repository)

        # Set matplotlib style
        plt.style.use('seaborn-v0_8-darkgrid')

    # ==================== Matplotlib Visualizations ====================

    def plot_weekly_summary(
        self,
        week_iso: Optional[str] = None,
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """
        Create a 4-subplot weekly summary chart using Matplotlib.

        Subplots:
        1. Entry frequency by category
        2. Mood distribution (pie chart)
        3. Daily entry count
        4. Metrics summary (if available)

        Args:
            week_iso: ISO week string (e.g., "2026-W02"). If None, uses current week.
            save_path: Optional path to save the figure

        Returns:
            matplotlib Figure object

        Example:
            >>> fig = visualizer.plot_weekly_summary("2026-W02")
            >>> fig.savefig('week_summary.png', dpi=300, bbox_inches='tight')
        """
        # Get weekly statistics
        stats = self.analyzer.weekly_statistics(week_iso=week_iso)

        if stats['total_entries'] == 0:
            # Create empty chart with message
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.text(0.5, 0.5, 'No data for this week',
                   ha='center', va='center', fontsize=16)
            ax.axis('off')
            return fig

        # Create figure with 2x2 subplots
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle(f"Weekly Summary - {stats['week']}", fontsize=16, fontweight='bold')

        # 1. Bar chart: Entries by category
        if stats['by_category']:
            categories = list(stats['by_category'].keys())
            counts = list(stats['by_category'].values())
            colors = plt.cm.Set3(np.linspace(0, 1, len(categories)))

            axes[0, 0].bar(categories, counts, color=colors)
            axes[0, 0].set_title('Entries by Category', fontweight='bold')
            axes[0, 0].set_xlabel('Category')
            axes[0, 0].set_ylabel('Count')
            axes[0, 0].tick_params(axis='x', rotation=45)

            # Add value labels on bars
            for i, v in enumerate(counts):
                axes[0, 0].text(i, v + 0.1, str(v), ha='center', va='bottom')

        # 2. Pie chart: Mood distribution
        if stats['mood_distribution']:
            moods = list(stats['mood_distribution'].keys())
            mood_counts = list(stats['mood_distribution'].values())
            mood_colors = {
                'positive': '#2ecc71',
                'neutral': '#95a5a6',
                'negative': '#e74c3c'
            }
            colors = [mood_colors.get(m, '#3498db') for m in moods]

            axes[0, 1].pie(mood_counts, labels=moods, autopct='%1.1f%%',
                          colors=colors, startangle=90)
            axes[0, 1].set_title('Mood Distribution', fontweight='bold')

        # 3. Line chart: Daily entry count
        if stats['by_day']:
            days = list(stats['by_day'].keys())
            day_counts = list(stats['by_day'].values())

            axes[1, 0].plot(days, day_counts, marker='o', linewidth=2, markersize=8)
            axes[1, 0].set_title('Daily Entry Count', fontweight='bold')
            axes[1, 0].set_xlabel('Day of Week')
            axes[1, 0].set_ylabel('Count')
            axes[1, 0].tick_params(axis='x', rotation=45)
            axes[1, 0].grid(True, alpha=0.3)

        # 4. Metrics summary (bar chart of top metrics)
        if stats['metrics_summary']:
            # Get top 5 metrics by sum
            metrics = stats['metrics_summary']
            metric_names = []
            metric_sums = []

            for name, data in list(metrics.items())[:5]:
                if data.get('sum'):
                    metric_names.append(name.replace('_', ' ').title())
                    metric_sums.append(data['sum'])

            if metric_names:
                y_pos = np.arange(len(metric_names))
                axes[1, 1].barh(y_pos, metric_sums, color=plt.cm.viridis(np.linspace(0, 1, len(metric_names))))
                axes[1, 1].set_yticks(y_pos)
                axes[1, 1].set_yticklabels(metric_names)
                axes[1, 1].set_title('Top Metrics (Sum)', fontweight='bold')
                axes[1, 1].set_xlabel('Total')
                axes[1, 1].invert_yaxis()

        plt.tight_layout()

        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')

        return fig

    def plot_comparison(
        self,
        period1: str,
        period2: str,
        category: Optional[str] = None,
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """
        Create a comparison chart between two periods.

        Args:
            period1: ISO week string for period 1
            period2: ISO week string for period 2
            category: Optional category filter
            save_path: Optional path to save the figure

        Returns:
            matplotlib Figure object

        Example:
            >>> fig = visualizer.plot_comparison("2026-W01", "2026-W02")
            >>> fig.savefig('comparison.png')
        """
        # Get comparison data
        comparison = self.analyzer.compare_periods(period1, period2, category)

        # Create figure
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle(f"Period Comparison: {period1} vs {period2}",
                    fontsize=16, fontweight='bold')

        # 1. Total entries comparison
        total_entries = [
            comparison['period1_stats']['total_entries'],
            comparison['period2_stats']['total_entries']
        ]
        axes[0, 0].bar([period1, period2], total_entries,
                      color=['#3498db', '#2ecc71'])
        axes[0, 0].set_title('Total Entries', fontweight='bold')
        axes[0, 0].set_ylabel('Count')

        # Add percentage change annotation
        pct_change = comparison['change']['total_entries_percent']
        direction = "↑" if pct_change >= 0 else "↓"
        axes[0, 0].text(0.5, 0.95, f"{direction} {abs(pct_change):.1f}%",
                       transform=axes[0, 0].transAxes, ha='center',
                       bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        # 2. Category comparison (grouped bar chart)
        all_categories = set(
            list(comparison['period1_stats'].get('by_category', {}).keys()) +
            list(comparison['period2_stats'].get('by_category', {}).keys())
        )

        if all_categories:
            categories = sorted(list(all_categories))
            p1_counts = [comparison['period1_stats'].get('by_category', {}).get(c, 0)
                         for c in categories]
            p2_counts = [comparison['period2_stats'].get('by_category', {}).get(c, 0)
                         for c in categories]

            x = np.arange(len(categories))
            width = 0.35

            axes[0, 1].bar(x - width/2, p1_counts, width, label=period1, color='#3498db')
            axes[0, 1].bar(x + width/2, p2_counts, width, label=period2, color='#2ecc71')
            axes[0, 1].set_title('Entries by Category', fontweight='bold')
            axes[0, 1].set_ylabel('Count')
            axes[0, 1].set_xticks(x)
            axes[0, 1].set_xticklabels(categories, rotation=45, ha='right')
            axes[0, 1].legend()

        # 3. Mood distribution comparison
        moods = ['positive', 'neutral', 'negative']
        p1_moods = [comparison['period1_stats'].get('mood_distribution', {}).get(m, 0)
                    for m in moods]
        p2_moods = [comparison['period2_stats'].get('mood_distribution', {}).get(m, 0)
                    for m in moods]

        x = np.arange(len(moods))
        width = 0.35

        axes[1, 0].bar(x - width/2, p1_moods, width, label=period1, color='#3498db')
        axes[1, 0].bar(x + width/2, p2_moods, width, label=period2, color='#2ecc71')
        axes[1, 0].set_title('Mood Distribution', fontweight='bold')
        axes[1, 0].set_ylabel('Count')
        axes[1, 0].set_xticks(x)
        axes[1, 0].set_xticklabels([m.title() for m in moods])
        axes[1, 0].legend()

        # 4. Metrics comparison (if available)
        metrics1 = comparison['period1_stats'].get('metrics_summary', {})
        metrics2 = comparison['period2_stats'].get('metrics_summary', {})

        if metrics1 or metrics2:
            all_metrics = set(list(metrics1.keys()) + list(metrics2.keys()))

            if all_metrics:
                metric_names = sorted(list(all_metrics))[:5]  # Top 5
                m1_sums = [metrics1.get(m, {}).get('sum', 0) for m in metric_names]
                m2_sums = [metrics2.get(m, {}).get('sum', 0) for m in metric_names]

                x = np.arange(len(metric_names))
                width = 0.35

                axes[1, 1].bar(x - width/2, m1_sums, width, label=period1, color='#3498db')
                axes[1, 1].bar(x + width/2, m2_sums, width, label=period2, color='#2ecc71')
                axes[1, 1].set_title('Metrics Comparison', fontweight='bold')
                axes[1, 1].set_ylabel('Total')
                axes[1, 1].set_xticks(x)
                axes[1, 1].set_xticklabels([m.replace('_', ' ').title() for m in metric_names],
                                           rotation=45, ha='right')
                axes[1, 1].legend()

        plt.tight_layout()

        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')

        return fig

    def plot_trend(
        self,
        category: Optional[str] = None,
        metric: Optional[str] = None,
        weeks: int = 4,
        window: int = 7,
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """
        Create a trend analysis chart with moving average.

        Args:
            category: Optional category filter
            metric: Specific metric to plot
            weeks: Number of weeks to analyze
            window: Moving average window size
            save_path: Optional path to save the figure

        Returns:
            matplotlib Figure object

        Example:
            >>> fig = visualizer.plot_trend(
            ...     category="运动",
            ...     metric="distance_km",
            ...     weeks=4
            ... )
            >>> fig.savefig('trend.png')
        """
        # Get trend data
        trend = self.analyzer.trend_analysis(
            category=category,
            metric=metric,
            window=window,
            weeks=weeks
        )

        if not trend['daily_data']:
            # Create empty chart
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.text(0.5, 0.5, 'Insufficient data for trend analysis',
                   ha='center', va='center', fontsize=16)
            ax.axis('off')
            return fig

        # Create figure
        fig, ax = plt.subplots(figsize=(14, 7))

        # Extract data
        dates = [d['date'] for d in trend['daily_data']]
        values = [d['value'] if d['value'] is not None else 0 for d in trend['daily_data']]
        moving_avg = [d['moving_avg'] if d['moving_avg'] is not None else 0
                     for d in trend['daily_data']]

        # Plot
        x = np.arange(len(dates))
        ax.plot(x, values, marker='o', linewidth=2, markersize=6,
               label='Daily Value', color='#3498db', alpha=0.7)
        ax.plot(x, moving_avg, linewidth=3, label=f'{window}-Day Moving Avg',
               color='#e74c3c')

        # Fill between
        ax.fill_between(x, values, moving_avg, alpha=0.2, color='#3498db')

        # Styling
        metric_name = trend['summary'].get('metric', 'Count')
        ax.set_title(f'Trend Analysis: {metric_name} (Last {weeks} weeks)',
                    fontsize=14, fontweight='bold')
        ax.set_xlabel('Date')
        ax.set_ylabel(metric_name.replace('_', ' ').title())
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)

        # Set x-axis labels (show every nth label to avoid crowding)
        step = max(1, len(dates) // 10)
        ax.set_xticks(x[::step])
        ax.set_xticklabels([dates[i] for i in range(0, len(dates), step)], rotation=45)

        # Add trend info box
        info_text = f"Trend: {trend['trend_direction'].title()}\n"
        info_text += f"Strength (R²): {trend['trend_strength']:.3f}\n"
        info_text += f"Mean: {trend['summary']['mean_value']:.2f}"

        ax.text(0.02, 0.98, info_text, transform=ax.transAxes,
               verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

        plt.tight_layout()

        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')

        return fig

    # ==================== Plotly Interactive Visualizations ====================

    def plot_weekly_summary_interactive(
        self,
        week_iso: Optional[str] = None
    ) -> go.Figure:
        """
        Create an interactive weekly summary chart using Plotly.

        Args:
            week_iso: ISO week string. If None, uses current week.

        Returns:
            plotly Figure object

        Example:
            >>> fig = visualizer.plot_weekly_summary_interactive("2026-W02")
            >>> fig.write_html('weekly_summary.html')
        """
        stats = self.analyzer.weekly_statistics(week_iso=week_iso)

        if stats['total_entries'] == 0:
            fig = go.Figure()
            fig.add_annotation(text="No data for this week",
                             xref="paper", yref="paper",
                             x=0.5, y=0.5, showarrow=False,
                             font=dict(size=16))
            return fig

        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Entries by Category', 'Mood Distribution',
                           'Daily Entry Count', 'Top Metrics'),
            specs=[[{"type": "bar"}, {"type": "pie"}],
                   [{"type": "scatter"}, {"type": "bar"}]]
        )

        # 1. Bar chart: Entries by category
        if stats['by_category']:
            fig.add_trace(
                go.Bar(x=list(stats['by_category'].keys()),
                      y=list(stats['by_category'].values()),
                      name="Entries"),
                row=1, col=1
            )

        # 2. Pie chart: Mood distribution
        if stats['mood_distribution']:
            fig.add_trace(
                go.Pie(labels=list(stats['mood_distribution'].keys()),
                      values=list(stats['mood_distribution'].values()),
                      name="Mood"),
                row=1, col=2
            )

        # 3. Line chart: Daily entries
        if stats['by_day']:
            fig.add_trace(
                go.Scatter(x=list(stats['by_day'].keys()),
                          y=list(stats['by_day'].values()),
                          mode='lines+markers',
                          name="Daily Count"),
                row=2, col=1
            )

        # 4. Metrics bar chart
        if stats['metrics_summary']:
            metrics = list(stats['metrics_summary'].items())[:5]
            if metrics:
                metric_names = [m[0].replace('_', ' ').title() for m in metrics]
                metric_sums = [m[1].get('sum', 0) for m in metrics if m[1].get('sum')]

                fig.add_trace(
                    go.Bar(x=metric_names, y=metric_sums, name="Metrics"),
                    row=2, col=2
                )

        fig.update_layout(
            title_text=f"Weekly Summary - {stats['week']}",
            showlegend=False,
            height=800
        )

        return fig

    def plot_trend_interactive(
        self,
        category: Optional[str] = None,
        metric: Optional[str] = None,
        weeks: int = 4,
        window: int = 7
    ) -> go.Figure:
        """
        Create an interactive trend chart using Plotly.

        Args:
            category: Optional category filter
            metric: Specific metric to plot
            weeks: Number of weeks to analyze
            window: Moving average window size

        Returns:
            plotly Figure object

        Example:
            >>> fig = visualizer.plot_trend_interactive(category="运动")
            >>> fig.write_html('trend.html')
        """
        trend = self.analyzer.trend_analysis(
            category=category,
            metric=metric,
            window=window,
            weeks=weeks
        )

        if not trend['daily_data']:
            fig = go.Figure()
            fig.add_annotation(text="Insufficient data for trend analysis",
                             xref="paper", yref="paper",
                             x=0.5, y=0.5, showarrow=False,
                             font=dict(size=16))
            return fig

        # Extract data
        dates = [d['date'] for d in trend['daily_data']]
        values = [d['value'] if d['value'] is not None else 0 for d in trend['daily_data']]
        moving_avg = [d['moving_avg'] if d['moving_avg'] is not None else 0
                     for d in trend['daily_data']]

        metric_name = trend['summary'].get('metric', 'Count')

        # Create figure
        fig = go.Figure()

        # Add daily values
        fig.add_trace(go.Scatter(
            x=dates, y=values,
            mode='lines+markers',
            name='Daily Value',
            line=dict(color='#3498db', width=2)
        ))

        # Add moving average
        fig.add_trace(go.Scatter(
            x=dates, y=moving_avg,
            mode='lines',
            name=f'{window}-Day Moving Avg',
            line=dict(color='#e74c3c', width=3)
        ))

        # Update layout
        fig.update_layout(
            title=f'Trend Analysis: {metric_name} (Last {weeks} weeks)<br>' +
                  f'<sub>Trend: {trend["trend_direction"].title()} | ' +
                  f'Strength (R²): {trend["trend_strength"]:.3f}</sub>',
            xaxis_title='Date',
            yaxis_title=metric_name.replace('_', ' ').title(),
            hovermode='x unified',
            height=500
        )

        return fig

    # ==================== Utility Functions ====================

    def fig_to_base64(self, fig: plt.Figure) -> str:
        """
        Convert matplotlib figure to base64 string.

        Args:
            fig: matplotlib Figure object

        Returns:
            Base64-encoded string

        Example:
            >>> fig = visualizer.plot_weekly_summary()
            >>> b64 = visualizer.fig_to_base64(fig)
            >>> html = f'<img src="data:image/png;base64,{b64}">'
        """
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        buf.close()
        return img_base64

    def export_chart_data(
        self,
        week_iso: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Export chart data as JSON for external visualization.

        Args:
            week_iso: ISO week string

        Returns:
            Dictionary with chart data

        Example:
            >>> data = visualizer.export_chart_data("2026-W02")
            >>> with open('chart_data.json', 'w') as f:
            ...     json.dump(data, f)
        """
        stats = self.analyzer.weekly_statistics(week_iso=week_iso)

        return {
            "week": stats['week'],
            "total_entries": stats['total_entries'],
            "by_category": stats['by_category'],
            "mood_distribution": stats['mood_distribution'],
            "by_day": stats['by_day'],
            "metrics_summary": stats['metrics_summary'],
            "export_timestamp": datetime.now().isoformat()
        }


if __name__ == "__main__":
    # Test the visualizer
    print("Habit Visualizer Test")
    print("=" * 50)

    visualizer = HabitVisualizer()

    # Test weekly summary
    print("\n1. Creating weekly summary chart...")
    fig = visualizer.plot_weekly_summary()
    print("   ✓ Chart created successfully")

    # Save test chart
    fig.savefig('test_weekly_summary.png', dpi=150, bbox_inches='tight')
    print("   ✓ Saved to test_weekly_summary.png")

    # Test trend
    print("\n2. Creating trend chart...")
    fig = visualizer.plot_trend(weeks=4)
    print("   ✓ Chart created successfully")

    # Test interactive charts
    print("\n3. Creating interactive charts...")
    fig = visualizer.plot_weekly_summary_interactive()
    print("   ✓ Interactive chart created successfully")

    fig = visualizer.plot_trend_interactive(weeks=4)
    print("   ✓ Interactive trend chart created successfully")

    # Test data export
    print("\n4. Exporting chart data...")
    data = visualizer.export_chart_data()
    print(f"   ✓ Exported {len(data)} fields")

    print("\n✓ All visualization tests completed!")
