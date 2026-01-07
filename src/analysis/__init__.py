"""
Analysis module for Trackit.

This module provides time series analysis, pattern detection,
visualization, and data export for habit tracking data.

Components:
- TimeSeriesAnalyzer: Time-based statistics and trend analysis
- PatternDetector: Pattern recognition in habit data
- HabitVisualizer: Data visualization (Matplotlib & Plotly)
- DataExporter: Export to CSV/JSON formats
- ReportGenerator: AI-powered report generation
"""

from .time_series import TimeSeriesAnalyzer
from .patterns import PatternDetector
from .visualizer import HabitVisualizer
from .exporter import DataExporter
from .report_generator import ReportGenerator

__all__ = [
    "TimeSeriesAnalyzer",
    "PatternDetector",
    "HabitVisualizer",
    "DataExporter",
    "ReportGenerator",
]
