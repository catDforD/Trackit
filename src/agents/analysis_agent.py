"""
Analysis agent for Trackit.

This agent provides comprehensive analysis capabilities including:
- Advanced queries with complex filters
- Pattern detection and insights
- Trend analysis
- Report generation

This integrates the analysis modules to provide intelligent
responses to user questions about their habits.

Author: Trackit Development
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from .base_agent import BaseAgent
from ..database.repository import HabitRepository
from ..llm.extractors import IntentClassifier
from ..analysis.time_series import TimeSeriesAnalyzer
from ..analysis.patterns import PatternDetector
from ..analysis.visualizer import HabitVisualizer
from ..analysis.exporter import DataExporter


class AnalysisAgentError(Exception):
    """Base exception for AnalysisAgent errors."""
    pass


class AnalysisAgent(BaseAgent):
    """
    Agent for advanced analysis of habit tracking data.

    This agent combines multiple analysis modules to provide
    comprehensive insights and answers to complex queries.

    Supported query types:
    - PATTERN: "有什么规律吗？" "我的习惯有什么模式？"
    - TREND: "最近趋势怎么样？" "这周和上周对比？"
    - INSIGHTS: "给我一些分析和建议" "帮我分析一下"
    - EXPORT: "导出数据" "保存成CSV"
    - CUSTOM: Custom date range queries

    Example:
        >>> agent = AnalysisAgent()
        >>> result = agent.execute("给我分析一下这周的习惯")
        >>> print(result["response"])
    """

    # Query types
    QUERY_PATTERN = "PATTERN"
    QUERY_TREND = "TREND"
    QUERY_INSIGHTS = "INSIGHTS"
    QUERY_EXPORT = "EXPORT"
    QUERY_CUSTOM = "CUSTOM"

    def __init__(
        self,
        repository: Optional[HabitRepository] = None,
        analyzer: Optional[TimeSeriesAnalyzer] = None,
        detector: Optional[PatternDetector] = None,
        visualizer: Optional[HabitVisualizer] = None,
        exporter: Optional[DataExporter] = None
    ):
        """
        Initialize the analysis agent.

        Args:
            repository: HabitRepository instance
            analyzer: TimeSeriesAnalyzer instance
            detector: PatternDetector instance
            visualizer: HabitVisualizer instance
            exporter: DataExporter instance
        """
        super().__init__(
            name="AnalysisAgent",
            config={"description": "Advanced analysis agent for habit data"}
        )

        self.repository = repository or HabitRepository()
        self.analyzer = analyzer or TimeSeriesAnalyzer(self.repository)
        self.detector = detector or PatternDetector(self.repository, self.analyzer)
        self.visualizer = visualizer or HabitVisualizer(self.repository, self.analyzer)
        self.exporter = exporter or DataExporter(self.repository)

        # Initialize intent classifier
        self.intent_classifier = IntentClassifier()

    def _classify_query(self, query: str) -> tuple[str, Dict[str, Any]]:
        """
        Classify the query type and extract entities.

        Args:
            query: User query string

        Returns:
            Tuple of (query_type, entities)
        """
        query_lower = query.lower()

        # Pattern detection queries
        if any(word in query for word in ['规律', '模式', 'pattern', '习惯', '特点']):
            return self.QUERY_PATTERN, {}

        # Trend queries
        if any(word in query for word in ['趋势', '变化', 'trend', '对比', 'compare']):
            return self.QUERY_TREND, {}

        # Insights/summary queries
        if any(word in query for word in ['分析', '建议', 'insight', '总结', '怎么样']):
            return self.QUERY_INSIGHTS, {}

        # Export queries
        if any(word in query for word in ['导出', 'export', '保存', 'csv', 'json']):
            return self.QUERY_EXPORT, {}

        # Default to custom query
        return self.QUERY_CUSTOM, {}

    def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Execute an analysis query.

        Args:
            query: User's query string
            **kwargs: Additional parameters (start_date, end_date, category, etc.)

        Returns:
            Dictionary containing:
                - success: Boolean indicating success
                - response: Natural language response
                - data: Optional analysis data
                - chart: Optional base64-encoded chart
                - error: Optional error message
        """
        try:
            # Classify query
            query_type, entities = self._classify_query(query)

            # Route to appropriate handler
            if query_type == self.QUERY_PATTERN:
                return self._handle_pattern_query(query, **kwargs)
            elif query_type == self.QUERY_TREND:
                return self._handle_trend_query(query, **kwargs)
            elif query_type == self.QUERY_INSIGHTS:
                return self._handle_insights_query(query, **kwargs)
            elif query_type == self.QUERY_EXPORT:
                return self._handle_export_query(query, **kwargs)
            else:
                return self._handle_custom_query(query, **kwargs)

        except Exception as e:
            self.execution_count += 1
            self.state["execution_count"] = self.execution_count
            return {
                "success": False,
                "response": "抱歉，分析时出错了",
                "error": str(e)
            }

    def _handle_pattern_query(self, query: str, **kwargs) -> Dict[str, Any]:
        """Handle pattern detection queries."""
        weeks = kwargs.get('weeks', 4)
        category = kwargs.get('category')

        # Detect patterns
        patterns = self.detector.detect_day_of_week_patterns(
            weeks=weeks,
            category=category
        )

        streaks = self.detector.detect_streaks(
            category=category,
            days=weeks * 7
        )

        # Generate response
        response_parts = []

        if patterns['patterns']:
            response_parts.append("🔍 **发现的规律：**")
            for pattern in patterns['patterns'][:3]:
                response_parts.append(f"  • {pattern}")

        if streaks['current_streak'] > 0:
            response_parts.append(f"\n🔥 **连续记录**: {streaks['current_streak']}天")
            if streaks['longest_streak'] > 0:
                response_parts.append(f"   最长记录: {streaks['longest_streak']}天")

        if not response_parts:
            response_parts.append("数据还不够多，继续记录来发现更多规律吧！")

        return {
            "success": True,
            "response": "\n".join(response_parts),
            "data": {
                "patterns": patterns,
                "streaks": streaks
            }
        }

    def _handle_trend_query(self, query: str, **kwargs) -> Dict[str, Any]:
        """Handle trend analysis queries."""
        weeks = kwargs.get('weeks', 4)
        category = kwargs.get('category')
        metric = kwargs.get('metric')

        # Get trend analysis
        trend = self.analyzer.trend_analysis(
            category=category,
            metric=metric,
            window=7,
            weeks=weeks
        )

        # Generate response
        direction_map = {
            'increasing': '上升 📈',
            'decreasing': '下降 📉',
            'stable': '稳定 ➡️',
            'insufficient_data': '数据不足'
        }

        direction = trend['trend_direction']
        direction_cn = direction_map.get(direction, direction)

        response_parts = [
            f"**趋势分析** (最近{weeks}周)",
            f"",
            f"📊 趋势: {direction_cn}",
        ]

        if direction != 'insufficient_data':
            strength = trend['trend_strength']
            if strength > 0.7:
                response_parts.append(f"   趋势强度: 强 ({strength:.2f})")
            elif strength > 0.3:
                response_parts.append(f"   趋势强度: 中等 ({strength:.2f})")
            else:
                response_parts.append(f"   趋势强度: 弱 ({strength:.2f})")

            summary = trend['summary']
            response_parts.append(f"📈 平均值: {summary['mean_value']:.2f} | 📊 最大值: {summary['max_value']:.2f} | 📊 最小值: {summary['min_value']:.2f}")

        return {
            "success": True,
            "response": "\n".join(response_parts),
            "data": trend
        }

    def _handle_insights_query(self, query: str, **kwargs) -> Dict[str, Any]:
        """Handle comprehensive insights queries."""
        weeks = kwargs.get('weeks', 2)

        # Get comprehensive insights
        insights = self.detector.get_insights(weeks=weeks)

        # Generate response
        response_parts = [
            f"📊 **{weeks}周习惯分析**",
            f"📝 {insights['summary']}"
        ]

        if insights['recommendations']:
            response_parts.append(f"💡 **建议：**")
            for i, rec in enumerate(insights['recommendations'][:3], 1):
                response_parts.append(f"  {i}. {rec}")

        return {
            "success": True,
            "response": "\n".join(response_parts),
            "data": insights
        }

    def _handle_export_query(self, query: str, **kwargs) -> Dict[str, Any]:
        """Handle data export queries."""
        # Determine export format from query
        query_lower = query.lower()
        if 'json' in query_lower:
            format_type = 'json'
            default_filename = 'habits_export.json'
        else:
            format_type = 'csv'
            default_filename = 'habits_export.csv'

        filename = kwargs.get('filename', default_filename)
        start_date = kwargs.get('start_date')
        end_date = kwargs.get('end_date')
        category = kwargs.get('category')

        try:
            # Perform export
            if format_type == 'json':
                count = self.exporter.to_json(
                    filename,
                    start_date=start_date,
                    end_date=end_date,
                    category=category
                )
            else:
                count = self.exporter.to_csv(
                    filename,
                    start_date=start_date,
                    end_date=end_date,
                    category=category
                )

            response = f"✅ 成功导出 {count} 条记录到 {filename}"

            return {
                "success": True,
                "response": response,
                "data": {
                    "count": count,
                    "filename": filename,
                    "format": format_type
                }
            }

        except Exception as e:
            return {
                "success": False,
                "response": f"❌ 导出失败: {str(e)}",
                "error": str(e)
            }

    def _handle_custom_query(self, query: str, **kwargs) -> Dict[str, Any]:
        """Handle custom queries with date ranges and filters."""
        start_date = kwargs.get('start_date')
        end_date = kwargs.get('end_date')
        category = kwargs.get('category')

        if not (start_date or end_date or category):
            return {
                "success": False,
                "response": "请提供查询条件，比如日期范围或类别"
            }

        # Get statistics for custom range
        stats = self.repository.get_statistics(
            start_date=start_date,
            end_date=end_date,
            category=category
        )

        # Generate response
        response_parts = ["📊 **查询结果**"]

        if start_date or end_date:
            response_parts.append(f"时间范围: {start_date or '开始'} 至 {end_date or '现在'}")

        if category:
            response_parts.append(f"类别: {category}")

        response_parts.append(f"总记录数: {stats['total_entries']}")

        if stats['by_category']:
            response_parts.append(f"按类别统计:")
            for cat, count in stats['by_category'].items():
                response_parts.append(f"  • {cat}: {count}条")

        if stats['mood_distribution']:
            response_parts.append(f"情绪分布:")
            mood_names = {'positive': '积极', 'neutral': '中性', 'negative': '消极'}
            for mood, count in stats['mood_distribution'].items():
                mood_cn = mood_names.get(mood, mood)
                response_parts.append(f"  • {mood_cn}: {count}条")

        return {
            "success": True,
            "response": "\n".join(response_parts),
            "data": stats
        }

    def get_analysis_report(self, weeks: int = 2) -> Dict[str, Any]:
        """
        Generate a comprehensive analysis report.

        This includes:
        - Weekly statistics
        - Pattern detection
        - Trend analysis
        - Insights and recommendations

        Args:
            weeks: Number of weeks to analyze

        Returns:
            Complete analysis report
        """
        # Gather all analysis data
        weekly_stats = self.analyzer.weekly_statistics()
        patterns = self.detector.detect_day_of_week_patterns(weeks=weeks)
        streaks = self.detector.detect_streaks(days=weeks*7)
        trends = self.analyzer.trend_analysis(window=7, weeks=weeks)
        insights = self.detector.get_insights(weeks=weeks)

        return {
            "generated_at": datetime.now().isoformat(),
            "period_weeks": weeks,
            "weekly_statistics": weekly_stats,
            "patterns": patterns,
            "streaks": streaks,
            "trends": trends,
            "insights": insights
        }


if __name__ == "__main__":
    # Test the analysis agent
    print("Analysis Agent Test")
    print("=" * 50)

    agent = AnalysisAgent()

    # Test pattern query
    print("\n1. Testing pattern query...")
    result = agent.execute("有什么规律吗？")
    print(f"   Success: {result['success']}")
    print(f"   Response: {result['response'][:100]}...")

    # Test trend query
    print("\n2. Testing trend query...")
    result = agent.execute("最近趋势怎么样？")
    print(f"   Success: {result['success']}")
    print(f"   Response: {result['response'][:100]}...")

    # Test insights query
    print("\n3. Testing insights query...")
    result = agent.execute("给我一些分析和建议")
    print(f"   Success: {result['success']}")
    print(f"   Response: {result['response'][:100]}...")

    # Test comprehensive report
    print("\n4. Testing comprehensive report...")
    report = agent.get_analysis_report(weeks=2)
    print(f"   Report sections: {len(report)}")
    print(f"   Generated at: {report['generated_at']}")

    print("\n✓ All tests completed!")
