"""
Validation utilities for Trackit.

This module provides JSON schema validation and data validation
for habit entries and API responses.

Author: Trackit Development
"""

import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from jsonschema import validate, ValidationError


# JSON Schemas for validation
EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {
            "type": "string",
            "enum": ["运动", "学习", "睡眠", "情绪", "饮食", "其他"]
        },
        "mood": {
            "type": "string",
            "enum": ["positive", "neutral", "negative"]
        },
        "metrics": {
            "type": "object",
            "patternProperties": {
                ".+": ["number", "string"]
            }
        },
        "note": {
            "type": ["string", "null"],
            "maxLength": 500
        }
    },
    "required": ["category", "mood", "metrics"],
    "additionalProperties": False
}

CLASSIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {
            "type": "string",
            "enum": ["RECORD", "COUNT", "LAST", "SUMMARY", "COMPARISON", "REPORT", "GENERAL"]
        },
        "entities": {
            "type": "object",
            "properties": {
                "category": {"type": ["string", "null"]},
                "timeframe": {"type": ["string", "null"]},
                "specific_date": {"type": ["string", "null"]}
            }
        }
    },
    "required": ["intent", "entities"],
    "additionalProperties": False
}


def validate_extraction(data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate extracted habit entry data.

    Args:
        data: Dictionary containing extracted data

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        >>> data = {"category": "运动", "mood": "positive", "metrics": {}}
        >>> is_valid, error = validate_extraction(data)
        >>> print(is_valid)
        True
    """
    try:
        validate(instance=data, schema=EXTRACTION_SCHEMA)
        return True, None
    except ValidationError as e:
        return False, f"Validation error: {e.message}"


def validate_classification(data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate intent classification data.

    Args:
        data: Dictionary containing classification result

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        validate(instance=data, schema=CLASSIFICATION_SCHEMA)
        return True, None
    except ValidationError as e:
        return False, f"Validation error: {e.message}"


def validate_metrics(metrics: Dict[str, Any], category: str) -> tuple[bool, Optional[str]]:
    """
    Validate metrics based on category.

    Different categories expect different metric types:
    - 运动: distance_km, duration_min, count
    - 学习: duration_min, pages, count
    - 睡眠: sleep_hours, wake_time, bedtime
    - 情绪: score (1-10)
    - 饮食: calories, meals

    Args:
        metrics: Dictionary of metrics
        category: Habit category

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(metrics, dict):
        return False, "Metrics must be a dictionary"

    # Category-specific validation
    category_rules = {
        "运动": {
            "allowed": ["distance_km", "duration_min", "count", "steps"],
            "required": []
        },
        "学习": {
            "allowed": ["duration_min", "pages", "count", "courses"],
            "required": []
        },
        "睡眠": {
            "allowed": ["sleep_hours", "wake_time", "bedtime", "quality"],
            "required": []
        },
        "情绪": {
            "allowed": ["score", "intensity"],
            "required": []
        },
        "饮食": {
            "allowed": ["calories", "meals", "water_ml"],
            "required": []
        },
        "其他": {
            "allowed": [],  # Any metrics allowed
            "required": []
        }
    }

    if category in category_rules:
        rules = category_rules[category]
        if rules["allowed"]:
            for key in metrics.keys():
                if key not in rules["allowed"]:
                    return False, f"Invalid metric for {category}: {key}"

    return True, None


def validate_date(date_string: str) -> tuple[bool, Optional[str]]:
    """
    Validate date string in YYYY-MM-DD format.

    Args:
        date_string: Date string to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        datetime.strptime(date_string, "%Y-%m-%d")
        return True, None
    except ValueError:
        return False, f"Invalid date format: {date_string}. Expected YYYY-MM-DD"


def validate_time(time_string: str) -> tuple[bool, Optional[str]]:
    """
    Validate time string in HH:MM format.

    Args:
        time_string: Time string to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    pattern = r"^([01]\d|2[0-3]):([0-5]\d)$"
    if re.match(pattern, time_string):
        return True, None
    return False, f"Invalid time format: {time_string}. Expected HH:MM"


def sanitize_note(note: Optional[str]) -> Optional[str]:
    """
    Sanitize user note input.

    Args:
        note: Raw note string

    Returns:
        Sanitized note string or None
    """
    if note is None:
        return None

    # Remove excessive whitespace
    note = " ".join(note.split())

    # Limit length
    if len(note) > 500:
        note = note[:497] + "..."

    return note if note else None


def validate_entry_data(data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Comprehensive validation for habit entry data.

    This combines all validation checks for a complete entry.

    Args:
        data: Dictionary with all entry fields

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        >>> entry = {
        ...     "raw_input": "今天跑了5公里",
        ...     "category": "运动",
        ...     "mood": "positive",
        ...     "metrics": {"distance_km": 5.0}
        ... }
        >>> is_valid, error = validate_entry_data(entry)
        >>> print(is_valid)
        True
    """
    # Check required fields
    required_fields = ["raw_input", "category", "mood", "metrics"]
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"

    # Validate extraction schema
    is_valid, error = validate_extraction(data)
    if not is_valid:
        return False, error

    # Validate metrics for category
    is_valid, error = validate_metrics(data["metrics"], data["category"])
    if not is_valid:
        return False, error

    # Validate raw_input
    if not isinstance(data["raw_input"], str) or len(data["raw_input"]) == 0:
        return False, "raw_input must be a non-empty string"

    # Sanitize note
    if "note" in data:
        data["note"] = sanitize_note(data["note"])

    return True, None


if __name__ == "__main__":
    # Test: Validation examples
    print("Testing validators...")
    print("=" * 60)

    # Valid extraction
    valid_data = {
        "category": "运动",
        "mood": "positive",
        "metrics": {"distance_km": 5.0},
        "note": None
    }
    is_valid, error = validate_extraction(valid_data)
    print(f"Valid extraction: {is_valid}")

    # Invalid extraction (wrong category)
    invalid_data = {
        "category": "invalid",
        "mood": "positive",
        "metrics": {}
    }
    is_valid, error = validate_extraction(invalid_data)
    print(f"Invalid extraction: {is_valid}, error: {error}")

    # Date validation
    print(f"Valid date: {validate_date('2026-01-10')}")
    print(f"Invalid date: {validate_date('2026/01/10')}")

    # Time validation
    print(f"Valid time: {validate_time('06:30')}")
    print(f"Invalid time: {validate_time('25:00')}")
