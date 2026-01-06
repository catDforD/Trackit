# Trackit - 习惯追踪与复盘Agent

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

> 一个基于LLM的智能习惯追踪系统，通过自然语言对话记录日常习惯，自动生成周报和个性化建议。

## ✨ 特性

- 🗣️ **自然语言输入** - 像聊天一样记录习惯，无需填写表单
- 🤖 **智能信息提取** - 使用Claude API自动提取结构化数据
- 📊 **时序分析** - 基于Pandas的趋势分析和模式发现
- 📈 **数据可视化** - 自动生成图表展示习惯趋势
- 📝 **智能周报** - LLM驱动的个性化复盘报告
- 🏗️ **可扩展架构** - Agent-based设计，易于扩展多Agent系统

## 🎯 应用场景

```python
# 用户只需自然语言输入
"今天跑了5公里，感觉不错"
"6点半起床，早起成功！"
"今天状态很差，什么都没做"

# Trackit自动：
# 1. 提取类别（运动/学习/睡眠/情绪/饮食）
# 2. 量化指标（距离、时长、次数等）
# 3. 记录情绪（positive/neutral/negative）
# 4. 存储到数据库
# 5. 生成反馈
```

## 🚀 快速开始

### 1. 安装依赖

```bash
# 克隆仓库
git clone https://github.com/catDforD/Trackit.git
cd Trackit

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置API密钥

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env文件，填入你的Claude API密钥
# ANTHROPIC_API_KEY=sk-ant-xxx
```

### 3. 初始化数据库

```python
from src.database.schema import init_database

schema = init_database()
print("✓ 数据库初始化成功")
```

### 4. 开始记录

```python
from src.agents.recording_agent import RecordingAgent

agent = RecordingAgent()
result = agent.execute(user_input="今天跑了5公里，感觉不错")

if result["success"]:
    print(result["feedback"])
    # ✓ 已记录：运动 😊
    #   distance_km: 5.0
```

## 📁 项目结构

```
Trackit/
├── src/
│   ├── agents/              # Agent模块
│   │   ├── base_agent.py    # Agent基类
│   │   └── recording_agent.py # 记录Agent
│   ├── database/            # 数据库层
│   │   ├── schema.py        # SQLite schema
│   │   └── repository.py    # 数据访问层
│   ├── llm/                 # LLM集成
│   │   ├── client.py        # Claude API客户端
│   │   └── extractors.py    # 信息提取器
│   ├── config/              # 配置管理
│   │   ├── settings.py      # 应用设置
│   │   └── prompts.py       # 提示词模板
│   └── utils/               # 工具模块
│       └── validators.py    # 数据验证
├── tests/                   # 测试套件
├── docs/                    # 教程文档
├── data/                    # 数据存储
├── requirements.txt         # Python依赖
├── .env.example             # 环境变量模板
└── README.md
```

## 🧪 运行测试

```bash
# 运行所有测试
python -m unittest discover tests

# 运行特定测试
python -m unittest tests.test_database -v

# 测试RecordingAgent（需要API密钥）
python -m src.agents.recording_agent
```

## 📊 核心技术栈

| 组件 | 技术 | 用途 |
|------|------|------|
| 数据库 | SQLite | 存储习惯记录 |
| LLM | Claude API | 信息提取、报告生成 |
| 数据分析 | Pandas | 时序分析、趋势检测 |
| 可视化 | Matplotlib/Plotly | 图表生成 |
| 前端 | Gradio | Web界面（开发中） |

## 🎓 学习价值

本项目是一个**教程级别的AI Agent实现**，涵盖：

1. ✅ **数据库设计** - SQLite schema、索引优化、Repository模式
2. ✅ **Agent架构** - 可扩展的BaseAgent、状态管理
3. ✅ **LLM集成** - API客户端、错误处理、成本优化
4. ✅ **信息提取** - Prompt工程、JSON验证、重试机制
5. ✅ **测试实践** - 单元测试、临时文件测试

详细教程请查看 `docs/` 目录。

## 📈 开发进度

- [x] 第1周 Day 1-2: 基础架构与数据库层 (100%)
- [x] 第1周 Day 3-4: LLM集成与信息提取 (100%)
- [x] 第1周 Day 5-6: Agent基础架构 (100%)
- [ ] 第1周 Day 7: 集成测试与优化
- [ ] 第2周: 查询与分析系统
- [ ] 第3周: 报告生成与Gradio界面
- [ ] 第4周: 多Agent架构重构

详见 [PROGRESS.md](PROGRESS.md)

## 🔮 未来计划

- [ ] QueryAgent - 自然语言查询
- [ ] AnalysisAgent - 时序分析与可视化
- [ ] Gradio Web界面
- [ ] 多Agent协作（LangGraph）
- [ ] 个性化建议系统
- [ ] 移动端支持

## 🤝 贡献

欢迎贡献！请随时提交Pull Request。

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 👨‍💻 作者

catDforD - [GitHub](https://github.com/catDforD)

## 🙏 致谢

- [Anthropic](https://www.anthropic.com/) - Claude API
- [LangChain](https://www.langchain.com/) - Agent框架参考
- [Gradio](https://www.gradio.app/) - Web界面框架

---

**注意**: 本项目为学习项目，请勿在生产环境中使用未测试的功能。

**Happy Coding! 🚀**
