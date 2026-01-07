"""
Report generation module for Trackit.

This module provides intelligent report generation capabilities:
- Weekly reports with LLM-powered insights
- Personalized recommendations based on patterns
- Trend analysis and visualizations
- Exportable reports in multiple formats

Author: Trackit Development
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json

from ..database.repository import HabitRepository
from .time_series import TimeSeriesAnalyzer
from .patterns import PatternDetector
from .visualizer import HabitVisualizer
from ..llm.client import LLMClient
from ..config.prompts import Prompts
from ..config.settings import settings


class ReportGenerator:
    """
    Generate comprehensive reports with AI-powered insights.

    Features:
    - Weekly/Monthly reports
    - LLM-generated personalized recommendations
    - Trend analysis with visualizations
    - Pattern detection and insights
    - Export to multiple formats

    Example:
        >>> generator = ReportGenerator()
        >>> report = generator.generate_weekly_report()
        >>> print(report['text'])
        >>> generator.save_report(report, 'weekly_report.md')
    """

    def __init__(
        self,
        repository: Optional[HabitRepository] = None,
        analyzer: Optional[TimeSeriesAnalyzer] = None,
        detector: Optional[PatternDetector] = None,
        visualizer: Optional[HabitVisualizer] = None
    ):
        """
        Initialize the report generator.

        Args:
            repository: HabitRepository instance
            analyzer: TimeSeriesAnalyzer instance
            detector: PatternDetector instance
            visualizer: HabitVisualizer instance
        """
        self.repository = repository or HabitRepository()
        self.analyzer = analyzer or TimeSeriesAnalyzer(self.repository)
        self.detector = detector or PatternDetector(self.repository, self.analyzer)
        self.visualizer = visualizer or HabitVisualizer(self.repository, self.analyzer)

        # Initialize LLM client (optional, for AI-powered insights)
        self.llm_client = None
        try:
            self.llm_client = LLMClient()
        except Exception as e:
            print(f"Warning: LLM client not available: {e}")
            print("Reports will use template-based insights instead.")

    def generate_weekly_report(self, weeks: int = 1) -> Dict[str, Any]:
        """
        Generate a comprehensive weekly report.

        Args:
            weeks: Number of weeks to include in the report (currently uses current week for stats)

        Returns:
            Dictionary containing:
                - text: Markdown-formatted report text
                - data: Raw analysis data
                - chart: Base64-encoded chart image (optional)
                - metadata: Report metadata
        """
        # Gather data - weekly_statistics uses current week, other methods use weeks param
        from datetime import datetime
        current_week = datetime.now().strftime('%Y-W%W')
        weekly_stats = self.analyzer.weekly_statistics(week_iso=current_week)
        patterns = self.detector.detect_day_of_week_patterns(weeks=weeks)
        streaks = self.detector.detect_streaks(days=weeks*7)
        trends = self.analyzer.trend_analysis(window=7, weeks=weeks)
        insights = self.detector.get_insights(weeks=weeks)

        # Generate visualization
        chart_base64 = None
        try:
            fig = self.visualizer.plot_weekly_summary()
            if fig:
                import io
                import base64
                buf = io.BytesIO()
                fig.savefig(buf, format='png', bbox_inches='tight', dpi=100)
                buf.seek(0)
                chart_base64 = base64.b64encode(buf.read()).decode('utf-8')
        except Exception as e:
            print(f"Warning: Could not generate chart: {e}")

        # Build report sections
        report_text = self._build_markdown_report(
            weekly_stats, patterns, streaks, trends, insights, weeks
        )

        # Generate AI-powered insights if LLM is available
        ai_insights = None
        if self.llm_client and weeks >= 1:
            try:
                ai_insights = self._generate_ai_insights(
                    weekly_stats, patterns, trends, insights
                )
            except Exception as e:
                print(f"Warning: Could not generate AI insights: {e}")

        return {
            'text': report_text,
            'ai_insights': ai_insights,
            'data': {
                'weekly_stats': weekly_stats,
                'patterns': patterns,
                'streaks': streaks,
                'trends': trends,
                'insights': insights
            },
            'chart': chart_base64,
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'period_weeks': weeks,
                'total_entries': weekly_stats.get('total_entries', 0),
                'has_ai_insights': ai_insights is not None
            }
        }

    def _build_markdown_report(
        self,
        weekly_stats: Dict,
        patterns: Dict,
        streaks: Dict,
        trends: Dict,
        insights: Dict,
        weeks: int
    ) -> str:
        """
        Build a markdown-formatted report.

        Args:
            weekly_stats: Weekly statistics (single week dict, not list)
            patterns: Pattern detection results
            streaks: Streak information
            trends: Trend analysis
            insights: Insights and recommendations
            weeks: Number of weeks covered

        Returns:
            Markdown-formatted report string
        """
        lines = []

        # Header
        lines.append(f"# 📊 习惯追踪周报")
        lines.append(f"**周期**: {weeks}周")
        lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("")

        # Summary section
        lines.append("## 📈 本周概览")
        total_entries = weekly_stats.get('total_entries', 0)
        lines.append(f"总记录数: **{total_entries}** 条")
        lines.append("")

        if weekly_stats.get('total_entries', 0) > 0:
            latest_week = weekly_stats
            if latest_week.get('by_category'):
                lines.append("### 类别分布")
                for category, count in sorted(latest_week['by_category'].items(), key=lambda x: x[1], reverse=True):
                    lines.append(f"- **{category}**: {count} 次")
                lines.append("")

            if latest_week.get('mood_distribution'):
                lines.append("### 情绪分布")
                mood_names = {'positive': '😊 积极', 'neutral': '😐 中性', 'negative': '😟 消极'}
                for mood, count in latest_week['mood_distribution'].items():
                    mood_cn = mood_names.get(mood, mood)
                    lines.append(f"- **{mood_cn}**: {count} 次")
                lines.append("")

        # Patterns section
        lines.append("## 🔍 发现的规律")
        if patterns.get('patterns'):
            for i, pattern in enumerate(patterns['patterns'][:5], 1):
                lines.append(f"{i}. {pattern}")
        else:
            lines.append("数据还不够多，继续记录来发现更多规律吧！")
        lines.append("")

        # Streaks section
        lines.append("## 🔥 连续记录")
        if streaks.get('current_streak', 0) > 0:
            lines.append(f"- 当前连续: **{streaks['current_streak']}** 天")
            if streaks.get('longest_streak', 0) > 0:
                lines.append(f"- 最长连续: **{streaks['longest_streak']}** 天")
        else:
            lines.append("还没有连续记录，开始养成记录习惯吧！")
        lines.append("")

        # Trends section
        lines.append("## 📊 趋势分析")
        if trends.get('trend_direction') and trends['trend_direction'] != 'insufficient_data':
            direction_map = {
                'increasing': '上升 📈',
                'decreasing': '下降 📉',
                'stable': '稳定 ➡️'
            }
            direction = direction_map.get(trends['trend_direction'], trends['trend_direction'])
            lines.append(f"- 趋势: {direction}")

            if trends.get('trend_strength'):
                strength = trends['trend_strength']
                if strength > 0.7:
                    strength_desc = "强"
                elif strength > 0.3:
                    strength_desc = "中等"
                else:
                    strength_desc = "弱"
                lines.append(f"- 趋势强度: {strength_desc} ({strength:.2f})")

            if trends.get('summary'):
                summary = trends['summary']
                lines.append(f"- 平均值: {summary.get('mean_value', 0):.2f}")
                lines.append(f"- 最大值: {summary.get('max_value', 0):.2f}")
                lines.append(f"- 最小值: {summary.get('min_value', 0):.2f}")
        else:
            lines.append("数据不足，无法分析趋势")
        lines.append("")

        # Recommendations section
        lines.append("## 💡 建议")
        if insights.get('recommendations'):
            for i, rec in enumerate(insights['recommendations'][:5], 1):
                lines.append(f"{i}. {rec}")
        else:
            lines.append("继续保持，记录更多的数据来获取个性化建议！")
        lines.append("")

        # Footer
        lines.append("---")
        lines.append("*由 Trackit 自动生成*")

        return "\n".join(lines)

    def _generate_ai_insights(
        self,
        weekly_stats: Dict,
        patterns: Dict,
        trends: Dict,
        insights: Dict
    ) -> str:
        """
        Generate AI-powered insights using LLM.

        Args:
            weekly_stats: Weekly statistics (single week dict, not list)
            patterns: Pattern detection results
            trends: Trend analysis
            insights: Basic insights

        Returns:
            AI-generated insights text
        """
        # Prepare data summary for the prompt
        data_summary = {
            'total_entries': weekly_stats.get('total_entries', 0),
            'patterns': patterns.get('patterns', [])[:3],
            'trend_direction': trends.get('trend_direction'),
            'trend_strength': trends.get('trend_strength'),
            'current_streak': insights.get('streaks', {}).get('current_streak', 0),
            'recommendations': insights.get('recommendations', [])[:3]
        }

        # Build prompt
        prompt = f"""基于以下习惯追踪数据，生成2-3条深度洞察和个性化建议：

数据摘要：
{json.dumps(data_summary, ensure_ascii=False, indent=2)}

请生成：
1. **深度洞察** (100-150字)
   - 发现非显而易见的模式
   - 连接不同数据点
   - 提供新视角

2. **个性化建议** (2-3条)
   - 具体可执行
   - 基于数据证据
   - 正向激励

格式要求：
- 使用友好的中文
- 用Markdown格式
- 每条建议单独成行
- 总长度200-300字

现在生成：
"""

        try:
            response = self.llm_client.call_with_retry(
                messages=[{"role": "user", "content": prompt}],
                model=settings.MODEL_REPORT
            )
            return response.get('content', '').strip()
        except Exception as e:
            print(f"Error generating AI insights: {e}")
            return None

    def save_report(self, report: Dict[str, Any], filename: str, format: str = 'md'):
        """
        Save report to file.

        Args:
            report: Report dictionary from generate_weekly_report()
            filename: Output filename (without extension)
            format: Output format ('md', 'html', 'json')

        Returns:
            Number of bytes written
        """
        if format == 'md':
            output_filename = f"{filename}.md"
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write(report['text'])

        elif format == 'json':
            output_filename = f"{filename}.json"
            with open(output_filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

        elif format == 'html':
            # Simple HTML wrapper
            import markdown
            output_filename = f"{filename}.html"
            md_text = report['text']
            html_content = markdown.markdown(md_text)

            html_template = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>习惯追踪报告</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; line-height: 1.6; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        h3 {{ color: #7f8c8d; }}
        .emoji {{ font-size: 1.2em; }}
    </style>
</head>
<body>
{html_content}
</body>
</html>
"""
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write(html_template)

        else:
            raise ValueError(f"Unsupported format: {format}")

        return output_filename


if __name__ == "__main__":
    # Test the report generator
    print("Report Generator Test")
    print("=" * 60)

    generator = ReportGenerator()

    # Generate weekly report
    print("\nGenerating weekly report...")
    report = generator.generate_weekly_report(weeks=2)

    print(f"✓ Report generated!")
    print(f"  - Total entries: {report['metadata']['total_entries']}")
    print(f"  - Has AI insights: {report['metadata']['has_ai_insights']}")
    print(f"  - Has chart: {report['chart'] is not None}")

    # Display first few lines
    print("\nReport preview (first 500 chars):")
    print("-" * 60)
    print(report['text'][:500] + "...")

    # Save report
    print("\n\nSaving report...")
    md_file = generator.save_report(report, 'test_report', format='md')
    print(f"✓ Saved to: {md_file}")

    print("\n✓ All tests completed!")
