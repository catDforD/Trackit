"""
Gradio web interface for Trackit.

This module provides a user-friendly web interface with:
- Chat interface for natural language interaction
- Dashboard with visualizations and statistics
- Report generation and export
- Real-time habit tracking and analysis
- Quick action buttons for common operations
- Enhanced user experience with loading states and error handling

Author: Trackit Development
"""

import gradio as gr
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
import io
import base64

from .agents.recording_agent import RecordingAgent
from .agents.query_agent import QueryAgent
from .agents.analysis_agent import AnalysisAgent
from .analysis.report_generator import ReportGenerator
from .analysis.visualizer import HabitVisualizer
from .database.repository import HabitRepository


# Custom CSS for enhanced styling
CUSTOM_CSS = """
/* Global styles */
.gradio-container {
    max-width: 1400px !important;
    margin: auto !important;
}

/* Tab styling */
.tabs {
    border-radius: 12px !important;
}

/* Button hover effects */
button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    transition: all 0.2s ease;
}

/* Quick action buttons */
.quick-action-btn {
    min-height: 60px !important;
    font-size: 14px !important;
    border-radius: 8px !important;
    transition: all 0.2s ease;
}

.quick-action-btn:hover {
    transform: scale(1.02);
}

/* Chat message styling */
.message {
    padding: 12px 16px !important;
    border-radius: 12px !important;
    margin-bottom: 8px !important;
}

/* Stats card styling */
.stats-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 12px;
    padding: 20px;
    color: white;
}

/* Responsive design */
@media (max-width: 768px) {
    .gradio-container {
        padding: 10px !important;
    }

    .quick-action-btn {
        min-height: 50px !important;
        font-size: 13px !important;
    }
}

/* Loading animation */
.loading-spinner {
    border: 3px solid #f3f3f3;
    border-top: 3px solid #3498db;
    border-radius: 50%;
    width: 40px;
    height: 40px;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

/* Status messages */
.status-success {
    background-color: #d4edda !important;
    border-color: #c3e6cb !important;
    color: #155724 !important;
}

.status-error {
    background-color: #f8d7da !important;
    border-color: #f5c6cb !important;
    color: #721c24 !important;
}

.status-info {
    background-color: #d1ecf1 !important;
    border-color: #bee5eb !important;
    color: #0c5460 !important;
}
"""


class TrackitApp:
    """
    Gradio web application for Trackit habit tracker.

    Features:
    - Chat interface for recording and querying habits
    - Dashboard with statistics and charts
    - Report generation with AI insights
    - Data export functionality

    Example:
        >>> app = TrackitApp()
        >>> app.launch()
    """

    def __init__(self):
        """Initialize the Trackit application."""
        print("Initializing Trackit...")

        # Initialize agents
        self.recording_agent = RecordingAgent()
        self.query_agent = QueryAgent()
        self.analysis_agent = AnalysisAgent()
        self.report_generator = ReportGenerator()

        # Initialize visualizer and repository for dashboard
        self.repository = HabitRepository()
        self.visualizer = HabitVisualizer(self.repository)

        # Chat history
        self.chat_history: List[Tuple[str, str]] = []

        print("✓ Trackit initialized successfully!")

    def chat(self, message: str, history: List[Dict]) -> Tuple[str, List[Dict], str]:
        """
        Handle chat interactions with enhanced error handling and status feedback.

        Args:
            message: User message
            history: Chat history (list of message dicts with 'role' and 'content')

        Returns:
            Tuple of (empty string, updated history, status message)
        """
        if not message or not message.strip():
            return "", history, "请输入消息"

        status_msg = "⏳ 处理中..."

        try:
            # Try recording first
            result = self.recording_agent.execute(message)

            # If recording failed, try query
            if not result.get("success"):
                result = self.query_agent.execute(message)

            # If query failed, try analysis
            if not result.get("success"):
                result = self.analysis_agent.execute(message)

            # Extract response
            if result.get("success"):
                response = result.get("feedback") or result.get("response", "操作成功")
                status_msg = "✅ 操作成功"
            else:
                response = result.get("error", "抱歉，我没有理解。请换个说法试试。")
                status_msg = "⚠️ 未完全理解"

            # Update history with Gradio v4+ format
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": response})

            return "", history, status_msg

        except Exception as e:
            error_msg = f"❌ 发生错误: {str(e)}"
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": error_msg})
            return "", history, "❌ 处理失败"

    def quick_action(self, action_type: str, history: List[Dict]) -> Tuple[str, List[Dict], str]:
        """
        Handle quick action button clicks.

        Args:
            action_type: Type of quick action
            history: Chat history

        Returns:
            Tuple of (empty string, updated history, status message)
        """
        # Quick action templates
        quick_actions = {
            "record_exercise": "今天运动了30分钟",
            "record_reading": "今天阅读了1小时",
            "record_meditation": "今天冥想了15分钟",
            "record_water": "今天喝了8杯水",
            "query_today": "我今天记录了什么？",
            "query_week": "我这周运动了几次？",
            "query_patterns": "有什么规律吗？",
            "query_trends": "最近趋势怎么样？",
            "analyze_all": "给我一些分析和建议",
            "clear_today": "删除今天的记录",
        }

        message = quick_actions.get(action_type, "")
        if message:
            return self.chat(message, history)
        return "", history, "❓ 未知操作"

    def get_dashboard_data(self) -> Tuple[Dict, str, Optional[str]]:
        """
        Get data for the dashboard.

        Returns:
            Tuple of (statistics dict, stats text, chart image path)
        """
        try:
            # Get statistics
            stats = self.repository.get_statistics()

            # Get all entries for "recent 7 days" calculation (using existing method)
            all_entries = self.repository.get_all_entries()
            recent_entries = [e for e in all_entries if self._is_within_days(e, 7)]

            # Build summary
            summary = {
                "总记录数": stats.get("total_entries", 0),
                "最近7天": len(recent_entries),
                "类别数": len(stats.get("by_category", {})),
                "连续记录": self._get_current_streak()
            }

            # Generate chart
            chart_path = None
            try:
                fig = self.visualizer.plot_weekly_summary()
                if fig:
                    chart_path = "/tmp/weekly_summary.png"
                    fig.savefig(chart_path, bbox_inches='tight', dpi=100)
            except Exception as e:
                print(f"Warning: Could not generate chart: {e}")

            # Format stats for display
            stats_text = self._format_stats(stats)

            return summary, stats_text, chart_path

        except Exception as e:
            error_msg = f"获取数据失败: {str(e)}"
            return {}, error_msg, None

    def _is_within_days(self, entry: Dict, days: int) -> bool:
        """Check if entry is within specified days."""
        # Database uses 'date' field
        date_key = entry.get("entry_date") or entry.get("date")
        if not date_key:
            return False
        entry_date = datetime.strptime(date_key, "%Y-%m-%d").date()
        return (datetime.now().date() - entry_date).days <= days

    def _get_current_streak(self) -> int:
        """Get current recording streak."""
        try:
            from .analysis.patterns import PatternDetector
            from .analysis.time_series import TimeSeriesAnalyzer

            analyzer = TimeSeriesAnalyzer(self.repository)
            detector = PatternDetector(self.repository, analyzer)
            streaks = detector.detect_streaks(days=30)
            return streaks.get("current_streak", 0)
        except:
            return 0

    def _format_stats(self, stats: Dict) -> str:
        """Format statistics for display."""
        lines = ["## 📊 数据统计"]

        if stats.get("total_entries", 0) == 0:
            lines.append("还没有记录，开始记录你的第一个习惯吧！")
            return "\n".join(lines)

        # Category breakdown
        if stats.get("by_category"):
            lines.append("\n### 按类别统计")
            for category, count in sorted(stats["by_category"].items(), key=lambda x: x[1], reverse=True):
                lines.append(f"- **{category}**: {count} 次")

        # Mood distribution
        if stats.get("mood_distribution"):
            lines.append("\n### 情绪分布")
            mood_names = {'positive': '😊 积极', 'neutral': '😐 中性', 'negative': '😟 消极'}
            for mood, count in stats["mood_distribution"].items():
                mood_cn = mood_names.get(mood, mood)
                lines.append(f"- **{mood_cn}**: {count} 次")

        return "\n".join(lines)

    def generate_report(self, weeks: int = 2) -> Tuple[str, Optional[str]]:
        """
        Generate a weekly report.

        Args:
            weeks: Number of weeks to include

        Returns:
            Tuple of (report text, chart path)
        """
        try:
            report = self.report_generator.generate_weekly_report(weeks=weeks)

            # Extract AI insights if available
            text = report['text']
            if report.get('ai_insights'):
                text += "\n\n## 🤖 AI 深度洞察\n\n" + report['ai_insights']

            # Save chart
            chart_path = None
            if report.get('chart'):
                try:
                    import tempfile
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                        import base64
                        img_data = base64.b64decode(report['chart'])
                        f.write(img_data)
                        chart_path = f.name
                except Exception as e:
                    print(f"Warning: Could not save chart: {e}")

            return text, chart_path

        except Exception as e:
            error_msg = f"生成报告失败: {str(e)}"
            return error_msg, None

    def export_data(self, format_type: str) -> str:
        """
        Export habit data.

        Args:
            format_type: "csv" or "json"

        Returns:
            File path or error message
        """
        try:
            from .analysis.exporter import DataExporter

            exporter = DataExporter(self.repository)

            if format_type == "csv":
                filename = f"/tmp/habits_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                count = exporter.to_csv(filename)
            else:
                filename = f"/tmp/habits_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                count = exporter.to_json(filename)

            return f"✅ 成功导出 {count} 条记录到 {filename}"

        except Exception as e:
            return f"❌ 导出失败: {str(e)}"

    def create_interface(self):
        """
        Create the enhanced Gradio interface with quick actions and improved UX.

        Returns:
            gr.Blocks: The Gradio interface
        """
        with gr.Blocks(title="Trackit - 习惯追踪助手") as app:
            # Header
            gr.Markdown(
                """
                # 🎯 Trackit - 习惯追踪与复盘助手
                ### 通过自然语言记录习惯，获取智能分析和个性化建议
                """
            )

            with gr.Tabs():
                # Tab 1: Chat Interface
                with gr.Tab("💬 对话记录"):
                    gr.Markdown("### 记录习惯或查询数据")

                    # Quick action buttons for recording
                    gr.Markdown("#### 📝 快速记录")
                    with gr.Row():
                        record_exercise_btn = gr.Button(
                            "🏃 运动30分钟",
                            elem_classes=["quick-action-btn"]
                        )
                        record_reading_btn = gr.Button(
                            "📚 阅读1小时",
                            elem_classes=["quick-action-btn"]
                        )
                        record_meditation_btn = gr.Button(
                            "🧘 冥想15分钟",
                            elem_classes=["quick-action-btn"]
                        )
                        record_water_btn = gr.Button(
                            "💧 喝8杯水",
                            elem_classes=["quick-action-btn"]
                        )

                    # Quick action buttons for querying
                    gr.Markdown("#### 🔍 快速查询")
                    with gr.Row():
                        query_today_btn = gr.Button(
                            "📅 今天记录",
                            elem_classes=["quick-action-btn"]
                        )
                        query_week_btn = gr.Button(
                            "📊 本周统计",
                            elem_classes=["quick-action-btn"]
                        )
                        query_patterns_btn = gr.Button(
                            "🔍 发现规律",
                            elem_classes=["quick-action-btn"]
                        )
                        query_trends_btn = gr.Button(
                            "📈 趋势分析",
                            elem_classes=["quick-action-btn"]
                        )

                    # Chat interface
                    gr.Markdown("#### 💬 自由对话")
                    gr.Markdown("试试说：\"今天跑了5公里\" 或 \"我这周运动了几次？\"")

                    chatbot = gr.Chatbot(
                        label="对话历史",
                        height=350
                    )
                    msg = gr.Textbox(
                        label="你的消息",
                        placeholder="输入消息，或点击上方快捷按钮...",
                        lines=2,
                        autofocus=True
                    )

                    with gr.Row():
                        submit_btn = gr.Button("发送 📤", variant="primary", scale=2)
                        clear_btn = gr.Button("清空对话 🗑️", variant="stop", scale=1)

                    # Status indicator
                    status_output = gr.Textbox(
                        label="状态",
                        interactive=False,
                        scale=1
                    )

                    # Example messages
                    gr.Examples(
                        examples=[
                            ["今天跑了5公里，感觉不错"],
                            ["我这周运动了几次？"],
                            ["有什么规律吗？"],
                            ["最近趋势怎么样？"],
                            ["给我一些分析和建议"],
                            ["导出数据"]
                        ],
                        inputs=msg,
                        label="示例输入"
                    )

                    # Event handlers
                    submit_btn.click(
                        self.chat,
                        inputs=[msg, chatbot],
                        outputs=[msg, chatbot, status_output]
                    )
                    msg.submit(
                        self.chat,
                        inputs=[msg, chatbot],
                        outputs=[msg, chatbot, status_output]
                    )

                    # Quick action handlers
                    record_exercise_btn.click(
                        lambda h: self.quick_action("record_exercise", h),
                        inputs=[chatbot],
                        outputs=[msg, chatbot, status_output]
                    )
                    record_reading_btn.click(
                        lambda h: self.quick_action("record_reading", h),
                        inputs=[chatbot],
                        outputs=[msg, chatbot, status_output]
                    )
                    record_meditation_btn.click(
                        lambda h: self.quick_action("record_meditation", h),
                        inputs=[chatbot],
                        outputs=[msg, chatbot, status_output]
                    )
                    record_water_btn.click(
                        lambda h: self.quick_action("record_water", h),
                        inputs=[chatbot],
                        outputs=[msg, chatbot, status_output]
                    )
                    query_today_btn.click(
                        lambda h: self.quick_action("query_today", h),
                        inputs=[chatbot],
                        outputs=[msg, chatbot, status_output]
                    )
                    query_week_btn.click(
                        lambda h: self.quick_action("query_week", h),
                        inputs=[chatbot],
                        outputs=[msg, chatbot, status_output]
                    )
                    query_patterns_btn.click(
                        lambda h: self.quick_action("query_patterns", h),
                        inputs=[chatbot],
                        outputs=[msg, chatbot, status_output]
                    )
                    query_trends_btn.click(
                        lambda h: self.quick_action("query_trends", h),
                        inputs=[chatbot],
                        outputs=[msg, chatbot, status_output]
                    )

                    clear_btn.click(
                        lambda: ([], "", "✅ 对话已清空"),
                        outputs=[chatbot, msg, status_output]
                    )

                # Tab 2: Dashboard
                with gr.Tab("📊 数据看板"):
                    with gr.Row():
                        refresh_btn = gr.Button("🔄 刷新数据", variant="primary", size="lg")

                    with gr.Row():
                        with gr.Column(scale=1):
                            gr.Markdown("### ⚡ 快速统计")
                            summary_output = gr.JSON(label="摘要")

                        with gr.Column(scale=2):
                            gr.Markdown("### 📋 详细统计")
                            stats_output = gr.Markdown()

                    with gr.Row():
                        chart_output = gr.Image(label="📈 本周趋势图", show_label=True)

                    # Load dashboard on mount and refresh
                    def load_dashboard():
                        summary, stats, chart = self.get_dashboard_data()
                        return summary, stats, chart, "✅ 数据已更新"

                    refresh_btn.click(
                        load_dashboard,
                        outputs=[summary_output, stats_output, chart_output, status_output]
                    )

                    app.load(
                        load_dashboard,
                        outputs=[summary_output, stats_output, chart_output, status_output]
                    )

                # Tab 3: Report Generation
                with gr.Tab("📑 报告生成"):
                    gr.Markdown("### 生成AI驱动的周报")

                    with gr.Row():
                        weeks_slider = gr.Slider(
                            minimum=1,
                            maximum=4,
                            value=2,
                            step=1,
                            label="报告周期（周）",
                            info="选择包含的周数"
                        )
                        generate_btn = gr.Button("📊 生成报告", variant="primary", size="lg")

                    with gr.Row():
                        with gr.Column(scale=2):
                            report_output = gr.Markdown(label="📝 周报内容")

                        with gr.Column(scale=1):
                            report_chart = gr.Image(label="📈 报告图表")

                    def generate_report_with_status(weeks: int):
                        text, chart = self.generate_report(weeks)
                        status = "✅ 报告生成成功" if chart else "⚠️ 报告生成完成（图表不可用）"
                        return text, chart, status

                    generate_btn.click(
                        generate_report_with_status,
                        inputs=[weeks_slider],
                        outputs=[report_output, report_chart, status_output]
                    )

                # Tab 4: Data Export
                with gr.Tab("💾 数据导出"):
                    gr.Markdown("### 导出你的习惯数据")

                    with gr.Row():
                        csv_btn = gr.Button("📄 导出为 CSV", variant="primary", size="lg")
                        json_btn = gr.Button("📋 导出为 JSON", variant="secondary", size="lg")

                    export_output = gr.Textbox(
                        label="导出结果",
                        interactive=False,
                        placeholder="点击上方按钮导出数据..."
                    )

                    def export_csv_with_status():
                        result = self.export_data("csv")
                        return result, result

                    def export_json_with_status():
                        result = self.export_data("json")
                        return result, result

                    csv_btn.click(
                        export_csv_with_status,
                        outputs=[export_output, status_output]
                    )
                    json_btn.click(
                        export_json_with_status,
                        outputs=[export_output, status_output]
                    )

            # Footer
            gr.Markdown("---")
            gr.Markdown(
                """
                💡 **使用提示**:
                - 支持**自然语言输入**，比如 \"今天跑了5公里\"、\"我这周运动了几次？\"
                - 使用**快捷按钮**快速记录常见习惯
                - 在**数据看板**查看可视化统计
                - 生成**AI周报**获取个性化洞察和建议
                """
            )
            gr.Markdown(
                "🌟 **Trackit** v0.3.0 | 持续记录，发现更好的自己 | [GitHub](https://github.com/yourusername/Trackit)"
            )

        return app

    def launch(self, share: bool = False, server_port: int = 7860):
        """
        Launch the Gradio application.

        Args:
            share: Whether to create a public link
            server_port: Port to run the server on
        """
        app = self.create_interface()
        app.launch(share=share, server_port=server_port)


def create_app():
    """Create and return the Trackit app instance."""
    trackit_app = TrackitApp()
    return trackit_app.create_interface()


if __name__ == "__main__":
    import sys

    # Parse command line arguments
    share = "--share" in sys.argv
    port = 7860

    for arg in sys.argv:
        if arg.startswith("--port="):
            port = int(arg.split("=")[1])

    # Create and launch app
    print("🚀 Starting Trackit...")
    app = TrackitApp()
    app.launch(share=share, server_port=port)
