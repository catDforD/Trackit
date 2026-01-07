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


class RecordingAgentError(Exception):
    """Base exception for RecordingAgent errors."""
    pass


class ExtractionError(RecordingAgentError):
    """Error during LLM extraction."""
    pass


class ValidationError(RecordingAgentError):
    """Error during data validation."""
    pass


class DatabaseError(RecordingAgentError):
    """Error during database operations."""
    pass


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

        # Default feedback templates
        self.feedback_templates = config.get("feedback_templates") if config else self._get_default_templates()

        # Error messages
        self.error_messages = {
            "extraction_failed": "抱歉，我没能理解这条记录。请换种说法试试？",
            "validation_failed": "记录格式有些问题，请提供更具体的信息。",
            "database_error": "保存记录时出错，请稍后重试。",
            "api_error": "AI服务暂时不可用，请稍后重试。",
            "unknown_error": "发生了未知错误，请稍后重试。"
        }

    def _get_default_templates(self) -> Dict[str, Dict[str, str]]:
        """
        Get default feedback templates for different categories and moods.

        Returns:
            Dictionary of feedback templates organized by category
        """
        return {
            "运动": {
                "positive": [
                    "太棒了！运动让人心情愉悦 🏃‍♂️",
                    "继续保持！坚持就是胜利 💪",
                    "运动完感觉很好吧？记录成功！"
                ],
                "neutral": [
                    "已记录运动，明天继续加油！",
                    "运动完成，继续保持！"
                ],
                "negative": [
                    "运动虽累，但完成了就很棒！",
                    "辛苦了，好好休息一下！"
                ]
            },
            "学习": {
                "positive": [
                    "学习使人进步！为你点赞 📚",
                    "太棒了！今天又学到了新知识 ✨",
                    "继续保持学习热情！"
                ],
                "neutral": [
                    "学习已记录，积少成多！",
                    "每一天的学习都在积累力量！"
                ],
                "negative": [
                    "学习遇到困难很正常，继续加油！",
                    "慢慢来，理解比速度更重要！"
                ]
            },
            "睡眠": {
                "positive": [
                    "良好的睡眠是健康的基础 😴",
                    "睡眠充足，精神饱满！"
                ],
                "neutral": [
                    "睡眠记录成功！",
                    "作息规律很重要！"
                ],
                "negative": [
                    "睡眠不好会影响状态，今晚早点休息 💤",
                    "尝试调整作息，改善睡眠质量！"
                ]
            },
            "情绪": {
                "positive": [
                    "保持积极心态，继续加油！✨",
                    "好心情传递好能量！",
                    "每天都保持这样积极的状态吧！"
                ],
                "neutral": [
                    "情绪记录成功！",
                    "记录心情，关注自我！"
                ],
                "negative": [
                    "理解你的感受，明天会更好的 💙",
                    "状态不好没关系，允许自己休息！",
                    "记录下来，释放压力！"
                ]
            },
            "饮食": {
                "positive": [
                    "健康饮食，身体更健康 🥗",
                    "吃得健康，生活更美好！"
                ],
                "neutral": [
                    "饮食已记录！",
                    "关注饮食，关爱健康！"
                ],
                "negative": [
                    "注意饮食平衡，身体是革命的本钱！",
                    "偶尔放纵没关系，明天注意调整！"
                ]
            }
        }

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
                - error_type: Type of error (if failed)
        """
        try:
            # Validate input
            if not user_input or not user_input.strip():
                return {
                    "success": False,
                    "error": "输入不能为空",
                    "error_type": "validation_error",
                    "user_input": user_input
                }

            # Step 1: Extract structured data
            try:
                extracted = self.extractor.extract_with_retry(
                    user_input=user_input,
                    max_attempts=3
                )
            except Exception as e:
                return {
                    "success": False,
                    "error": self.error_messages["extraction_failed"],
                    "error_type": "extraction_error",
                    "details": str(e),
                    "user_input": user_input
                }

            # Step 2: Validate extraction
            if not extracted.get("is_valid"):
                error_msg = extracted.get("error", "提取的数据验证失败")
                return {
                    "success": False,
                    "error": self.error_messages["validation_failed"],
                    "error_type": "validation_error",
                    "details": error_msg,
                    "extracted_data": extracted
                }

            # Step 3: Store in database
            try:
                entry_id = self.repository.add_entry(
                    raw_input=extracted["raw_input"],
                    category=extracted["category"],
                    mood=extracted["mood"],
                    metrics=extracted["metrics"],
                    note=extracted.get("note"),
                    entry_date=entry_date
                )
            except Exception as e:
                return {
                    "success": False,
                    "error": self.error_messages["database_error"],
                    "error_type": "database_error",
                    "details": str(e),
                    "extracted_data": extracted
                }

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
            # Catch-all for unexpected errors
            return {
                "success": False,
                "error": self.error_messages["unknown_error"],
                "error_type": "unknown_error",
                "details": str(e),
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
        import random

        category = extracted.get("category", "其他")
        mood = extracted.get("mood", "neutral")
        metrics = extracted.get("metrics", {})

        # Try to use custom template based on category and mood
        if category in self.feedback_templates:
            mood_templates = self.feedback_templates[category]

            # Get templates for the mood, fallback to neutral
            templates = mood_templates.get(
                mood,
                mood_templates.get("neutral", [])
            )

            if templates:
                # Randomly select from templates
                feedback = random.choice(templates)
            else:
                feedback = f"✓ 已记录：{category}"
        else:
            # Fallback for categories without templates
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
