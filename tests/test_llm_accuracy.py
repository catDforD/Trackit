"""
LLM Extraction Accuracy Test Suite for Trackit.

This script tests the accuracy of HabitExtractor across diverse input types.
It measures how well the LLM extracts structured data from natural language.

Author: Trackit Development
"""

import os
import sys
import json
from typing import Dict, List, Any, Tuple
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.llm.extractors import HabitExtractor
from src.config.settings import settings


class ExtractionAccuracyTest:
    """
    Test suite for measuring extraction accuracy.

    Test categories:
    1. Exercise (运动) - running, gym, sports
    2. Study (学习) - reading, courses, practice
    3. Sleep (睡眠) - wake time, sleep duration
    4. Mood (情绪) - emotional states
    5. Diet (饮食) - meals, nutrition
    6. Complex - multiple categories in one input
    7. Edge cases - ambiguous inputs
    """

    # Test cases with expected outputs
    TEST_CASES = [
        # ===== Exercise Category =====
        {
            "input": "今天跑了5公里，感觉不错",
            "expected": {
                "category": "运动",
                "mood": "positive",
                "metrics": {"distance_km": 5.0}
            },
            "category": "exercise",
            "description": "Simple running with distance"
        },
        {
            "input": "健身房练了1个小时，举铁",
            "expected": {
                "category": "运动",
                "mood": "neutral",
                "metrics": {"duration_min": 60}
            },
            "category": "exercise",
            "description": "Gym workout with duration"
        },
        {
            "input": "打了30分钟篮球",
            "expected": {
                "category": "运动",
                "mood": "neutral",
                "metrics": {"duration_min": 30}
            },
            "category": "exercise",
            "description": "Sports with duration"
        },
        {
            "input": "今天游泳1500米，太累了",
            "expected": {
                "category": "运动",
                "mood": "negative",
                "metrics": {"distance_m": 1500}
            },
            "category": "exercise",
            "description": "Swimming with negative mood"
        },
        {
            "input": "骑行20公里",
            "expected": {
                "category": "运动",
                "mood": "neutral",
                "metrics": {"distance_km": 20}
            },
            "category": "exercise",
            "description": "Cycling with distance"
        },

        # ===== Study Category =====
        {
            "input": "今天读了50页书",
            "expected": {
                "category": "学习",
                "mood": "neutral",
                "metrics": {"pages": 50}
            },
            "category": "study",
            "description": "Reading with page count"
        },
        {
            "input": "学习了2小时Python",
            "expected": {
                "category": "学习",
                "mood": "neutral",
                "metrics": {"duration_min": 120, "subject": "Python"}
            },
            "category": "study",
            "description": "Study with duration and subject"
        },
        {
            "input": "完成了一门在线课程，很有成就感",
            "expected": {
                "category": "学习",
                "mood": "positive",
                "metrics": {"count": 1}
            },
            "category": "study",
            "description": "Course completion with achievement"
        },
        {
            "input": "背了100个单词",
            "expected": {
                "category": "学习",
                "mood": "neutral",
                "metrics": {"count": 100}
            },
            "category": "study",
            "description": "Vocabulary with count"
        },

        # ===== Sleep Category =====
        {
            "input": "6点半起床，早起成功！",
            "expected": {
                "category": "睡眠",
                "mood": "positive",
                "metrics": {"wake_time": "06:30"}
            },
            "category": "sleep",
            "description": "Early wake time"
        },
        {
            "input": "昨晚只睡了5小时，好困",
            "expected": {
                "category": "睡眠",
                "mood": "negative",
                "metrics": {"sleep_hours": 5}
            },
            "category": "sleep",
            "description": "Short sleep with negative mood"
        },
        {
            "input": "睡了8个小时，精神饱满",
            "expected": {
                "category": "睡眠",
                "mood": "positive",
                "metrics": {"sleep_hours": 8}
            },
            "category": "sleep",
            "description": "Good sleep with positive mood"
        },
        {
            "input": "9点才起，起晚了",
            "expected": {
                "category": "睡眠",
                "mood": "negative",
                "metrics": {"wake_time": "09:00"}
            },
            "category": "sleep",
            "description": "Late wake time"
        },

        # ===== Mood Category =====
        {
            "input": "今天心情一般般",
            "expected": {
                "category": "情绪",
                "mood": "neutral",
                "metrics": {}
            },
            "category": "mood",
            "description": "Neutral mood"
        },
        {
            "input": "今天超级开心，状态极佳",
            "expected": {
                "category": "情绪",
                "mood": "positive",
                "metrics": {}
            },
            "category": "mood",
            "description": "Very positive mood"
        },
        {
            "input": "感觉很焦虑，压力很大",
            "expected": {
                "category": "情绪",
                "mood": "negative",
                "metrics": {}
            },
            "category": "mood",
            "description": "Anxious mood"
        },
        {
            "input": "有点沮丧，但不至于太糟",
            "expected": {
                "category": "情绪",
                "mood": "negative",
                "metrics": {}
            },
            "category": "mood",
            "description": "Mildly negative mood"
        },

        # ===== Diet Category =====
        {
            "input": "今天吃了蔬菜沙拉，很健康",
            "expected": {
                "category": "饮食",
                "mood": "positive",
                "metrics": {}
            },
            "category": "diet",
            "description": "Healthy meal"
        },
        {
            "input": "喝了8杯水",
            "expected": {
                "category": "饮食",
                "mood": "neutral",
                "metrics": {"glasses": 8}
            },
            "category": "diet",
            "description": "Water intake with count"
        },
        {
            "input": "没吃早饭",
            "expected": {
                "category": "饮食",
                "mood": "neutral",
                "metrics": {}
            },
            "category": "diet",
            "description": "Missed meal"
        },

        # ===== Complex & Edge Cases =====
        {
            "input": "今天状态很差，没学习",
            "expected": {
                "category": "学习",
                "mood": "negative",
                "metrics": {}
            },
            "category": "complex",
            "description": "Negative study record"
        },
        {
            "input": "今天什么都没做",
            "expected": {
                "category": "其他",
                "mood": "neutral",
                "metrics": {}
            },
            "category": "edge_case",
            "description": "Vague input"
        },
        {
            "input": "早上跑了步，晚上读了书",
            "expected": {
                "category": "运动",  # Should pick first/most prominent
                "mood": "neutral",
                "metrics": {}
            },
            "category": "complex",
            "description": "Multiple activities"
        },
    ]

    def __init__(self):
        """Initialize the test suite."""
        self.extractor = HabitExtractor()
        self.results = []
        self.stats = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "category_accuracy": {},
            "mood_accuracy": 0,
            "metrics_accuracy": 0
        }

    def compare_results(
        self,
        extracted: Dict[str, Any],
        expected: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Compare extracted result with expected result.

        Args:
            extracted: The result from LLM extraction
            expected: The expected result

        Returns:
            Tuple of (passed, list of discrepancies)
        """
        discrepancies = []

        # Check category
        if extracted.get("category") != expected.get("category"):
            discrepancies.append(
                f"Category: expected '{expected.get('category')}', "
                f"got '{extracted.get('category')}'"
            )

        # Check mood
        if extracted.get("mood") != expected.get("mood"):
            discrepancies.append(
                f"Mood: expected '{expected.get('mood')}', "
                f"got '{extracted.get('mood')}'"
            )

        # Check metrics (more flexible - check if expected keys exist)
        expected_metrics = expected.get("metrics", {})
        extracted_metrics = extracted.get("metrics", {})

        for key, value in expected_metrics.items():
            if key not in extracted_metrics:
                discrepancies.append(
                    f"Metrics: missing key '{key}'"
                )
            elif extracted_metrics[key] != value:
                # Allow small numerical differences
                if isinstance(value, (int, float)) and isinstance(extracted_metrics[key], (int, float)):
                    if abs(extracted_metrics[key] - value) > 0.01:
                        discrepancies.append(
                            f"Metrics: '{key}': expected {value}, "
                            f"got {extracted_metrics[key]}"
                        )
                else:
                    discrepancies.append(
                        f"Metrics: '{key}': expected {value}, "
                        f"got {extracted_metrics[key]}"
                    )

        return len(discrepancies) == 0, discrepancies

    def run_single_test(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a single test case.

        Args:
            test_case: Dictionary with input, expected, category, description

        Returns:
            Test result dictionary
        """
        print(f"\n{'='*70}")
        print(f"Test: {test_case['description']}")
        print(f"Category: {test_case['category']}")
        print(f"Input: {test_case['input']}")
        print(f"{'='*70}")

        # Extract
        result = self.extractor.extract(test_case["input"])

        # Compare
        passed, discrepancies = self.compare_results(
            result,
            test_case["expected"]
        )

        # Display results
        print(f"\nExpected:")
        print(f"  Category: {test_case['expected']['category']}")
        print(f"  Mood: {test_case['expected']['mood']}")
        print(f"  Metrics: {test_case['expected']['metrics']}")

        print(f"\nExtracted:")
        print(f"  Category: {result.get('category')}")
        print(f"  Mood: {result.get('mood')}")
        print(f"  Metrics: {result.get('metrics')}")
        print(f"  Valid: {result.get('is_valid')}")

        if passed:
            print(f"\n✅ PASSED")
        else:
            print(f"\n❌ FAILED")
            print("Discrepancies:")
            for d in discrepancies:
                print(f"  - {d}")

        return {
            "input": test_case["input"],
            "expected": test_case["expected"],
            "extracted": result,
            "passed": passed,
            "discrepancies": discrepancies,
            "category": test_case["category"],
            "description": test_case["description"]
        }

    def run_all_tests(self) -> Dict[str, Any]:
        """
        Run all test cases and generate statistics.

        Returns:
            Summary statistics dictionary
        """
        print("\n" + "="*70)
        print("LLM EXTRACTION ACCURACY TEST")
        print("="*70)
        print(f"Model: {settings.MODEL_EXTRACTION}")
        print(f"Provider: {settings.LLM_PROVIDER}")
        print(f"Total test cases: {len(self.TEST_CASES)}")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Run all tests
        for test_case in self.TEST_CASES:
            result = self.run_single_test(test_case)
            self.results.append(result)
            self.stats["total"] += 1
            if result["passed"]:
                self.stats["passed"] += 1
            else:
                self.stats["failed"] += 1

        # Calculate category-wise accuracy
        category_counts = {}
        category_passed = {}
        for result in self.results:
            cat = result["category"]
            category_counts[cat] = category_counts.get(cat, 0) + 1
            if result["passed"]:
                category_passed[cat] = category_passed.get(cat, 0) + 1

        for cat in category_counts:
            self.stats["category_accuracy"][cat] = (
                category_passed.get(cat, 0) / category_counts[cat] * 100
            )

        # Calculate mood accuracy
        mood_correct = sum(
            1 for r in self.results
            if r["extracted"].get("mood") == r["expected"].get("mood")
        )
        self.stats["mood_accuracy"] = mood_correct / len(self.results) * 100

        # Calculate metrics accuracy (has expected metrics)
        metrics_correct = sum(
            1 for r in self.results
            if not r["expected"]["metrics"] or  # No metrics expected
            all(k in r["extracted"].get("metrics", {})
                for k in r["expected"]["metrics"])
        )
        self.stats["metrics_accuracy"] = metrics_correct / len(self.results) * 100

        # Print summary
        self.print_summary()

        return self.stats

    def print_summary(self):
        """Print test summary statistics."""
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)

        print(f"\nOverall Results:")
        print(f"  Total: {self.stats['total']}")
        print(f"  Passed: {self.stats['passed']} ({self.stats['passed']/self.stats['total']*100:.1f}%)")
        print(f"  Failed: {self.stats['failed']} ({self.stats['failed']/self.stats['total']*100:.1f}%)")

        print(f"\nField Accuracy:")
        print(f"  Mood: {self.stats['mood_accuracy']:.1f}%")
        print(f"  Metrics: {self.stats['metrics_accuracy']:.1f}%")

        print(f"\nCategory-wise Accuracy:")
        for cat, acc in sorted(self.stats["category_accuracy"].items()):
            count = sum(1 for r in self.results if r["category"] == cat)
            print(f"  {cat}: {acc:.1f}% ({count} tests)")

        # Show failed tests
        failed = [r for r in self.results if not r["passed"]]
        if failed:
            print(f"\n{'='*70}")
            print("FAILED TESTS ({len(failed)}):")
            print("="*70)
            for result in failed:
                print(f"\n{result['description']}")
                print(f"  Input: {result['input']}")
                for d in result["discrepancies"]:
                    print(f"  - {d}")

        print(f"\n{'='*70}")
        print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)

    def save_results(self, filepath: str = "test_results.json"):
        """
        Save test results to JSON file.

        Args:
            filepath: Path to save results
        """
        output = {
            "timestamp": datetime.now().isoformat(),
            "model": settings.MODEL_EXTRACTION,
            "provider": settings.LLM_PROVIDER,
            "stats": self.stats,
            "results": self.results
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"\n✅ Results saved to: {filepath}")


def main():
    """Main entry point."""
    # Check if API key is configured
    if settings.LLM_PROVIDER == "anthropic" and not settings.ANTHROPIC_API_KEY:
        print("❌ Error: ANTHROPIC_API_KEY not configured")
        print("Please set up your .env file with the API key")
        return

    if settings.LLM_PROVIDER == "openai" and not settings.OPENAI_API_KEY:
        print("❌ Error: OPENAI_API_KEY not configured")
        print("Please set up your .env file with the API key")
        return

    # Run tests
    tester = ExtractionAccuracyTest()
    stats = tester.run_all_tests()

    # Save results
    results_dir = os.path.join(os.path.dirname(__file__), "..", "data", "test_results")
    os.makedirs(results_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_path = os.path.join(results_dir, f"extraction_accuracy_{timestamp}.json")
    tester.save_results(results_path)

    # Return exit code based on pass rate
    pass_rate = stats["passed"] / stats["total"]
    if pass_rate >= 0.9:
        print("\n🎉 Excellent! Accuracy >= 90%")
        sys.exit(0)
    elif pass_rate >= 0.75:
        print("\n✅ Good! Accuracy >= 75%")
        sys.exit(0)
    else:
        print(f"\n⚠️  Accuracy ({pass_rate*100:.1f}%) below 75% - consider improving prompts")
        sys.exit(1)


if __name__ == "__main__":
    main()
