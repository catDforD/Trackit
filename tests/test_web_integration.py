"""
Web interface integration tests for Trackit.

This module tests the Gradio web interface components:
- TrackitApp initialization
- Chat functionality
- Dashboard data loading
- Report generation
- Data export
- Quick actions

Author: Trackit Development
"""

import pytest
import tempfile
import os
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from src.app import TrackitApp
from src.database.repository import HabitRepository


class TestTrackitApp:
    """Test cases for TrackitApp web interface."""

    @pytest.fixture
    def app(self):
        """Create a TrackitApp instance for testing."""
        return TrackitApp()

    @pytest.fixture
    def test_db(self):
        """Create a test database with sample data."""
        db = HabitRepository()
        today = datetime.now().strftime('%Y-%m-%d')
        # Add test data
        db.add_entry(
            raw_input="跑步30分钟",
            category="运动",
            mood="positive",
            metrics={"distance_km": 3.0, "duration_min": 30},
            note="跑步30分钟",
            entry_date=today
        )
        db.add_entry(
            raw_input="阅读1小时",
            category="阅读",
            mood="neutral",
            metrics={"duration_min": 60},
            note="阅读1小时",
            entry_date=today
        )
        return db

    def test_app_initialization(self, app):
        """Test that TrackitApp initializes correctly."""
        assert app.recording_agent is not None
        assert app.query_agent is not None
        assert app.analysis_agent is not None
        assert app.report_generator is not None
        assert app.repository is not None
        assert app.visualizer is not None
        assert app.chat_history == []

    def test_chat_with_recording_message(self, app):
        """Test chat with a recording message."""
        message = "今天跑步30分钟"
        history = []

        result_msg, result_history, status = app.chat(message, history)

        assert result_msg == ""
        assert len(result_history) == 2
        assert result_history[0]["role"] == "user"
        assert result_history[0]["content"] == message
        assert result_history[1]["role"] == "assistant"
        assert status in ["✅ 操作成功", "⚠️ 未完全理解"]

    def test_chat_with_query_message(self, app, test_db):
        """Test chat with a query message."""
        app.repository = test_db
        message = "我这周运动了几次？"
        history = []

        result_msg, result_history, status = app.chat(message, history)

        assert result_msg == ""
        assert len(result_history) == 2
        assert result_history[0]["content"] == message
        assert status in ["✅ 操作成功", "⚠️ 未完全理解"]

    def test_chat_with_empty_message(self, app):
        """Test chat with an empty message."""
        message = ""
        history = []

        result_msg, result_history, status = app.chat(message, history)

        assert result_msg == ""
        assert result_history == history
        assert status == "请输入消息"

    def test_chat_with_whitespace_message(self, app):
        """Test chat with a whitespace-only message."""
        message = "   "
        history = []

        result_msg, result_history, status = app.chat(message, history)

        assert result_msg == ""
        assert result_history == history
        assert status == "请输入消息"

    def test_quick_action_record_exercise(self, app):
        """Test quick action for recording exercise."""
        history = []

        result_msg, result_history, status = app.quick_action("record_exercise", history)

        assert result_msg == ""
        assert len(result_history) == 2
        assert "运动" in result_history[0]["content"] or "30分钟" in result_history[0]["content"]
        assert status in ["✅ 操作成功", "⚠️ 未完全理解", "⏳ 处理中..."]

    def test_quick_action_record_reading(self, app):
        """Test quick action for recording reading."""
        history = []

        result_msg, result_history, status = app.quick_action("record_reading", history)

        assert result_msg == ""
        assert len(result_history) == 2
        assert "阅读" in result_history[0]["content"] or "1小时" in result_history[0]["content"]

    def test_quick_action_query_today(self, app):
        """Test quick action for querying today."""
        history = []

        result_msg, result_history, status = app.quick_action("query_today", history)

        assert result_msg == ""
        assert len(result_history) == 2
        assert "今天" in result_history[0]["content"]

    def test_quick_action_query_week(self, app):
        """Test quick action for querying weekly stats."""
        history = []

        result_msg, result_history, status = app.quick_action("query_week", history)

        assert result_msg == ""
        assert len(result_history) == 2
        assert "周" in result_history[0]["content"]

    def test_quick_action_invalid(self, app):
        """Test quick action with invalid action type."""
        history = []

        result_msg, result_history, status = app.quick_action("invalid_action", history)

        assert result_msg == ""
        assert result_history == history
        assert status == "❓ 未知操作"

    def test_get_dashboard_data(self, app, test_db):
        """Test dashboard data retrieval."""
        app.repository = test_db

        summary, stats_text, chart_path = app.get_dashboard_data()

        assert isinstance(summary, dict)
        assert "总记录数" in summary
        assert "最近7天" in summary
        assert "类别数" in summary
        assert "连续记录" in summary
        assert isinstance(stats_text, str)
        assert "数据统计" in stats_text

    def test_get_dashboard_data_empty(self, app):
        """Test dashboard data with empty database."""
        # Create empty repository with temporary database
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_db_path = f.name

        try:
            from src.database.schema import init_database
            from src.database.repository import HabitRepository

            # Initialize temp database
            init_database(temp_db_path)
            empty_repo = HabitRepository(db_path=temp_db_path)

            original_repo = app.repository
            app.repository = empty_repo
            app.visualizer.repository = empty_repo

            summary, stats_text, chart_path = app.get_dashboard_data()

            assert summary["总记录数"] == 0
            assert "还没有记录" in stats_text

            # Restore original
            app.repository = original_repo
            app.visualizer.repository = original_repo
        finally:
            if os.path.exists(temp_db_path):
                os.remove(temp_db_path)

    def test_generate_report(self, app, test_db):
        """Test report generation."""
        app.repository = test_db

        report_text, chart_path = app.generate_report(weeks=2)

        assert isinstance(report_text, str)
        assert len(report_text) > 0
        assert "习惯追踪周报" in report_text or "周报" in report_text

    def test_generate_report_with_error(self, app):
        """Test report generation with error handling."""
        # Mock to raise an error
        with patch.object(app.report_generator, 'generate_weekly_report',
                         side_effect=Exception("Test error")):
            report_text, chart_path = app.generate_report(weeks=2)

            assert "生成报告失败" in report_text or "error" in report_text.lower()

    def test_export_data_csv(self, app, test_db):
        """Test CSV data export."""
        app.repository = test_db

        result = app.export_data("csv")

        assert isinstance(result, str)
        assert "✅" in result or "成功" in result or "导出" in result
        assert ".csv" in result

    def test_export_data_json(self, app, test_db):
        """Test JSON data export."""
        app.repository = test_db

        result = app.export_data("json")

        assert isinstance(result, str)
        assert "✅" in result or "成功" in result or "导出" in result
        assert ".json" in result

    def test_export_data_with_error(self, app):
        """Test data export with error handling."""
        # Mock to raise an error - use correct path
        with patch('src.analysis.exporter.DataExporter.__init__', side_effect=Exception("Export error")):
            result = app.export_data("csv")

            assert "❌" in result or "失败" in result

    def test_create_interface(self, app):
        """Test Gradio interface creation."""
        interface = app.create_interface()

        assert interface is not None
        # Check that it's a Gradio Blocks object
        assert hasattr(interface, 'blocks')

    def test_create_app_function(self):
        """Test the create_app helper function."""
        from src.app import create_app

        app = create_app()
        assert app is not None
        assert hasattr(app, 'blocks')


class TestInterfaceComponents:
    """Test individual interface components."""

    @pytest.fixture
    def app(self):
        """Create app for component testing."""
        return TrackitApp()

    def test_chatbot_component(self, app):
        """Test chatbot component in interface."""
        interface = app.create_interface()
        # Interface should contain chatbot
        assert interface is not None

    def test_dashboard_components(self, app):
        """Test dashboard components are accessible."""
        summary, stats, chart = app.get_dashboard_data()

        assert summary is not None
        assert stats is not None
        # Chart may be None if no data, that's okay

    def test_report_components(self, app):
        """Test report generation components."""
        text, chart = app.generate_report(weeks=1)

        assert text is not None
        assert isinstance(text, str)

    def test_export_components(self, app):
        """Test export functionality components."""
        csv_result = app.export_data("csv")
        json_result = app.export_data("json")

        assert csv_result is not None
        assert json_result is not None


class TestUserWorkflows:
    """Test complete user workflows."""

    @pytest.fixture
    def app(self):
        """Create app for workflow testing."""
        return TrackitApp()

    def test_record_and_query_workflow(self, app):
        """Test workflow: record a habit and then query it."""
        history = []

        # Step 1: Record a habit
        msg, history, status = app.chat("今天跑步30分钟", history)
        assert len(history) == 2

        # Step 2: Query the habit
        msg, history, status = app.chat("我今天运动了吗？", history)
        assert len(history) == 4

    def test_quick_actions_workflow(self, app):
        """Test workflow using quick actions."""
        history = []

        # Use multiple quick actions
        for action in ["record_exercise", "record_reading", "query_today"]:
            msg, history, status = app.quick_action(action, history)

        assert len(history) >= 6  # 3 actions * 2 messages each

    def test_dashboard_refresh_workflow(self, app):
        """Test dashboard refresh workflow."""
        # Get initial data
        summary1, stats1, chart1 = app.get_dashboard_data()

        # Get data again (simulating refresh)
        summary2, stats2, chart2 = app.get_dashboard_data()

        # Both should be valid
        assert summary1 is not None
        assert summary2 is not None

    def test_export_and_report_workflow(self, app):
        """Test workflow: generate report and export data."""
        # Generate report
        report_text, chart = app.generate_report(weeks=1)
        assert report_text is not None

        # Export data
        csv_result = app.export_data("csv")
        json_result = app.export_data("json")

        assert csv_result is not None
        assert json_result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
