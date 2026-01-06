"""
Information extraction module for Trackit.

This module uses LLMs to extract structured data from natural language input.
It handles habit tracking entries, intent classification, and data parsing.

Author: Trackit Development
"""

import json
from typing import Dict, Any, List, Optional
from ..llm.client import LLMClient, extract_json_from_response
from ..config.settings import settings
from ..config.prompts import Prompts
from ..utils.validators import (
    validate_extraction,
    validate_entry_data,
    sanitize_note
)
from ..utils.cache import ExtractionCache


class HabitExtractor:
    """
    Extract structured habit data from natural language input.

    This class handles the extraction of:
    - Category (运动/学习/睡眠/情绪/饮食/其他)
    - Mood (positive/neutral/negative)
    - Metrics (quantitative data like distance, duration, etc.)
    - Notes (additional context)

    Example:
        >>> extractor = HabitExtractor()
        >>> result = extractor.extract("今天跑了5公里，感觉不错")
        >>> print(result["category"])
        运动
        >>> print(result["metrics"]["distance_km"])
        5.0
    """

    def __init__(
        self,
        client: Optional[LLMClient] = None,
        use_cache: bool = True,
        cache: Optional[ExtractionCache] = None
    ):
        """
        Initialize the extractor.

        Args:
            client: LLM client instance (creates new one if not provided)
            use_cache: Whether to use extraction cache
            cache: Custom cache instance (creates default if not provided)
        """
        self.client = client or LLMClient()
        self.model = settings.MODEL_EXTRACTION
        self.use_cache = use_cache
        self.cache = cache or (ExtractionCache() if use_cache else None)

    def extract(
        self,
        user_input: str,
        validate: bool = True,
        use_cache: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Extract structured data from user input.

        Args:
            user_input: Raw natural language input
            validate: Whether to validate the extracted data
            use_cache: Override default cache setting

        Returns:
            Dictionary with extracted data:
                - raw_input: Original input
                - category: Habit category
                - mood: Mood label
                - metrics: Quantitative metrics
                - note: Additional notes
                - is_valid: Validation result
                - error: Error message if validation failed
                - cached: Whether result came from cache

        Example:
            >>> result = extractor.extract("今天跑了5公里")
            >>> print(result["category"])
            '运动'
        """
        # Determine whether to use cache
        should_use_cache = use_cache if use_cache is not None else self.use_cache

        # Check cache first
        if should_use_cache and self.cache is not None:
            cached_result = self.cache.get(user_input)
            if cached_result is not None:
                # Mark as cached and return
                cached_result["cached"] = True
                return cached_result

        try:
            # Generate prompt
            prompt = Prompts.get_extraction_prompt(user_input)

            # Call LLM
            response = self.client.call_with_retry(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                max_tokens=1024,
                temperature=0.0
            )

            # Extract JSON from response
            extracted_data = extract_json_from_response(response["content"])

            # Add raw_input
            extracted_data["raw_input"] = user_input

            # Validate if requested
            if validate:
                is_valid, error = validate_entry_data(extracted_data)
                extracted_data["is_valid"] = is_valid
                extracted_data["error"] = error
            else:
                extracted_data["is_valid"] = True
                extracted_data["error"] = None

            # Store in cache (without cached flag)
            if should_use_cache and self.cache is not None:
                # Store clean copy without cached flag
                cache_data = extracted_data.copy()
                cache_data.pop("cached", None)
                self.cache.store(user_input, cache_data)

            # Mark as not cached for this return
            extracted_data["cached"] = False
            return extracted_data

        except Exception as e:
            return {
                "raw_input": user_input,
                "category": "其他",
                "mood": "neutral",
                "metrics": {},
                "note": f"Extraction failed: {str(e)}",
                "is_valid": False,
                "error": str(e),
                "cached": False
            }

    def batch_extract(
        self,
        inputs: List[str],
        validate: bool = True,
        show_progress: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Extract from multiple inputs in batch.

        Args:
            inputs: List of user input strings
            validate: Whether to validate each extraction
            show_progress: Whether to show progress (for batch operations)

        Returns:
            List of extraction results with batch metadata:
                - results: List of extraction results
                - summary: Batch statistics
                    - total: Total number of inputs
                    - cached: Number from cache
                    - api_calls: Number of API calls made
                    - cache_hit_rate: Cache hit rate (0-1)
        """
        results = []
        cached_count = 0
        api_calls = 0

        for i, user_input in enumerate(inputs):
            if show_progress and (i + 1) % 10 == 0:
                print(f"Processing {i + 1}/{len(inputs)}...")

            result = self.extract(user_input, validate=validate)
            results.append(result)

            if result.get("cached"):
                cached_count += 1
            else:
                api_calls += 1

        # Calculate statistics
        cache_hit_rate = cached_count / len(inputs) if inputs else 0

        return {
            "results": results,
            "summary": {
                "total": len(inputs),
                "cached": cached_count,
                "api_calls": api_calls,
                "cache_hit_rate": cache_hit_rate
            }
        }

    def get_cache_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get cache statistics.

        Returns:
            Cache statistics dictionary or None if cache not enabled
        """
        if self.cache:
            return self.cache.get_stats()
        return None

    def clear_cache(self) -> None:
        """Clear the extraction cache."""
        if self.cache:
            self.cache.clear()

    def extract_with_retry(
        self,
        user_input: str,
        max_attempts: int = 3
    ) -> Dict[str, Any]:
        """
        Extract with automatic retry on validation failure.

        If extraction fails validation, retry with refined prompt.

        Args:
            user_input: Raw input text
            max_attempts: Maximum extraction attempts

        Returns:
            Extraction result (best attempt)
        """
        best_result = None
        best_score = 0

        for attempt in range(max_attempts):
            result = self.extract(user_input, validate=True)

            if result.get("is_valid"):
                return result

            # Score based on how much valid data we got
            score = 0
            if result.get("category") and result["category"] != "其他":
                score += 1
            if result.get("metrics"):
                score += 1

            if score > best_score:
                best_score = score
                best_result = result

        # Return best attempt if all failed
        return best_result or {
            "raw_input": user_input,
            "category": "其他",
            "mood": "neutral",
            "metrics": {},
            "note": "Extraction failed after multiple attempts",
            "is_valid": False
        }


class IntentClassifier:
    """
    Classify user query intent.

    Determines what the user wants to do:
    - RECORD: Record a habit
    - COUNT: Query frequency/count
    - LAST: Query most recent occurrence
    - SUMMARY: Get summary statistics
    - COMPARISON: Compare time periods
    - REPORT: Generate report
    - GENERAL: General conversation

    Example:
        >>> classifier = IntentClassifier()
        >>> result = classifier.classify("我这周运动了几次？")
        >>> print(result["intent"])
        COUNT
    """

    def __init__(self, client: Optional[LLMClient] = None):
        """
        Initialize the classifier.

        Args:
            client: LLM client instance
        """
        self.client = client or LLMClient()
        self.model = settings.MODEL_CLASSIFICATION

    def classify(self, query: str) -> Dict[str, Any]:
        """
        Classify user query intent.

        Args:
            query: User's query text

        Returns:
            Dictionary with:
                - intent: Intent category
                - entities: Extracted entities (category, timeframe, etc.)
                - raw_query: Original query

        Example:
            >>> result = classifier.classify("我这周运动了几次？")
            >>> print(result["intent"])
            'COUNT'
            >>> print(result["entities"]["category"])
            '运动'
        """
        try:
            # Generate prompt
            prompt = Prompts.get_classification_prompt(query)

            # Call LLM
            response = self.client.call_with_retry(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                max_tokens=512,
                temperature=0.0
            )

            # Extract classification
            classification = extract_json_from_response(response["content"])
            classification["raw_query"] = query

            return classification

        except Exception as e:
            # Fallback to GENERAL on error
            return {
                "intent": "GENERAL",
                "entities": {
                    "category": None,
                    "timeframe": None,
                    "specific_date": None
                },
                "raw_query": query,
                "error": str(e)
            }


# Convenience functions
def extract_habit(user_input: str) -> Dict[str, Any]:
    """
    Quick function to extract habit data.

    Args:
        user_input: Natural language input

    Returns:
        Extracted data dictionary
    """
    extractor = HabitExtractor()
    return extractor.extract(user_input)


def classify_intent(query: str) -> Dict[str, Any]:
    """
    Quick function to classify query intent.

    Args:
        query: User query text

    Returns:
        Classification dictionary
    """
    classifier = IntentClassifier()
    return classifier.classify(query)


if __name__ == "__main__":
    # Test: Extraction examples
    print("Testing HabitExtractor...")
    print("=" * 60)

    extractor = HabitExtractor()

    test_inputs = [
        "今天跑了5公里，感觉不错",
        "今天状态很差，没学习",
        "6点半起床，早起成功！",
        "今天心情一般般"
    ]

    for test_input in test_inputs:
        print(f"\nInput: {test_input}")
        try:
            result = extractor.extract(test_input)
            if result.get("is_valid"):
                print(f"  Category: {result.get('category')}")
                print(f"  Mood: {result.get('mood')}")
                print(f"  Metrics: {result.get('metrics')}")
            else:
                print(f"  Error: {result.get('error')}")
        except Exception as e:
            print(f"  Failed: {e}")

    # Test: Intent classification
    print("\n" + "=" * 60)
    print("Testing IntentClassifier...")
    print("=" * 60)

    classifier = IntentClassifier()

    test_queries = [
        "我这周运动了几次？",
        "生成周报",
        "今天跑了5公里"
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")
        try:
            result = classifier.classify(query)
            print(f"  Intent: {result.get('intent')}")
            print(f"  Entities: {result.get('entities')}")
        except Exception as e:
            print(f"  Failed: {e}")
