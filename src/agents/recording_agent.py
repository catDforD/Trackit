"""
Recording agent for Trackit.

This agent handles the workflow of recording new habit entries:
1. Extract structured data from natural language
2. Validate the extracted data
3. Store in database
4. Generate user feedback

Author: Trackit Development
"""

from typing import Dict, Any, Optional
from .base_agent import BaseAgent
from ..database.repository import HabitRepository
from ..llm.extractors import HabitExtractor
from ..utils.validators import validate_entry_data
from ..config.settings import settings


class RecordingAgent(BaseAgent):
    """
    Agent for recording habit entries.

    This agent orchestrates the complete recording workflow:
    - Extracts structured data from user input
    - Validates the data
    - Saves to database
    - Provides user feedback

    Example:
        >>> agent = RecordingAgent()
        >>> result = agent.execute(user_input="今天跑了5公里")
        >>> print(result["success"])
        True
        >>> print(result["feedback"])
        已记录：运动 - 5公里
    """

    def __init__(
        self,
        repository: Optional[HabitRepository] = None,
        extractor: Optional[HabitExtractor] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the recording agent.

        Args:
            repository: Database repository (creates default if not provided)
            extractor: Habit extractor (creates default if not provided)
            config: Optional configuration
        """
        super().__init__(name="RecordingAgent", config=config)

        self.repository = repository or HabitRepository(settings.DB_PATH)
        self.extractor = extractor or HabitExtractor()

        # Optional: Custom feedback messages
        self.feedback_templates = config.get("feedback_templates") if config else None

    def execute(
        self,
        user_input: str,
        entry_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute the recording workflow.

        Args:
            user_input: Natural language input from user
            entry_date: Optional date (YYYY-MM-DD), defaults to today

        Returns:
            Dictionary with:
                - success: Boolean indicating success
                - entry_id: ID of created entry (if successful)
                - feedback: User-friendly feedback message
                - extracted_data: The extracted structured data
                - error: Error message (if failed)
        """
        try:
            # Step 1: Extract structured data
            extracted = self.extractor.extract_with_retry(
                user_input=user_input,
                max_attempts=3
            )

            # Step 2: Validate extraction
            if not extracted.get("is_valid"):
                return {
                    "success": False,
                    "error": extracted.get("error", "Extraction validation failed"),
                    "extracted_data": extracted
                }

            # Step 3: Store in database
            entry_id = self.repository.add_entry(
                raw_input=extracted["raw_input"],
                category=extracted["category"],
                mood=extracted["mood"],
                metrics=extracted["metrics"],
                note=extracted.get("note"),
                entry_date=entry_date
            )

            # Step 4: Generate user feedback
            feedback = self._generate_feedback(extracted)

            # Step 5: Update agent state
            self.update_state({
                "last_entry_id": entry_id,
                "last_category": extracted["category"],
                "last_mood": extracted["mood"]
            })

            # Log execution
            self.log_execution()

            return {
                "success": True,
                "entry_id": entry_id,
                "feedback": feedback,
                "extracted_data": extracted
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "user_input": user_input
            }

    def _generate_feedback(self, extracted: Dict[str, Any]) -> str:
        """
        Generate user-friendly feedback message.

        Args:
            extracted: Extracted and validated data

        Returns:
            Feedback message string
        """
        category = extracted.get("category", "其他")
        mood = extracted.get("mood", "neutral")
        metrics = extracted.get("metrics", {})

        # Custom template if provided
        if self.feedback_templates and category in self.feedback_templates:
            return self.feedback_templates[category].format(
                category=category,
                mood=mood,
                **metrics
            )

        # Default feedback templates
        mood_emoji = {
            "positive": "😊",
            "neutral": "😐",
            "negative": "😔"
        }

        emoji = mood_emoji.get(mood, "")
        feedback = f"✓ 已记录：{category} {emoji}"

        # Add metrics details
        if metrics:
            metric_details = []
            for key, value in metrics.items():
                # Format metric names nicely
                metric_name = key.replace("_", " ").replace("km", "公里")
                metric_details.append(f"{metric_name}: {value}")

            if metric_details:
                feedback += f"\n  {' | '.join(metric_details)}"

        return feedback

    def validate_extraction(
        self,
        user_input: str
    ) -> tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Validate extraction without saving to database.

        Useful for previewing what would be extracted.

        Args:
            user_input: Natural language input

        Returns:
            Tuple of (is_valid, extracted_data, error_message)
        """
        try:
            extracted = self.extractor.extract(user_input, validate=True)

            if extracted.get("is_valid"):
                return True, extracted, None
            else:
                return False, extracted, extracted.get("error")

        except Exception as e:
            return False, None, str(e)


# Convenience functions
def record_habit(user_input: str, db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Quick function to record a habit entry.

    Args:
        user_input: Natural language input
        db_path: Optional database path

    Returns:
        Result dictionary
    """
    repository = HabitRepository(db_path) if db_path else HabitRepository()
    agent = RecordingAgent(repository=repository)
    return agent.execute(user_input=user_input)


if __name__ == "__main__":
    # Test: Recording agent functionality
    print("Testing RecordingAgent...")
    print("=" * 60)

    from ..database.schema import init_database

    # Initialize database
    init_database()

    # Create agent
    agent = RecordingAgent()

    # Test recordings
    test_inputs = [
        "今天跑了5公里，感觉不错",
        "今天状态很差，什么都没做",
        "6点半起床，早起成功！",
        "今天心情一般般"
    ]

    for test_input in test_inputs:
        print(f"\nInput: {test_input}")
        print("-" * 60)

        result = agent.execute(user_input=test_input)

        if result["success"]:
            print(f"✓ Success!")
            print(f"  Entry ID: {result['entry_id']}")
            print(f"  Feedback: {result['feedback']}")
            print(f"  Extracted: {result['extracted_data']['category']} - {result['extracted_data']['mood']}")
            print(f"  Metrics: {result['extracted_data']['metrics']}")
        else:
            print(f"✗ Failed: {result['error']}")

    # Test statistics
    print("\n" + "=" * 60)
    print("Agent Statistics:")
    print(agent.get_stats())
