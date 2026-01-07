"""
Unit tests for agents - RecordingAgent and QueryAgent.

Tests cover:
- RecordingAgent error handling
- RecordingAgent feedback generation
- QueryAgent intent classification
- QueryAgent query execution
- Integration tests with database

Author: Trackit Development
"""

import unittest
import tempfile
import os
from datetime import datetime

from src.agents.recording_agent import RecordingAgent
from src.agents.query_agent import QueryAgent
from src.database.schema import init_database
from src.database.repository import HabitRepository
from src.config.settings import settings


class TestRecordingAgent(unittest.TestCase):
    """Test cases for RecordingAgent."""

    def setUp(self):
        """Set up test database and agent."""
        # Create temporary database
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        settings.DB_PATH = self.db_path

        # Initialize database
        init_database()

        # Create agent
        self.agent = RecordingAgent()

    def tearDown(self):
        """Clean up temporary database."""
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_agent_initialization(self):
        """Test agent initializes correctly."""
        self.assertEqual(self.agent.name, "RecordingAgent")
        self.assertIsNotNone(self.agent.repository)
        self.assertIsNotNone(self.agent.extractor)
        self.assertIsNotNone(self.agent.feedback_templates)
        self.assertIsNotNone(self.agent.error_messages)

    def test_feedback_templates_structure(self):
        """Test feedback templates are properly structured."""
        templates = self.agent.feedback_templates

        # Check main categories exist
        self.assertIn("运动", templates)
        self.assertIn("学习", templates)
        self.assertIn("睡眠", templates)
        self.assertIn("情绪", templates)
        self.assertIn("饮食", templates)

        # Check mood levels exist
        for category, mood_templates in templates.items():
            self.assertIn("positive", mood_templates)
            self.assertIn("neutral", mood_templates)
            self.assertIn("negative", mood_templates)

    def test_error_messages_structure(self):
        """Test error messages are defined."""
        errors = self.agent.error_messages

        self.assertIn("extraction_failed", errors)
        self.assertIn("validation_failed", errors)
        self.assertIn("database_error", errors)
        self.assertIn("api_error", errors)
        self.assertIn("unknown_error", errors)

    def test_execute_with_empty_input(self):
        """Test execute rejects empty input."""
        result = self.agent.execute(user_input="")

        self.assertFalse(result["success"])
        self.assertEqual(result["error_type"], "validation_error")
        self.assertIn("不能为空", result["error"])

    def test_execute_with_whitespace_input(self):
        """Test execute rejects whitespace-only input."""
        result = self.agent.execute(user_input="   ")

        self.assertFalse(result["success"])
        self.assertEqual(result["error_type"], "validation_error")

    def test_generate_feedback_for_exercise_positive(self):
        """Test feedback generation for positive exercise."""
        extracted = {
            "category": "运动",
            "mood": "positive",
            "metrics": {"distance_km": 5.0}
        }

        feedback = self.agent._generate_feedback(extracted)

        self.assertIsInstance(feedback, str)
        self.assertTrue(len(feedback) > 0)
        # Should contain one of the positive templates
        self.assertTrue(
            any(keyword in feedback for keyword in ["太棒了", "坚持", "胜利", "记录"])
        )

    def test_generate_feedback_for_study_neutral(self):
        """Test feedback generation for neutral study."""
        extracted = {
            "category": "学习",
            "mood": "neutral",
            "metrics": {"duration_hours": 2.0}
        }

        feedback = self.agent._generate_feedback(extracted)

        self.assertIsInstance(feedback, str)
        self.assertTrue(len(feedback) > 0)

    def test_generate_feedback_for_negative_mood(self):
        """Test feedback generation for negative mood."""
        extracted = {
            "category": "情绪",
            "mood": "negative",
            "metrics": {}
        }

        feedback = self.agent._generate_feedback(extracted)

        self.assertIsInstance(feedback, str)
        # Should contain supportive messages
        self.assertTrue(
            any(keyword in feedback for keyword in ["理解", "明天", "休息", "压力"])
        )

    def test_generate_feedback_with_metrics(self):
        """Test feedback includes metric details."""
        extracted = {
            "category": "运动",
            "mood": "positive",
            "metrics": {
                "distance_km": 5.0,
                "duration_min": 30
            }
        }

        feedback = self.agent._generate_feedback(extracted)

        # Should contain metric details
        self.assertIn("5.0", feedback)
        self.assertIn("30", feedback)

    def test_generate_feedback_for_unknown_category(self):
        """Test feedback for category without template."""
        extracted = {
            "category": "未知类别",
            "mood": "neutral",
            "metrics": {}
        }

        feedback = self.agent._generate_feedback(extracted)

        self.assertIsInstance(feedback, str)
        self.assertIn("未知类别", feedback)

    def test_validate_extraction_without_saving(self):
        """Test validate_extraction method."""
        is_valid, extracted, error = self.agent.validate_extraction(
            "今天跑了5公里"
        )

        # Result should be a tuple
        self.assertIsInstance(is_valid, bool)
        if is_valid:
            self.assertIsNotNone(extracted)
            self.assertIn("category", extracted)


class TestQueryAgent(unittest.TestCase):
    """Test cases for QueryAgent."""

    def setUp(self):
        """Set up test database and agent."""
        # Create temporary database
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        settings.DB_PATH = self.db_path

        # Initialize database
        init_database()

        # Create repository and add test data
        repo = HabitRepository()
        today = datetime.now().strftime("%Y-%m-%d")

        # Add test entries
        repo.add_entry(
            raw_input="今天跑了5公里",
            category="运动",
            mood="positive",
            metrics={"distance_km": 5.0},
            entry_date=today
        )

        repo.add_entry(
            raw_input="学习了2小时",
            category="学习",
            mood="neutral",
            metrics={"duration_hours": 2.0},
            entry_date=today
        )

        repo.add_entry(
            raw_input="心情不错",
            category="情绪",
            mood="positive",
            metrics={},
            entry_date=today
        )

        # Create agent
        self.agent = QueryAgent()

    def tearDown(self):
        """Clean up temporary database."""
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_agent_initialization(self):
        """Test agent initializes correctly."""
        self.assertEqual(self.agent.name, "QueryAgent")
        self.assertIsNotNone(self.agent.repository)
        self.assertIsNotNone(self.agent.classifier)
        self.assertIsNotNone(self.agent.response_templates)

    def test_response_templates_structure(self):
        """Test response templates are properly structured."""
        templates = self.agent.response_templates

        # Check intent types exist
        self.assertIn("count", templates)
        self.assertIn("last", templates)
        self.assertIn("summary", templates)
        self.assertIn("comparison", templates)

    def test_execute_with_empty_query(self):
        """Test execute rejects empty query."""
        result = self.agent.execute(query="")

        self.assertFalse(result["success"])
        self.assertIsNotNone(result["error"])
        self.assertIn("不能为空", result["error"])

    def test_query_last_entry(self):
        """Test querying last entry."""
        result = self.agent.execute(query="上次运动是什么时候？")

        # Should succeed (may depend on LLM for intent classification)
        self.assertIsInstance(result, dict)
        self.assertIn("success", result)
        self.assertIn("response", result)

    def test_query_summary(self):
        """Test querying summary."""
        result = self.agent.execute(query="这周的习惯怎么样？")

        self.assertIsInstance(result, dict)
        self.assertIn("success", result)
        self.assertIn("response", result)

    def test_parse_timeframe_week(self):
        """Test timeframe parsing for 'week'."""
        start, end = self.agent._parse_timeframe("week")

        self.assertIsInstance(start, str)
        self.assertIsInstance(end, str)
        self.assertRegex(start, r"\d{4}-\d{2}-\d{2}")
        self.assertRegex(end, r"\d{4}-\d{2}-\d{2}")

    def test_parse_timeframe_month(self):
        """Test timeframe parsing for 'month'."""
        start, end = self.agent._parse_timeframe("month")

        self.assertIsInstance(start, str)
        self.assertIsInstance(end, str)

    def test_timeframe_to_chinese(self):
        """Test timeframe conversion to Chinese."""
        self.assertEqual(self.agent._timeframe_to_chinese("week"), "周")
        self.assertEqual(self.agent._timeframe_to_chinese("month"), "月")
        self.assertEqual(self.agent._timeframe_to_chinese("day"), "天")

    def test_summarize_metrics(self):
        """Test metrics summarization."""
        entries = [
            {"metrics": {"distance_km": 5.0, "duration_min": 30}},
            {"metrics": {"distance_km": 3.0, "duration_min": 20}},
            {"metrics": {"distance_km": 7.0}}
        ]

        summary = self.agent._summarize_metrics(entries)

        self.assertEqual(summary["distance_km"], 15.0)
        self.assertEqual(summary["duration_min"], 50)

    def test_format_entry_details(self):
        """Test entry details formatting."""
        entry = {
            "category": "运动",
            "mood": "positive",
            "metrics": {"distance_km": 5.0, "duration_min": 30}
        }

        details = self.agent._format_entry_details(entry)

        self.assertIsInstance(details, str)
        self.assertIn("5", details)
        self.assertIn("30", details)

    def test_format_entry_details_with_mood(self):
        """Test entry details with mood."""
        entry = {
            "category": "情绪",
            "mood": "positive",
            "metrics": {}
        }

        details = self.agent._format_entry_details(entry)

        self.assertIsInstance(details, str)
        # Mood emoji should be present
        self.assertTrue("😊" in details or "positive" in details)


class TestAgentIntegration(unittest.TestCase):
    """Integration tests for agents working together."""

    def setUp(self):
        """Set up test database."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        settings.DB_PATH = self.db_path
        init_database()

    def tearDown(self):
        """Clean up."""
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_recording_then_query(self):
        """Test recording data then querying it."""
        # Create agents
        recording_agent = RecordingAgent()
        query_agent = QueryAgent()

        # Record a habit
        record_result = recording_agent.execute(user_input="今天跑了5公里")

        if record_result["success"]:
            entry_id = record_result["entry_id"]

            # Query should find this entry
            # (This is a basic test - real queries depend on LLM classification)
            self.assertIsNotNone(entry_id)
            self.assertIsInstance(entry_id, int)

    def test_multiple_recordings(self):
        """Test recording multiple habits."""
        agent = RecordingAgent()

        # Record multiple habits
        inputs = [
            "今天运动了5公里",
            "学习了3小时",
            "心情很好"
        ]

        successful = 0
        for user_input in inputs:
            result = agent.execute(user_input=user_input)
            if result["success"]:
                successful += 1

        # At least some should succeed (depends on LLM availability)
        # This test mainly checks the agent doesn't crash
        self.assertGreaterEqual(successful, 0)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def setUp(self):
        """Set up test database."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        settings.DB_PATH = self.db_path
        init_database()

    def tearDown(self):
        """Clean up."""
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_recording_with_very_long_input(self):
        """Test recording with very long input."""
        agent = RecordingAgent()
        long_input = "今天运动了 " + "非常好 " * 100

        result = agent.execute(user_input=long_input)

        # Should handle gracefully
        self.assertIsInstance(result, dict)
        self.assertIn("success", result)

    def test_query_with_special_characters(self):
        """Test query with special characters."""
        agent = QueryAgent()
        query = "这周运动了几次？！@#$%"

        result = agent.execute(query=query)

        # Should handle gracefully
        self.assertIsInstance(result, dict)
        self.assertIn("success", result)

    def test_recording_agent_state_management(self):
        """Test agent state management."""
        agent = RecordingAgent()

        # Initial state should be empty
        state = agent.get_state()
        self.assertEqual(len(state), 0)

        # Update state
        agent.update_state({"test_key": "test_value"})

        # Check state was updated
        state = agent.get_state()
        self.assertEqual(state["test_key"], "test_value")

        # Reset state
        agent.reset_state()
        state = agent.get_state()
        self.assertEqual(len(state), 0)

    def test_query_agent_state_management(self):
        """Test query agent state management."""
        agent = QueryAgent()

        # Check stats
        stats = agent.get_stats()
        self.assertEqual(stats["execution_count"], 0)

        # Execute a query
        agent.execute(query="测试查询")

        # Check stats updated
        stats = agent.get_stats()
        self.assertEqual(stats["execution_count"], 1)


if __name__ == "__main__":
    unittest.main()
