"""
Unit tests for data validators.

Tests validation logic without requiring LLM API calls.

Author: Trackit Development
"""

import unittest
from src.utils.validators import (
    validate_extraction,
    validate_classification,
    validate_metrics,
    validate_date,
    validate_time,
    sanitize_note,
    validate_entry_data
)


class TestExtractionValidation(unittest.TestCase):
    """Test extraction data validation."""

    def test_valid_extraction(self):
        """Test validation of valid extraction data."""
        data = {
            "category": "运动",
            "mood": "positive",
            "metrics": {"distance_km": 5.0},
            "note": None
        }
        is_valid, error = validate_extraction(data)
        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_invalid_category(self):
        """Test validation rejects invalid category."""
        data = {
            "category": "invalid",
            "mood": "positive",
            "metrics": {}
        }
        is_valid, error = validate_extraction(data)
        self.assertFalse(is_valid)
        self.assertIn("category", error.lower())

    def test_invalid_mood(self):
        """Test validation rejects invalid mood."""
        data = {
            "category": "运动",
            "mood": "invalid",
            "metrics": {}
        }
        is_valid, error = validate_extraction(data)
        self.assertFalse(is_valid)

    def test_all_valid_categories(self):
        """Test all valid categories are accepted."""
        categories = ["运动", "学习", "睡眠", "情绪", "饮食", "其他"]
        for category in categories:
            data = {
                "category": category,
                "mood": "neutral",
                "metrics": {}
            }
            is_valid, _ = validate_extraction(data)
            self.assertTrue(is_valid, f"Category {category} should be valid")

    def test_all_valid_moods(self):
        """Test all valid moods are accepted."""
        moods = ["positive", "neutral", "negative"]
        for mood in moods:
            data = {
                "category": "运动",
                "mood": mood,
                "metrics": {}
            }
            is_valid, _ = validate_extraction(data)
            self.assertTrue(is_valid, f"Mood {mood} should be valid")


class TestMetricsValidation(unittest.TestCase):
    """Test metrics validation by category."""

    def test_valid_exercise_metrics(self):
        """Test valid exercise metrics."""
        metrics = {"distance_km": 5.0, "duration_min": 30}
        is_valid, _ = validate_metrics(metrics, "运动")
        self.assertTrue(is_valid)

    def test_invalid_exercise_metrics(self):
        """Test invalid metrics for exercise category."""
        metrics = {"invalid_metric": 123}
        is_valid, error = validate_metrics(metrics, "运动")
        self.assertFalse(is_valid)
        self.assertIn("invalid_metric", error)

    def test_valid_sleep_metrics(self):
        """Test valid sleep metrics."""
        metrics = {"sleep_hours": 7.5, "wake_time": "06:30"}
        is_valid, _ = validate_metrics(metrics, "睡眠")
        self.assertTrue(is_valid)

    def test_other_category_accepts_any(self):
        """Test that '其他' category accepts any metrics."""
        metrics = {"random_metric": "value"}
        is_valid, _ = validate_metrics(metrics, "其他")
        self.assertTrue(is_valid)


class TestDateTimeValidation(unittest.TestCase):
    """Test date and time validation."""

    def test_valid_date(self):
        """Test valid date format."""
        is_valid, _ = validate_date("2026-01-10")
        self.assertTrue(is_valid)

    def test_invalid_date_format(self):
        """Test invalid date formats."""
        invalid_dates = ["2026/01/10", "01-10-2026", "2026-01-10-extra"]
        for date_str in invalid_dates:
            is_valid, _ = validate_date(date_str)
            self.assertFalse(is_valid, f"{date_str} should be invalid")

    def test_valid_time(self):
        """Test valid time format."""
        valid_times = ["06:30", "23:59", "00:00"]
        for time_str in valid_times:
            is_valid, _ = validate_time(time_str)
            self.assertTrue(is_valid, f"{time_str} should be valid")

    def test_invalid_time_format(self):
        """Test invalid time formats."""
        invalid_times = ["25:00", "24:00", "06:60", "6:30", "abc"]
        for time_str in invalid_times:
            is_valid, _ = validate_time(time_str)
            self.assertFalse(is_valid, f"{time_str} should be invalid")


class TestNoteSanitization(unittest.TestCase):
    """Test note sanitization."""

    def test_none_note(self):
        """Test None note returns None."""
        result = sanitize_note(None)
        self.assertIsNone(result)

    def test_normal_note(self):
        """Test normal note is unchanged."""
        result = sanitize_note("This is a normal note")
        self.assertEqual(result, "This is a normal note")

    def test_whitespace_removal(self):
        """Test excessive whitespace is removed."""
        result = sanitize_note("This  has    extra   spaces")
        self.assertEqual(result, "This has extra spaces")

    def test_long_note_truncation(self):
        """Test very long notes are truncated."""
        long_note = "a" * 600
        result = sanitize_note(long_note)
        self.assertEqual(len(result), 500)  # Should be truncated to 500
        self.assertTrue(result.endswith("..."))

    def test_empty_note(self):
        """Test empty string note returns None."""
        result = sanitize_note("")
        self.assertIsNone(result)


class TestEntryValidation(unittest.TestCase):
    """Test complete entry validation."""

    def test_valid_entry(self):
        """Test validation of complete valid entry."""
        entry = {
            "raw_input": "今天跑了5公里",
            "category": "运动",
            "mood": "positive",
            "metrics": {"distance_km": 5.0}
        }
        is_valid, _ = validate_entry_data(entry)
        self.assertTrue(is_valid)

    def test_missing_required_field(self):
        """Test validation fails when required field is missing."""
        entry = {
            "raw_input": "今天跑了5公里",
            "category": "运动",
            # Missing "mood"
            "metrics": {}
        }
        is_valid, error = validate_entry_data(entry)
        self.assertFalse(is_valid)
        self.assertIn("mood", error)

    def test_invalid_metrics_for_category(self):
        """Test validation fails with invalid metrics."""
        entry = {
            "raw_input": "今天睡了8小时",
            "category": "睡眠",
            "mood": "positive",
            "metrics": {"invalid_metric": 123}
        }
        is_valid, _ = validate_entry_data(entry)
        self.assertFalse(is_valid)


if __name__ == '__main__':
    unittest.main()
