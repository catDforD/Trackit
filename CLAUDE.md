# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

## Git 工作流操作指南
- 每次提交时，都要写中文的 commit message，参考项目历史 commit 风格

## 项目概述

Trackit - 习惯追踪与复盘Agent，一个AI驱动的个人习惯管理和分析系统。

### 当前状态

**进度**: 第3周完成 (Day 15-21) ✅
**最后更新**: 2026-01-08
**完成度**: 75%

### 核心技术栈

| 组件 | 技术选型 |
|------|----------|
| 数据存储 | SQLite |
| LLM | Claude API / OpenAI API |
| 数据分析 | Pandas, NumPy |
| 可视化 | Matplotlib, Plotly |
| 前端 | Gradio 4.0+ |

### 项目架构

```
Trackit/
├── src/
│   ├── database/          # 数据库层 (SQLite)
│   ├── llm/               # LLM集成 (Claude/OpenAI)
│   ├── config/            # 配置管理
│   ├── agents/            # Agent系统
│   │   ├── base_agent.py
│   │   ├── recording_agent.py    # 记录Agent ✅
│   │   ├── query_agent.py        # 查询Agent ✅
│   │   └── analysis_agent.py     # 分析Agent ✅ (第2周)
│   ├── analysis/          # 数据分析 (第2周新增)
│   │   ├── time_series.py        # 时序分析 ✅
│   │   ├── patterns.py            # 模式检测 ✅
│   │   ├── visualizer.py          # 可视化 ✅
│   │   ├── exporter.py            # 数据导出 ✅
│   │   └── report_generator.py   # 报告生成 ✅ (第3周)
│   ├── app.py             # Gradio Web应用 ✅ (第3周)
│   └── utils/             # 工具模块
│       └── font_config.py # 中文字体配置 ✅ (第3周)
├── tests/                 # 测试套件 (208个测试)
├── docs/                  # 文档
├── data/                  # 数据目录
├── requirements.txt       # Python依赖
├── run_app.sh            # Web应用启动脚本 ✅ (第3周)
└── .env.example          # API密钥模板
```

### 已实现功能

#### 第1周 (Day 1-7) ✅
1. **数据库层** - SQLite schema, Repository模式, CRUD操作
2. **LLM集成** - Claude/OpenAI双支持, 自动重试, Token计数
3. **信息提取** - HabitExtractor, IntentClassifier, 准确率91.3%
4. **Agent系统** - RecordingAgent, QueryAgent
5. **缓存优化** - LRU缓存, 速度提升90万倍
6. **成本追踪** - API调用成本分析
7. **测试覆盖** - 72个测试全部通过

#### 第2周 (Day 8-14) ✅
1. **时序分析** - 周统计, 趋势分析, 移动平均, 线性回归
2. **模式检测** - 星期几模式, 连续记录, 关联分析
3. **数据可视化** - Matplotlib静态图, Plotly交互图
4. **数据导出** - CSV, JSON, 字典格式
5. **高级查询** - 智能路由, 5种查询类型
6. **测试扩展** - 67个新测试, 共147个测试

#### 第3周 (Day 15-21) ✅ 完成
1. **报告生成系统** - ReportGenerator, 周报生成, AI洞察
2. **Gradio Web界面** - 聊天界面, 数据看板, 报告展示
3. **数据导出UI** - CSV/JSON导出功能
4. **启动脚本** - 一键启动Web应用
5. **UI优化** - 快捷按钮, 响应式设计, 自定义样式
6. **中文字体配置** - FontConfig, 跨平台字体检测
7. **集成测试** - Web界面测试, 报告生成测试, E2E测试

### 代码统计

| 阶段 | 代码行数 | 测试数 |
|------|----------|--------|
| 第1周 | ~6,930 | 72 |
| 第2周 | ~4,979 | 67 |
| 第3周 | ~2,637 | 69 |
| **总计** | **~14,546** | **208** |

### 环境配置

**安装依赖**:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

**API密钥配置**:
```bash
cp .env.example .env
# 编辑 .env 文件，添加 ANTHROPIC_API_KEY 或 OPENAI_API_KEY
```

**运行测试**:
```bash
# 所有测试
python -m pytest tests/ -v

# 忽略性能测试
python -m pytest tests/ --ignore=tests/test_performance.py -v

# 特定测试文件
python -m pytest tests/test_analysis.py -v
```

### 核心模块使用示例

#### 1. RecordingAgent - 记录习惯
```python
from src.agents.recording_agent import RecordingAgent

agent = RecordingAgent()
result = agent.execute("今天跑了5公里，感觉不错")

if result["success"]:
    print(result["feedback"])
```

#### 2. QueryAgent - 查询习惯
```python
from src.agents.query_agent import QueryAgent

agent = QueryAgent()
result = agent.execute("我这周运动了几次？")

if result["success"]:
    print(result["response"])
```

#### 3. AnalysisAgent - 高级分析
```python
from src.agents.analysis_agent import AnalysisAgent

agent = AnalysisAgent()

# 模式查询
result = agent.execute("有什么规律吗？")

# 趋势查询
result = agent.execute("最近趋势怎么样？")

# 综合分析
result = agent.execute("给我一些分析和建议")

# 数据导出
result = agent.execute("导出数据", filename="habits.csv")
```

#### 4. 数据分析模块
```python
from src.analysis import TimeSeriesAnalyzer, PatternDetector, HabitVisualizer, DataExporter

# 时序分析
analyzer = TimeSeriesAnalyzer()
stats = analyzer.weekly_statistics()
trend = analyzer.trend_analysis(weeks=4)

# 模式检测
detector = PatternDetector()
patterns = detector.detect_day_of_week_patterns()
streaks = detector.detect_streaks()

# 可视化
visualizer = HabitVisualizer()
fig = visualizer.plot_weekly_summary()
fig.savefig('weekly_summary.png')

# 数据导出
exporter = DataExporter()
exporter.to_csv("export.csv")
exporter.to_json("export.json")
```

#### 5. 报告生成模块
```python
from src.analysis.report_generator import ReportGenerator

generator = ReportGenerator()

# 生成周报
report = generator.generate_weekly_report(weeks=2)

# 获取报告文本
print(report['text'])

# 获取AI洞察
if report['ai_insights']:
    print(report['ai_insights'])

# 保存报告
generator.save_report(report, 'weekly_report', format='md')
```

#### 6. Gradio Web应用
```bash
# 启动Web应用
python -m src.app --port=7862

# 或使用启动脚本
chmod +x run_app.sh
./run_app.sh
```

访问 http://localhost:7862 使用：
- **对话记录**: 自然语言记录和查询习惯
- **快捷操作**: 8个快速记录和查询按钮
- **数据看板**: 查看统计和图表
- **报告生成**: 生成AI驱动的周报
- **数据导出**: 导出CSV/JSON格式数据

### 下一步计划 (第4周)

**Day 22-23**: 多Agent架构
- LangGraph重构
- 状态管理优化

**Day 24-25**: 高级个性化
- 学习用户偏好
- 智能提醒系统

**Day 26-27**: 性能优化
- 批量LLM调用
- 数据库查询缓存

**Day 28**: 文档与打包

### 技术学习重点

**第1-2周已完成**:
- ✅ 数据库设计与优化
- ✅ Agent架构设计
- ✅ LLM集成与缓存
- ✅ Pandas时序分析
- ✅ 数据可视化
- ✅ 测试驱动开发

**第3周已完成**:
- ✅ 报告生成系统
- ✅ Gradio Web界面
- ✅ AI驱动的洞察生成
- ✅ UI优化与打磨
- ✅ 集成测试

**第4周目标**:
- 多Agent架构
- 高级个性化
- 性能优化

### 已知限制

1. **中文字体警告** - 在某些系统上，Matplotlib可能显示中文字体警告（不影响功能）
2. **性能测试阈值** - 部分性能测试需要根据环境调整阈值
3. **多Agent架构** - 第4周待实现

### 参考文档

- 详细进度: `PROGRESS.md`
- 开发计划: `/home/gargantua/.claude/plans/hidden-percolating-valley.md`
- 数据库设计: `docs/03_database_design.md`

---

**Happy Coding! 🚀**
