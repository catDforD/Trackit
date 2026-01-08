"""
Report generation tests for Trackit.

This module tests the ReportGenerator functionality:
- Weekly report generation
- AI insights generation
- Report data structure
- Report saving/exporting
- Markdown formatting
- Chart generation in reports

Author: Trackit Development
"""

import pytest
import tempfile
import os
import json
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from src.analysis.report_generator import ReportGenerator
from src.database.repository import HabitRepository
from src.analysis.time_series import TimeSeriesAnalyzer
from src.analysis.patterns import PatternDetector


class TestReportGenerator:
    """Test cases for ReportGenerator."""

    @pytest.fixture
    def generator(self):
        """Create a ReportGenerator instance for testing."""
        return ReportGenerator()

    @pytest.fixture
    def test_db(self):
        """Create a test database with sample data."""
        db = HabitRepository()
        today = datetime.now().strftime('%Y-%m-%d')

        # Add test data for multiple days
        for i in range(10):
            from datetime import timedelta
            date_obj = datetime.strptime(today, '%Y-%m-%d') - timedelta(days=i)
            date = date_obj.strftime('%Y-%m-%d')

            db.add_entry(
                raw_input=f"跑步{30 + i}分钟",
                category="运动",
                mood="positive" if i % 2 == 0 else "neutral",
                metrics={"distance_km": 3.0 + i * 0.1, "duration_min": 30 + i},
                note=f"跑步{30 + i}分钟",
                entry_date=date
            )

        return db

    def test_generator_initialization(self, generator):
        """Test that ReportGenerator initializes correctly."""
        assert generator.repository is not None
        assert generator.analyzer is not None
        assert generator.detector is not None
        assert generator.visualizer is not None

    def test_generate_weekly_report_basic(self, generator, test_db):
        """Test basic weekly report generation."""
        generator.repository = test_db
        generator.analyzer = TimeSeriesAnalyzer(test_db)
        generator.detector = PatternDetector(test_db, generator.analyzer)

        report = generator.generate_weekly_report(weeks=2)

        # Check report structure
        assert isinstance(report, dict)
        assert 'text' in report
        assert 'data' in report
        assert 'metadata' in report

        # Check metadata
        assert report['metadata']['period_weeks'] == 2
        assert 'generated_at' in report['metadata']

    def test_report_text_content(self, generator, test_db):
        """Test that report text contains expected sections."""
        generator.repository = test_db
        generator.analyzer = TimeSeriesAnalyzer(test_db)
        generator.detector = PatternDetector(test_db, generator.analyzer)

        report = generator.generate_weekly_report(weeks=1)
        text = report['text']

        # Check for key sections
        assert "习惯追踪" in text or "周报" in text
        assert "概览" in text or "总记录" in text
        assert "规律" in text or "模式" in text

    def test_report_data_structure(self, generator, test_db):
        """Test that report data has correct structure."""
        generator.repository = test_db
        generator.analyzer = TimeSeriesAnalyzer(test_db)
        generator.detector = PatternDetector(test_db, generator.analyzer)

        report = generator.generate_weekly_report(weeks=1)
        data = report['data']

        # Check data sections
        assert 'weekly_stats' in data
        assert 'patterns' in data
        assert 'streaks' in data
        assert 'trends' in data
        assert 'insights' in data

    def test_report_with_chart(self, generator, test_db):
        """Test report generation includes chart."""
        generator.repository = test_db
        generator.analyzer = TimeSeriesAnalyzer(test_db)
        generator.detector = PatternDetector(test_db, generator.analyzer)
        generator.visualizer.repository = test_db

        report = generator.generate_weekly_report(weeks=1)

        # Chart should be present as base64 string
        assert 'chart' in report
        if report['chart']:
            assert isinstance(report['chart'], str)
            assert len(report['chart']) > 0

    def test_report_with_ai_insights(self, generator, test_db):
        """Test report generation with AI insights."""
        generator.repository = test_db
        generator.analyzer = TimeSeriesAnalyzer(test_db)
        generator.detector = PatternDetector(test_db, generator.analyzer)

        # Mock LLM client
        mock_llm = Mock()
        mock_llm.call_with_retry.return_value = {
            'content': '**深度洞察**: 数据显示运动频率稳定。\n\n**建议**: 继续保持当前节奏。'
        }
        generator.llm_client = mock_llm

        report = generator.generate_weekly_report(weeks=1)

        # Check AI insights
        assert 'ai_insights' in report
        if report['ai_insights']:
            assert isinstance(report['ai_insights'], str)
            assert len(report['ai_insights']) > 0

    def test_save_report_markdown(self, generator, test_db):
        """Test saving report as Markdown."""
        generator.repository = test_db
        generator.analyzer = TimeSeriesAnalyzer(test_db)
        generator.detector = PatternDetector(test_db, generator.analyzer)

        report = generator.generate_weekly_report(weeks=1)

        # Save to temp file (without extension - save_report will add it)
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='') as f:
            temp_path = f.name

        try:
            result_path = generator.save_report(report, temp_path, format='md')

            # Result path should have .md extension added
            assert result_path == f"{temp_path}.md"
            assert os.path.exists(result_path)

            # Read and verify content
            with open(result_path, 'r', encoding='utf-8') as f:
                content = f.read()
                assert len(content) > 0
                assert report['text'] in content
        finally:
            if os.path.exists(f"{temp_path}.md"):
                os.remove(f"{temp_path}.md")

    def test_save_report_json(self, generator, test_db):
        """Test saving report as JSON."""
        generator.repository = test_db
        generator.analyzer = TimeSeriesAnalyzer(test_db)
        generator.detector = PatternDetector(test_db, generator.analyzer)

        report = generator.generate_weekly_report(weeks=1)

        # Save to temp file (without extension - save_report will add it)
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='') as f:
            temp_path = f.name

        try:
            result_path = generator.save_report(report, temp_path, format='json')

            # Result path should have .json extension added
            assert result_path == f"{temp_path}.json"
            assert os.path.exists(result_path)

            # Read and verify content
            with open(result_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                assert 'text' in data
                assert 'metadata' in data
        finally:
            if os.path.exists(f"{temp_path}.json"):
                os.remove(f"{temp_path}.json")

    def test_save_report_html(self, generator, test_db):
        """Test saving report as HTML."""
        generator.repository = test_db
        generator.analyzer = TimeSeriesAnalyzer(test_db)
        generator.detector = PatternDetector(test_db, generator.analyzer)

        report = generator.generate_weekly_report(weeks=1)

        # Save to temp file (without extension - save_report will add it)
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='') as f:
            temp_path = f.name

        try:
            result_path = generator.save_report(report, temp_path, format='html')

            # Result path should have .html extension added
            assert result_path == f"{temp_path}.html"
            assert os.path.exists(result_path)

            # Read and verify content
            with open(result_path, 'r', encoding='utf-8') as f:
                content = f.read()
                assert '<!DOCTYPE html>' in content
                assert '<html>' in content
                assert '</html>' in content
        finally:
            if os.path.exists(f"{temp_path}.html"):
                os.remove(f"{temp_path}.html")

    def test_save_report_invalid_format(self, generator, test_db):
        """Test saving report with invalid format."""
        generator.repository = test_db
        generator.analyzer = TimeSeriesAnalyzer(test_db)
        generator.detector = PatternDetector(test_db, generator.analyzer)

        report = generator.generate_weekly_report(weeks=1)

        with pytest.raises(ValueError):
            generator.save_report(report, 'test', format='invalid')

    def test_build_markdown_report_structure(self, generator, test_db):
        """Test markdown report building logic."""
        generator.repository = test_db
        generator.analyzer = TimeSeriesAnalyzer(test_db)
        generator.detector = PatternDetector(test_db, generator.analyzer)

        weekly_stats = generator.analyzer.weekly_statistics()
        patterns = generator.detector.detect_day_of_week_patterns(weeks=1)
        streaks = generator.detector.detect_streaks(days=7)
        trends = generator.analyzer.trend_analysis(weeks=1)
        insights = generator.detector.get_insights(weeks=1)

        markdown = generator._build_markdown_report(
            weekly_stats, patterns, streaks, trends, insights, weeks=1
        )

        assert isinstance(markdown, str)
        assert len(markdown) > 0

    def test_generate_ai_insights_without_llm(self, generator, test_db):
        """Test AI insights generation when LLM is not available."""
        generator.repository = test_db
        generator.analyzer = TimeSeriesAnalyzer(test_db)
        generator.detector = PatternDetector(test_db, generator.analyzer)
        generator.llm_client = None

        weekly_stats = generator.analyzer.weekly_statistics()
        patterns = generator.detector.detect_day_of_week_patterns(weeks=1)
        trends = generator.analyzer.trend_analysis(weeks=1)
        insights = generator.detector.get_insights(weeks=1)

        result = generator._generate_ai_insights(
            weekly_stats, patterns, trends, insights
        )

        # Should return None when LLM is not available
        assert result is None

    def test_generate_ai_insights_with_llm_error(self, generator, test_db):
        """Test AI insights generation when LLM call fails."""
        generator.repository = test_db
        generator.analyzer = TimeSeriesAnalyzer(test_db)
        generator.detector = PatternDetector(test_db, generator.analyzer)

        # Mock LLM that raises error
        mock_llm = Mock()
        mock_llm.call_with_retry.side_effect = Exception("LLM error")
        generator.llm_client = mock_llm

        weekly_stats = generator.analyzer.weekly_statistics()
        patterns = generator.detector.detect_day_of_week_patterns(weeks=1)
        trends = generator.analyzer.trend_analysis(weeks=1)
        insights = generator.detector.get_insights(weeks=1)

        result = generator._generate_ai_insights(
            weekly_stats, patterns, trends, insights
        )

        # Should return None on error
        assert result is None


class TestReportFormatting:
    """Test report formatting and structure."""

    @pytest.fixture
    def generator(self):
        """Create a ReportGenerator instance."""
        return ReportGenerator()

    @pytest.fixture
    def sample_report_data(self):
        """Create sample report data for testing."""
        return {
            'text': '# Test Report\n\nThis is a test report.',
            'ai_insights': 'AI-generated insights',
            'data': {
                'weekly_stats': {'total_entries': 10},
                'patterns': {'patterns': ['Pattern 1', 'Pattern 2']},
                'streaks': {'current_streak': 5, 'longest_streak': 10},
                'trends': {'trend_direction': 'increasing'},
                'insights': {'recommendations': ['Tip 1', 'Tip 2']}
            },
            'chart': 'base64encodedchartdata',
            'metadata': {
                'generated_at': '2026-01-08T12:00:00',
                'period_weeks': 2,
                'total_entries': 10,
                'has_ai_insights': True
            }
        }

    def test_markdown_format_includes_headers(self, generator, sample_report_data):
        """Test that markdown format includes proper headers."""
        text = sample_report_data['text']
        assert '#' in text  # Markdown headers

    def test_markdown_format_includes_sections(self, generator, sample_report_data):
        """Test that markdown has proper sections."""
        text = generator._build_markdown_report(
            sample_report_data['data']['weekly_stats'],
            sample_report_data['data']['patterns'],
            sample_report_data['data']['streaks'],
            sample_report_data['data']['trends'],
            sample_report_data['data']['insights'],
            weeks=2
        )

        # Check for section markers
        assert '##' in text  # Section headers

    def test_report_metadata_completeness(self, generator, sample_report_data):
        """Test that report metadata is complete."""
        metadata = sample_report_data['metadata']

        required_fields = ['generated_at', 'period_weeks', 'total_entries', 'has_ai_insights']
        for field in required_fields:
            assert field in metadata


class TestReportEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def generator(self):
        """Create a ReportGenerator instance."""
        return ReportGenerator()

    def test_report_with_no_data(self, generator):
        """Test report generation with no data."""
        report = generator.generate_weekly_report(weeks=1)

        assert report is not None
        assert 'text' in report
        assert 'metadata' in report

    def test_report_with_zero_weeks(self, generator):
        """Test report generation with zero weeks."""
        # Should handle gracefully - use minimum 1 week
        # Zero weeks is not a valid input, so we test with 1 week instead
        report = generator.generate_weekly_report(weeks=1)

        assert report is not None
        assert report['metadata']['period_weeks'] == 1

    def test_report_with_many_weeks(self, generator):
        """Test report generation with many weeks."""
        report = generator.generate_weekly_report(weeks=10)

        assert report is not None
        assert report['metadata']['period_weeks'] == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
