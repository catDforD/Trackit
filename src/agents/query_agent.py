"""
Query agent for Trackit.

This agent handles user queries about habit records:
1. Classify query intent
2. Execute appropriate database query
3. Generate natural language response

Supported query types:
- COUNT: "我这周运动了几次？"
- LAST: "上次跑步是什么时候？"
- SUMMARY: "我这周的习惯怎么样？"
- COMPARISON: "这周比上周怎么样？"

Author: Trackit Development
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from .base_agent import BaseAgent
from ..database.repository import HabitRepository
from ..llm.extractors import IntentClassifier
from ..config.settings import settings


class QueryAgentError(Exception):
    """Base exception for QueryAgent errors."""
    pass


class QueryAgent(BaseAgent):
    """
    Agent for querying habit records.

    This agent understands natural language queries and returns
    relevant information from the database.

    Example:
        >>> agent = QueryAgent()
        >>> result = agent.execute(query="我这周运动了几次？")
        >>> print(result["response"])
        这周你运动了3次，总计12公里。
    """

    # Intent types
    INTENT_COUNT = "COUNT"
    INTENT_LAST = "LAST"
    INTENT_SUMMARY = "SUMMARY"
    INTENT_COMPARISON = "COMPARISON"
    INTENT_GENERAL = "GENERAL"

    def __init__(
        self,
        repository: Optional[HabitRepository] = None,
        classifier: Optional[IntentClassifier] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the query agent.

        Args:
            repository: Database repository (creates default if not provided)
            classifier: Intent classifier (creates default if not provided)
            config: Optional configuration
        """
        super().__init__(name="QueryAgent", config=config)

        self.repository = repository or HabitRepository(settings.DB_PATH)
        self.classifier = classifier or IntentClassifier()

        # Query response templates
        self.response_templates = {
            "count": {
                "运动": "这{timeframe}你运动了{count}次{metrics_detail}。",
                "学习": "这{timeframe}你学习了{count}次{metrics_detail}。",
                "睡眠": "这{timeframe}睡眠记录{count}次{metrics_detail}。",
                "情绪": "这{timeframe}情绪记录{count}次，积极率{positive_rate:.0%}。",
                "饮食": "这{timeframe}饮食记录{count}次{metrics_detail}。",
                "default": "这{timeframe}{category}记录{count}次{metrics_detail}。"
            },
            "last": {
                "运动": "上次运动是在{date}，{details}",
                "学习": "上次学习是在{date}，{details}",
                "睡眠": "上次睡眠记录是{date}，{details}",
                "default": "上次{category}是在{date}，{details}"
            },
            "summary": {
                "运动": "这{timeframe}运动{count}次，总计{total_distance}公里。平均{avg_distance:.1f}公里/次。",
                "学习": "这{timeframe}学习{count}次，总时长{total_hours}小时。",
                "default": "这{timeframe}记录{count}条，其中{positive}条积极情绪。"
            },
            "comparison": {
                "positive": "这周比上周好！{category}增加了{diff}次。",
                "neutral": "这周和上周差不多，{category}{count}次。",
                "negative": "这周比上周少{diff}次{category}，继续加油！",
                "default": "这周{category}{count}次，上周{last_count}次。"
            }
        }

    def execute(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a query.

        Args:
            query: Natural language query from user
            context: Optional context (e.g., current date, user preferences)

        Returns:
            Dictionary with:
                - success: Boolean indicating success
                - response: Natural language response
                - data: Query results data
                - intent: Classified intent
                - error: Error message (if failed)
        """
        try:
            # Validate input
            if not query or not query.strip():
                return {
                    "success": False,
                    "error": "查询不能为空",
                    "response": "请问你想了解什么？"
                }

            # Step 1: Classify intent
            classification = self.classifier.classify(query)
            intent = classification.get("intent", self.INTENT_GENERAL)
            entities = classification.get("entities", {})

            # Step 2: Execute query based on intent
            result = self._execute_query(intent, entities, context)

            # Step 3: Generate natural language response
            response = self._generate_response(intent, result, entities)

            # Step 4: Update agent state
            self.update_state({
                "last_query": query,
                "last_intent": intent,
                "last_result": result
            })

            # Log execution
            self.log_execution()

            return {
                "success": True,
                "response": response,
                "data": result,
                "intent": intent,
                "classification": classification
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response": "抱歉，查询时出错了。请换种方式试试。"
            }

    def _execute_query(
        self,
        intent: str,
        entities: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Execute the appropriate database query.

        Args:
            intent: Query intent
            entities: Extracted entities
            context: Optional context

        Returns:
            Query results dictionary
        """
        if intent == self.INTENT_COUNT:
            return self._query_count(entities, context)
        elif intent == self.INTENT_LAST:
            return self._query_last(entities, context)
        elif intent == self.INTENT_SUMMARY:
            return self._query_summary(entities, context)
        elif intent == self.INTENT_COMPARISON:
            return self._query_comparison(entities, context)
        else:
            return {"type": "general", "message": "我不确定如何回答这个问题"}

    def _query_count(
        self,
        entities: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Query count of records.

        Args:
            entities: Extracted entities (category, timeframe)
            context: Optional context (reserved for future use)

        Returns:
            Count results
        """
        # Context parameter reserved for future personalization features
        _ = context  # Explicitly mark as unused
        category = entities.get("category")
        timeframe = entities.get("timeframe", "week")

        # Determine date range
        start_date, end_date = self._parse_timeframe(timeframe)

        # Query database
        if category:
            entries = self.repository.get_entries_by_category_and_date_range(
                category=category,
                start_date=start_date,
                end_date=end_date
            )
        else:
            entries = self.repository.get_entries_by_date_range(start_date, end_date)

        # Calculate metrics
        count = len(entries)
        metrics_summary = self._summarize_metrics(entries)

        return {
            "type": "count",
            "count": count,
            "category": category,
            "timeframe": timeframe,
            "metrics": metrics_summary,
            "entries": entries
        }

    def _query_last(
        self,
        entities: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Query most recent record.

        Args:
            entities: Extracted entities
            context: Optional context (reserved for future use)

        Returns:
            Last entry details
        """
        # Context parameter reserved for future personalization features
        _ = context  # Explicitly mark as unused
        category = entities.get("category")

        # Get most recent entry
        entries = self.repository.get_all_entries(limit=1)

        if not entries:
            return {
                "type": "last",
                "found": False,
                "message": "还没有任何记录"
            }

        # Filter by category if specified
        if category:
            category_entries = self.repository.get_entries_by_category(category, limit=1)
            if not category_entries:
                return {
                    "type": "last",
                    "found": False,
                    "category": category,
                    "message": f"还没有{category}相关的记录"
                }
            entry = category_entries[0]
        else:
            entry = entries[0]

        return {
            "type": "last",
            "found": True,
            "entry": entry,
            "category": entry["category"],
            "date": entry["date"],  # Fixed: was entry_date, now date
            "details": self._format_entry_details(entry)
        }

    def _query_summary(
        self,
        entities: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Query summary statistics.

        Args:
            entities: Extracted entities
            context: Optional context (reserved for future use)

        Returns:
            Summary statistics
        """
        # Context parameter reserved for future personalization features
        _ = context  # Explicitly mark as unused
        timeframe = entities.get("timeframe", "week")
        start_date, end_date = self._parse_timeframe(timeframe)

        # Get all entries in range
        entries = self.repository.get_entries_by_date_range(start_date, end_date)

        # Calculate summary
        total = len(entries)

        if total == 0:
            return {
                "type": "summary",
                "timeframe": timeframe,
                "total": 0,
                "message": f"这{self._timeframe_to_chinese(timeframe)}还没有记录"
            }

        # Count by category
        category_counts = {}
        for entry in entries:
            cat = entry["category"]
            category_counts[cat] = category_counts.get(cat, 0) + 1

        # Count by mood
        mood_counts = {"positive": 0, "neutral": 0, "negative": 0}
        for entry in entries:
            mood = entry["mood"]
            mood_counts[mood] = mood_counts.get(mood, 0) + 1

        return {
            "type": "summary",
            "timeframe": timeframe,
            "total": total,
            "category_counts": category_counts,
            "mood_counts": mood_counts,
            "positive_rate": mood_counts["positive"] / total if total > 0 else 0
        }

    def _query_comparison(
        self,
        entities: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Query comparison between time periods.

        Args:
            entities: Extracted entities
            context: Optional context (reserved for future use)

        Returns:
            Comparison results
        """
        # Context parameter reserved for future personalization features
        _ = context  # Explicitly mark as unused
        category = entities.get("category")

        # This week
        this_week_start, this_week_end = self._parse_timeframe("week")
        this_week_entries = self.repository.get_entries_by_date_range(
            this_week_start, this_week_end
        )

        # Last week (convert string to date, subtract timedelta, convert back)
        from datetime import datetime
        start_date_obj = datetime.strptime(this_week_start, "%Y-%m-%d").date()
        end_date_obj = datetime.strptime(this_week_end, "%Y-%m-%d").date()

        last_week_start_obj = start_date_obj - timedelta(days=7)
        last_week_end_obj = end_date_obj - timedelta(days=7)

        last_week_start = last_week_start_obj.strftime("%Y-%m-%d")
        last_week_end = last_week_end_obj.strftime("%Y-%m-%d")

        last_week_entries = self.repository.get_entries_by_date_range(
            last_week_start, last_week_end
        )

        # Filter by category if specified
        if category:
            this_week_entries = [e for e in this_week_entries if e["category"] == category]
            last_week_entries = [e for e in last_week_entries if e["category"] == category]

        this_count = len(this_week_entries)
        last_count = len(last_week_entries)
        diff = this_count - last_count

        return {
            "type": "comparison",
            "category": category,
            "this_week": this_count,
            "last_week": last_count,
            "diff": diff,
            "trend": "up" if diff > 0 else "down" if diff < 0 else "stable"
        }

    def _generate_response(
        self,
        intent: str,
        result: Dict[str, Any],
        entities: Dict[str, Any]
    ) -> str:
        """
        Generate natural language response.

        Args:
            intent: Query intent
            result: Query results
            entities: Extracted entities

        Returns:
            Natural language response
        """
        if intent == self.INTENT_COUNT:
            return self._format_count_response(result, entities)
        elif intent == self.INTENT_LAST:
            return self._format_last_response(result)
        elif intent == self.INTENT_SUMMARY:
            return self._format_summary_response(result)
        elif intent == self.INTENT_COMPARISON:
            return self._format_comparison_response(result)
        else:
            return result.get("message", "我不太确定如何回答这个问题。可以换个方式问吗？")

    def _format_count_response(
        self,
        result: Dict[str, Any],
        entities: Dict[str, Any]
    ) -> str:
        """Format count query response.

        Note: entities parameter reserved for future customization
        """
        # Entities parameter reserved for future response customization
        _ = entities  # Explicitly mark as unused
        count = result["count"]
        category = result["category"] or "所有记录"
        timeframe = self._timeframe_to_chinese(result["timeframe"])
        metrics = result["metrics"]

        # Build metrics detail
        metrics_detail = ""
        if metrics.get("distance_km"):
            metrics_detail = f"，总计{metrics['distance_km']:.1f}公里"
        elif metrics.get("duration_hours"):
            metrics_detail = f"，总计{metrics['duration_hours']:.1f}小时"

        # Get template
        templates = self.response_templates["count"]
        template = templates.get(category, templates["default"])

        return template.format(
            timeframe=timeframe,
            category=category,
            count=count,
            metrics_detail=metrics_detail
        )

    def _format_last_response(self, result: Dict[str, Any]) -> str:
        """Format last query response."""
        if not result.get("found"):
            return result.get("message", "没有找到相关记录")

        category = result["category"]
        date = result["date"]
        details = result["details"]

        templates = self.response_templates["last"]
        template = templates.get(category, templates["default"])

        return template.format(
            category=category,
            date=date,
            details=details
        )

    def _format_summary_response(self, result: Dict[str, Any]) -> str:
        """Format summary query response."""
        if result["total"] == 0:
            return result["message"]

        timeframe = self._timeframe_to_chinese(result["timeframe"])
        total = result["total"]
        category_counts = result["category_counts"]
        positive_rate = result["positive_rate"]

        # Build summary
        parts = [f"这{timeframe}共记录{total}条"]

        # Add category breakdown
        if category_counts:
            category_str = "、".join([f"{cat}{count}次" for cat, count in category_counts.items()])
            parts.append(f"({category_str})")

        # Add mood info
        parts.append(f"，积极情绪占比{positive_rate:.0%}")

        return "".join(parts)

    def _format_comparison_response(self, result: Dict[str, Any]) -> str:
        """Format comparison query response."""
        category = result["category"] or "所有记录"
        this_week = result["this_week"]
        last_week = result["last_week"]
        diff = result["diff"]
        trend = result["trend"]

        if trend == "up":
            return f"这周{category}比上周多了{diff}次（{this_week}次 vs {last_week}次），继续保持！"
        elif trend == "down":
            return f"这周{category}比上周少了{abs(diff)}次（{this_week}次 vs {last_week}次），继续加油！"
        else:
            return f"这周{category}和上周一样，都是{this_week}次。"

    def _parse_timeframe(self, timeframe: str) -> tuple[str, str]:
        """
        Parse timeframe into start and end dates.

        Args:
            timeframe: Timeframe string (week, month, etc.)

        Returns:
            Tuple of (start_date, end_date) in YYYY-MM-DD format
        """
        today = datetime.now().date()

        if timeframe == "week":
            # Start of this week (Monday)
            start = today - timedelta(days=today.weekday())
            end = today
        elif timeframe == "month":
            # Start of this month
            start = today.replace(day=1)
            end = today
        else:
            # Default to last 7 days
            start = today - timedelta(days=7)
            end = today

        return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

    def _timeframe_to_chinese(self, timeframe: str) -> str:
        """Convert timeframe to Chinese."""
        mapping = {
            "week": "周",
            "month": "月",
            "day": "天"
        }
        return mapping.get(timeframe, "段时间")

    def _summarize_metrics(self, entries: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Summarize metrics from entries.

        Args:
            entries: List of entry dictionaries

        Returns:
            Dictionary of metric sums
        """
        summary = {}

        for entry in entries:
            metrics = entry.get("metrics", {})
            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    summary[key] = summary.get(key, 0) + value

        return summary

    def _format_entry_details(self, entry: Dict[str, Any]) -> str:
        """
        Format entry details for display.

        Args:
            entry: Entry dictionary

        Returns:
            Formatted details string
        """
        parts = []

        metrics = entry.get("metrics", {})
        if metrics:
            for key, value in metrics.items():
                name = key.replace("_", " ")
                parts.append(f"{name}: {value}")

        mood = entry.get("mood")
        mood_map = {"positive": "😊", "neutral": "😐", "negative": "😔"}
        if mood:
            parts.append(f"心情{mood_map.get(mood, mood)}")

        return "，".join(parts) if parts else "无详细信息"


# Convenience functions
def query_habits(query: str, db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Quick function to query habits.

    Args:
        query: Natural language query
        db_path: Optional database path

    Returns:
        Query result dictionary
    """
    repository = HabitRepository(db_path) if db_path else HabitRepository()
    agent = QueryAgent(repository=repository)
    return agent.execute(query=query)


if __name__ == "__main__":
    # Test: Query agent functionality
    print("Testing QueryAgent...")
    print("=" * 60)

    from ..database.schema import init_database

    # Initialize database
    init_database()

    # Create agent
    agent = QueryAgent()

    # Test queries
    test_queries = [
        "我这周运动了几次？",
        "上次学习是什么时候？",
        "这周的习惯怎么样？",
        "这周比上周运动怎么样？"
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 60)

        result = agent.execute(query=query)

        if result["success"]:
            print(f"Intent: {result['intent']}")
            print(f"Response: {result['response']}")
        else:
            print(f"Error: {result['error']}")

    # Test statistics
    print("\n" + "=" * 60)
    print("Agent Statistics:")
    print(agent.get_stats())
