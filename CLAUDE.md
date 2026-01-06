# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Git 工作流操作指南
- 每次提交时,都要写中文的 commit message,参考项目历史 commit 风格

## 仓库概述

这是一个AI Agent学习项目仓库,用于研究生的AI/ML Agent系统学习。仓库包含三个详细的AI Agent项目设计文档,目前处于设计阶段,尚未开始代码实现。

### 三个核心项目

```
github_repo/
├── ShoppingDecisionAssistant/  # 多Agent购物决策助手
├── MemoriK/                      # 带记忆的知识管理助手
├── Trackit/                      # 习惯追踪与复盘Agent(当前目录)
└── to_do.md                      # 8周学习路线图
```

**技术递进关系:**
1. **ShoppingDecisionAssistant** (第1周) → 学习多Agent协作基础、工具调用
2. **MemoriK** (第2周) → 学习向量数据库、RAG检索
3. **Trackit** (第3周) → 综合运用:结构化提取 + 时序分析 + 报告生成

---

## 当前项目: Trackit (习惯追踪与复盘Agent)

### 项目定位

通过自然语言对话记录日常习惯(运动、学习、睡眠、情绪等),系统自动积累数据,周末自动生成复盘报告和个性化建议。

### 核心技术架构

```
用户输入
    │
    ▼
记录解析模块 (LLM提取结构化数据)
    │
    ▼
数据存储层 (SQLite)
    │
    ▼
分析与洞察 (Pandas时序分析)
    │
    ▼
报告生成Agent (数据驱动的个性化建议)
```

### 技术栈

| 组件 | 技术选型 | 用途 |
|------|----------|------|
| 数据存储 | SQLite | 存储每日习惯记录,支持复杂查询 |
| LLM | Claude API / GPT-4 | 自然语言→结构化数据提取、报告生成 |
| 数据分析 | Pandas | 时序趋势分析、周/月对比 |
| 可视化 | Matplotlib / Plotly | 在报告中嵌入趋势图表 |
| 前端 | Gradio | 对话界面 + 图表展示 |

### 数据结构设计

**每日记录:**
```python
{
    "date": "2026-01-10",
    "entries": [
        {
            "time": "08:30",
            "raw_input": "今天6点半起床,早起成功",
            "category": "睡眠",      # 类别: 运动/学习/睡眠/情绪/饮食
            "metrics": {"wake_time": "06:30", "early_rise": true},
            "mood": "positive",      # 情绪标签: positive/neutral/negative
            "note": null
        }
    ]
}
```

**周报数据:**
```python
{
    "week": "2026-W02",
    "summary": {
        "运动": {"count": 4, "total_distance_km": 18},
        "睡眠": {"avg_wake_time": "07:15", "early_rise_rate": 0.6},
        "情绪": {"positive_rate": 0.7}
    },
    "comparison_to_last_week": {...},
    "patterns": ["周三状态容易低落", "运动后情绪普遍较好"],
    "suggestions": ["尝试周二晚早睡,改善周三状态"]
}
```

### 四大功能模块

**1. 每日记录**
- 输入: 自然语言("今天跑了5公里"、"今天状态不太好")
- 输出: 确认记录成功 + 简单反馈

**2. 信息提取**
- 使用LLM将自然语言转为结构化数据
- 提取维度: 类别、数值、情绪标签、备注

**3. 即时查询**
- 示例: "我这周运动了几次?"、"上次跑步是什么时候?"
- 需要意图识别 + SQL查询

**4. 周期性复盘**
- 自动触发或手动请求
- 生成: 数据摘要、趋势分析、模式发现、改进建议

### 开发路线

**Day 1-2: 记录与提取**
- 设计SQLite schema
- 实现LLM信息提取(Prompt设计 + JSON输出)
- 测试各种输入格式

**Day 3-4: 查询功能**
- 实现基本统计查询
- 支持多种问法的意图识别

**Day 5-6: 复盘报告**
- 实现数据聚合逻辑
- 设计报告生成的Prompt
- 加入Matplotlib/Plotly可视化

**Day 7: 完善与优化**
- 优化对话体验
- 加入个性化建议
- 处理边界情况

---

## 通用开发规范

### 项目标准结构

每个项目应包含:
- `DESIGN.md` - 详细技术架构和实现计划(已存在)
- `README.md` - 项目概述、快速开始、演示(待创建)
- `requirements.txt` - Python依赖(待创建)
- `src/` - 源代码(待创建)
- `data/` - 本地数据存储(待创建)

### 依赖管理

创建虚拟环境:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows
```

安装依赖(项目开始时创建requirements.txt):
```bash
pip install -r requirements.txt
```

### 测试与运行

每个项目应该有:
- 运行主程序: `python src/main.py` 或 `gradio src/app.py`
- 运行测试: `pytest tests/` (如果实现测试)

### API密钥管理

所有项目使用 `.env` 文件存储敏感配置:
```
ANTHROPIC_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-xxx
TAVILY_API_KEY=tvly-xxx
```

使用 `python-dotenv` 加载:
```python
from dotenv import load_dotenv
load_dotenv()
```

**重要**: `.env` 文件必须在 `.gitignore` 中,永远不要提交API密钥。

---

## 与其他项目的关系

Trackit可以与MemoriK联动:
- Trackit记录学习习惯
- MemoriK存储具体学到的知识
- 复盘时可以关联:"你上周学了很多多Agent相关的内容"

---

## 技术学习重点

在实现Trackit时,重点关注以下可写成教程的技术点:

1. **LLM结构化信息提取**
   - Prompt设计确保输出稳定JSON
   - 错误处理和重试机制

2. **对话式应用的状态管理**
   - 跨session的上下文保持
   - 数据库schema设计

3. **时序数据分析与可视化**
   - Pandas时序操作
   - 趋势对比和模式发现

4. **数据驱动的报告生成**
   - 如何设计Prompt让LLM生成有洞见的报告
   - 数据可视化的最佳实践

---

## 延伸方向

完成基础版后可考虑:
- 通知提醒(每晚提醒记录)
- 语音输入支持
- 与日历/待办应用集成
- 长期趋势分析(月报、季报)
- 与MemoriK知识库联动

---

## 注意事项

- **当前状态**: Trackit项目已完成第1周前半部分的基础架构实现
- **优先级**: 建议按 ShoppingDecisionAssistant → MemoriK → Trackit 的顺序实现
- **语言**: 设计文档用中文,代码和注释用英文
- **文档**: 每个项目完成后应产出教程级别的代码和README
- **演示**: 每个项目应有清晰的演示,易于理解和使用

---

## 当前开发进度

**最后更新**: 2026-01-06
**当前阶段**: 第1周 Day 1-2 完成 (基础架构与数据库层)

### ✅ 已完成的工作

#### 1. 项目基础设施 (100%)
```
Trackit/
├── requirements.txt          ✅ 所有依赖已定义
├── .env.example              ✅ API密钥模板
├── .gitignore               ✅ Git忽略规则
├── PROGRESS.md              ✅ 进度报告文档
├── src/                     ✅ 完整的目录结构
├── tests/                   ✅ 测试目录
├── docs/                    ✅ 文档目录
└── data/                    ✅ 数据目录
```

#### 2. 核心模块实现

**数据库层** (src/database/) - 100%
- ✅ `schema.py` - SQLite表结构定义
  - entries表 (习惯记录)
  - weekly_reports表 (周报缓存)
  - 索引优化
- ✅ `repository.py` - 数据访问层
  - CRUD操作
  - 日期/周查询
  - 统计聚合
- ✅ 测试: 7个单元测试全部通过

**LLM集成层** (src/llm/, src/config/) - 100%
- ✅ `client.py` - Claude API客户端
  - 自动重试机制
  - Token计数和成本估算
  - JSON提取工具
- ✅ `settings.py` - 配置管理
  - 模型选择 (Haiku/Sonnet优化)
  - 成本追踪
- ✅ `prompts.py` - 提示词模板库
  - 信息提取Prompt
  - 意图分类Prompt
  - 报告生成Prompt

**信息提取模块** (src/llm/extractors.py, src/utils/validators.py) - 100%
- ✅ HabitExtractor类
  - 自然语言→结构化数据
  - 批量提取支持
  - 重试验证
- ✅ IntentClassifier类
  - 意图分类
  - 实体提取
- ✅ 完整的验证器
  - JSON schema验证
  - 类别/指标验证
  - 日期时间验证

**Agent基础架构** (src/agents/) - 100%
- ✅ `base_agent.py` - Agent基类
  - LangGraph兼容的状态管理
  - 统一执行接口
  - 统计追踪
- ✅ `recording_agent.py` - 记录Agent
  - 完整工作流: 提取→验证→存储→反馈
  - 用户友好的反馈生成
  - 错误处理

**测试套件** (tests/) - 100%
- ✅ `test_database.py` - 数据库测试 (7个测试, 全部通过)
- ✅ `test_extractors.py` - 验证器测试 (17个测试)

**文档** (docs/) - 17% (1/6完成)
- ✅ `03_database_design.md` - 数据库设计教程 (6000+字)
- ⏳ 其他5篇教程待编写

### 📊 代码统计

| 模块 | 文件数 | 代码行数 | 状态 |
|------|--------|----------|------|
| database | 2 | ~250 | ✅ 完成 |
| config | 2 | ~200 | ✅ 完成 |
| llm | 2 | ~350 | ✅ 完成 |
| agents | 2 | ~200 | ✅ 完成 |
| utils | 1 | ~250 | ✅ 完成 |
| tests | 2 | ~300 | ✅ 完成 |
| docs | 1 | ~600 | ⏳ 进行中 |
| **总计** | **17** | **~2,150** | **45%** |

### 🎯 下一步计划

**立即可做的任务**:
1. 安装依赖: `pip install -r requirements.txt`
2. 配置API密钥: 复制`.env.example`到`.env`并填入`ANTHROPIC_API_KEY`
3. 测试RecordingAgent: `python -m src.agents.recording_agent`

**第1周后半部分** (Day 3-7):
- Day 3-4: LLM集成测试
  - 测试HabitExtractor提取准确率
  - 优化Prompt提高准确率
  - 实现批量提取和缓存
- Day 5-6: QueryAgent基础版
  - 实现QueryAgent框架
  - 添加基本查询模式
  - 集成IntentClassifier
- Day 7: 集成测试和优化
  - 端到端工作流测试
  - 性能基准测试
  - 成本分析

**第2周**: 查询与分析系统
- Day 8-9: 意图分类增强
- Day 10-11: Pandas时序分析
- Day 12-13: 数据可视化 (Matplotlib/Plotly)
- Day 14: 集成测试

### 🔧 如何使用当前代码

**无需API密钥的功能**:
```python
# 数据库操作
from src.database.schema import init_database
from src.database.repository import HabitRepository

schema = init_database()
repo = HabitRepository()
entry_id = repo.add_entry(...)
```

**需要API密钥的功能**:
```python
# 完整的LLM工作流
import os
os.environ["ANTHROPIC_API_KEY"] = "your_key"

from src.agents.recording_agent import RecordingAgent
agent = RecordingAgent()
result = agent.execute(user_input="今天跑了5公里")
```

### 📝 关键学习成果

1. **数据库设计**: SQLite schema、索引优化、Repository模式
2. **Agent架构**: 可扩展的BaseAgent、状态管理
3. **LLM集成**: API客户端、错误处理、成本优化
4. **测试实践**: 单元测试、临时文件测试

### 📖 推荐学习顺序

1. **阅读已实现的代码**:
   - `src/database/schema.py` - 理解数据库设计
   - `src/database/repository.py` - 学习数据访问层
   - `src/agents/base_agent.py` - 理解Agent架构

2. **阅读教程**: `docs/03_database_design.md`

3. **运行测试**: `python -m unittest tests.test_database -v`

4. **实验和扩展**: 修改现有代码,添加新功能

### 🚧 已知限制

1. **LLM功能需要API密钥** - 未配置时会报错
2. **依赖包未安装** - 需要运行`pip install -r requirements.txt`
3. **功能不完整** - QueryAgent、分析模块、Gradio界面未实现

### 📞 继续开发

当准备好继续时:
1. 参考`PROGRESS.md`了解详细进度
2. 查看计划文件: `/home/gargantua/.claude/plans/hidden-percolating-valley.md`
3. 继续实现第1周剩余任务
