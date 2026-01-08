"""
End-to-end user flow tests for Trackit.

This module tests complete user workflows from start to finish:
- First-time user onboarding
- Daily habit recording
- Weekly review and analysis
- Data export and backup
- Pattern discovery workflow
- Long-term trend analysis

Author: Trackit Development
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.app import TrackitApp
from src.database.repository import HabitRepository
from src.agents.recording_agent import RecordingAgent
from src.agents.query_agent import QueryAgent
from src.agents.analysis_agent import AnalysisAgent
from src.analysis.report_generator import ReportGenerator


class TestFirstTimeUserFlow:
    """Test first-time user onboarding and initial usage."""

    @pytest.fixture
    def fresh_app(self):
        """Create a fresh app instance with empty database."""
        # Use a temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_db = f.name

        try:
            app = TrackitApp()
            yield app
        finally:
            if os.path.exists(temp_db):
                os.remove(temp_db)

    def test_new_user_sees_empty_state(self, fresh_app):
        """Test that new users see appropriate empty state."""
        # Create temporary database for this test
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_db_path = f.name

        try:
            from src.database.schema import init_database
            from src.database.repository import HabitRepository

            # Create fresh database
            init_database(temp_db_path)
            empty_repo = HabitRepository(db_path=temp_db_path)

            # Update app to use empty repository
            original_repo = fresh_app.repository
            fresh_app.repository = empty_repo
            fresh_app.visualizer.repository = empty_repo

            summary, stats_text, chart_path = fresh_app.get_dashboard_data()

            assert summary["总记录数"] == 0
            assert "还没有记录" in stats_text

            # Restore original
            fresh_app.repository = original_repo
            fresh_app.visualizer.repository = original_repo
        finally:
            if os.path.exists(temp_db_path):
                os.remove(temp_db_path)

    def test_new_user_can_record_first_habit(self, fresh_app):
        """Test that new user can successfully record first habit."""
        history = []

        # Record first habit
        msg, history, status = fresh_app.chat("今天跑步30分钟", history)

        assert len(history) == 2
        assert history[0]["content"] == "今天跑步30分钟"
        assert status in ["✅ 操作成功", "⚠️ 未完全理解"]

    def test_new_user_quick_start_flow(self, fresh_app):
        """Test complete quick start flow for new user."""
        history = []

        # Step 1: Record first habit using quick action
        msg, history, status = fresh_app.quick_action("record_exercise", history)
        assert len(history) == 2

        # Step 2: Record another habit
        msg, history, status = fresh_app.quick_action("record_reading", history)
        assert len(history) == 4

        # Step 3: Check today's records
        msg, history, status = fresh_app.quick_action("query_today", history)
        assert len(history) == 6

        # Step 4: View dashboard
        summary, stats_text, chart_path = fresh_app.get_dashboard_data()
        assert summary["总记录数"] >= 2


class TestDailyUsageFlow:
    """Test daily usage patterns."""

    @pytest.fixture
    def app_with_data(self):
        """Create app with sample data."""
        app = TrackitApp()
        today = datetime.now().strftime('%Y-%m-%d')

        # Add habits for today
        app.recording_agent.execute(f"今天跑步30分钟")
        app.recording_agent.execute(f"今天阅读1小时")

        return app

    def test_morning_recording_flow(self, app_with_data):
        """Test morning habit recording routine."""
        history = []

        # Morning exercise
        msg, history, status = app_with_data.chat("今天早上跑步30分钟，感觉很棒", history)
        assert len(history) == 2

        # Morning meditation
        msg, history, status = app_with_data.chat("冥想了15分钟", history)
        assert len(history) == 4

        # Check today's progress
        msg, history, status = app_with_data.chat("我今天记录了什么？", history)
        assert len(history) == 6

    def test_evening_review_flow(self, app_with_data):
        """Test evening review routine."""
        history = []

        # Record evening activities
        msg, history, status = app_with_data.chat("晚上阅读了1小时", history)
        msg, history, status = app_with_data.chat("喝了8杯水", history)

        # Get daily summary
        msg, history, status = app_with_data.chat("今天我做了什么？", history)

        assert len(history) >= 6

    def test_multiple_queries_in_session(self, app_with_data):
        """Test multiple queries in one session."""
        history = []

        queries = [
            "我今天运动了几次？",
            "我这周阅读了多久？",
            "有什么规律吗？",
            "最近趋势怎么样？"
        ]

        for query in queries:
            msg, history, status = app_with_data.chat(query, history)
            assert len(history) > 0

        # Should have 8 messages (4 user + 4 assistant)
        assert len(history) == 8


class TestWeeklyReviewFlow:
    """Test weekly review and analysis workflow."""

    @pytest.fixture
    def app_with_week_data(self):
        """Create app with a week of data."""
        app = TrackitApp()
        today = datetime.now()

        # Add data for the past week
        for i in range(7):
            date = (today - timedelta(days=i)).strftime('%Y-%m-%d')

            # Vary activities by day
            if i % 2 == 0:
                app.recording_agent.execute(f"{date} 跑步30分钟")
            if i % 3 == 0:
                app.recording_agent.execute(f"{date} 阅读1小时")
            if i == 0:
                app.recording_agent.execute(f"{date} 冥想15分钟")

        return app

    def test_generate_weekly_report(self, app_with_week_data):
        """Test weekly report generation."""
        report_text, chart_path = app_with_week_data.generate_report(weeks=1)

        assert report_text is not None
        assert len(report_text) > 0
        assert "周报" in report_text or "概览" in report_text

    def test_weekly_analysis_workflow(self, app_with_week_data):
        """Test complete weekly analysis workflow."""
        history = []

        # Step 1: Check patterns
        msg, history, status = app_with_week_data.chat("有什么规律吗？", history)

        # Step 2: Check trends
        msg, history, status = app_with_week_data.chat("最近趋势怎么样？", history)

        # Step 3: Get recommendations
        msg, history, status = app_with_week_data.chat("给我一些分析和建议", history)

        # Step 4: Generate report
        report_text, chart_path = app_with_week_data.generate_report(weeks=1)

        assert len(history) >= 6
        assert report_text is not None

    def test_weekly_data_export(self, app_with_week_data):
        """Test weekly data export workflow."""
        # Export to CSV
        csv_result = app_with_week_data.export_data("csv")
        assert "✅" in csv_result or "成功" in csv_result

        # Export to JSON
        json_result = app_with_week_data.export_data("json")
        assert "✅" in json_result or "成功" in json_result


class TestPatternDiscoveryFlow:
    """Test pattern discovery and insights workflow."""

    @pytest.fixture
    def app_with_patterns(self):
        """Create app with data containing patterns."""
        app = TrackitApp()
        today = datetime.now()

        # Create pattern: exercise every other day
        for i in range(14):
            date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
            if i % 2 == 0:
                app.recording_agent.execute(f"{date} 跑步30分钟，心情很好")

        # Create pattern: read every weekend
        for i in range(4):
            date = (today - timedelta(days=i*7)).strftime('%Y-%m-%d')
            app.recording_agent.execute(f"{date} 阅读了2小时")

        return app

    def test_discover_day_patterns(self, app_with_patterns):
        """Test discovering day-of-week patterns."""
        history = []

        msg, history, status = app_with_patterns.chat(
            "我在星期几最活跃？", history
        )

        assert len(history) == 2

    def test_discover_activity_patterns(self, app_with_patterns):
        """Test discovering activity patterns."""
        history = []

        msg, history, status = app_with_patterns.chat(
            "我通常在哪些日子运动？", history
        )

        assert len(history) == 2

    def test_get_all_insights(self, app_with_patterns):
        """Test getting all insights at once."""
        history = []

        msg, history, status = app_with_patterns.chat(
            "给我一些分析和建议", history
        )

        assert len(history) >= 2


class TestLongTermTrackingFlow:
    """Test long-term habit tracking workflows."""

    @pytest.fixture
    def app_with_month_data(self):
        """Create app with a month of data."""
        app = TrackitApp()
        today = datetime.now()

        # Add daily data for a month
        for i in range(30):
            date = (today - timedelta(days=i)).strftime('%Y-%m-%d')

            # Daily exercise
            app.recording_agent.execute(f"{date} 运动{(30 + i % 30)}分钟")

            # Weekly reading
            if i % 7 == 0:
                app.recording_agent.execute(f"{date} 阅读2小时")

        return app

    def test_long_term_trend_analysis(self, app_with_month_data):
        """Test long-term trend analysis."""
        history = []

        msg, history, status = app_with_month_data.chat(
            "最近30天的趋势怎么样？", history
        )

        assert len(history) >= 2

    def test_streak_detection(self, app_with_month_data):
        """Test streak detection in long-term data."""
        history = []

        msg, history, status = app_with_month_data.chat(
            "我连续记录了多少天？", history
        )

        assert len(history) >= 2

    def test_multi_week_report(self, app_with_month_data):
        """Test generating multi-week report."""
        report_text, chart_path = app_with_month_data.generate_report(weeks=4)

        assert report_text is not None
        assert len(report_text) > 0


class TestErrorRecoveryFlow:
    """Test error recovery and edge cases."""

    @pytest.fixture
    def app(self):
        """Create app instance."""
        return TrackitApp()

    def test_handle_nonsense_input(self, app):
        """Test handling of nonsense input."""
        history = []

        nonsense_inputs = [
            "asdfghjkl",
            "xyz123",
            "!@#$%^&*()",
            "   ",
            "random words with no meaning"
        ]

        for inp in nonsense_inputs:
            msg, history, status = app.chat(inp, history)
            # Should handle gracefully
            assert history is not None

    def test_handle_ambiguous_input(self, app):
        """Test handling of ambiguous input."""
        history = []

        # Ambiguous: could be recording or query
        msg, history, status = app.chat("运动", history)

        assert len(history) >= 2

    def test_session_with_mixed_intents(self, app):
        """Test session with mixed recording and query intents."""
        history = []

        # Mix of recording, querying, and analysis
        messages = [
            "今天跑步30分钟",  # Record
            "我今天运动了吗？",  # Query
            "阅读1小时",  # Record
            "有什么规律吗？",  # Analysis
            "冥想15分钟",  # Record
            "导出数据"  # Export
        ]

        for msg in messages:
            msg, history, status = app.chat(msg, history)

        assert len(history) == len(messages) * 2

    def test_recovery_after_error(self, app):
        """Test recovery after an error."""
        history = []

        # First message might fail
        msg1, history, status1 = app.chat("xyz", history)

        # Second message should work
        msg2, history, status2 = app.chat("今天跑步30分钟", history)

        assert len(history) >= 4


class TestQuickActionsFlow:
    """Test quick action workflows."""

    @pytest.fixture
    def app(self):
        """Create app instance."""
        return TrackitApp()

    def test_batch_recording_with_quick_actions(self, app):
        """Test recording multiple habits with quick actions."""
        history = []

        actions = [
            "record_exercise",
            "record_reading",
            "record_meditation",
            "record_water"
        ]

        for action in actions:
            msg, history, status = app.quick_action(action, history)

        assert len(history) == len(actions) * 2

    def test_batch_querying_with_quick_actions(self, app):
        """Test multiple queries with quick actions."""
        # First add some data
        app.recording_agent.execute("今天跑步30分钟")
        app.recording_agent.execute("今天阅读1小时")

        history = []

        actions = [
            "query_today",
            "query_week",
            "query_patterns",
            "query_trends"
        ]

        for action in actions:
            msg, history, status = app.quick_action(action, history)

        assert len(history) == len(actions) * 2


class TestCompleteUserJourney:
    """Test complete user journey from onboarding to advanced usage."""

    @pytest.fixture
    def fresh_app(self):
        """Create fresh app for complete journey."""
        return TrackitApp()

    def test_first_week_journey(self, fresh_app):
        """Test user journey through first week."""
        history = []

        # Day 1: First records
        msg, history, status = fresh_app.chat("今天跑步30分钟", history)
        msg, history, status = fresh_app.chat("阅读1小时", history)

        # Day 3: Check progress
        msg, history, status = fresh_app.chat("我这几天运动了几次？", history)

        # Day 5: Discover patterns
        msg, history, status = fresh_app.chat("有什么规律吗？", history)

        # Day 7: Generate weekly report
        report_text, chart_path = fresh_app.generate_report(weeks=1)

        # Verify journey progress
        assert len(history) >= 6
        assert report_text is not None

    def test_power_user_workflow(self, fresh_app):
        """Test advanced power user workflow."""
        history = []

        # 1. Quick batch recording
        for action in ["record_exercise", "record_reading", "record_meditation"]:
            msg, history, status = fresh_app.quick_action(action, history)

        # 2. Complex analysis
        msg, history, status = fresh_app.chat("给我一些分析和建议", history)

        # 3. Data export
        csv_result = fresh_app.export_data("csv")

        # 4. Generate report
        report_text, chart_path = fresh_app.generate_report(weeks=1)

        # Verify all operations succeeded
        assert len(history) >= 8
        assert report_text is not None
        assert csv_result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
