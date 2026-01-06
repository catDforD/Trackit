"""
LLM prompt templates for Trackit.

This module centralizes all prompts used for LLM interactions.
Having prompts in one place makes them easier to test, version control, and optimize.

Author: Trackit Development
"""

from typing import Dict, Any


class Prompts:
    """
    Collection of prompt templates for different LLM tasks.

    Prompts are organized by task:
    - Extraction: Converting natural language to structured data
    - Classification: Determining user intent
    - Report generation: Creating weekly reports
    - Response formatting: Generating user-friendly responses
    """

    # Information Extraction Prompts
    EXTRACTION_PROMPT = """你是一个习惯追踪助手。从用户输入中提取结构化信息。

用户输入: {user_input}

请提取并返回 ONLY 有效的 JSON，必须严格匹配以下格式：

```json
{{
    "category": "运动|学习|睡眠|情绪|饮食|其他",
    "mood": "positive|neutral|negative",
    "metrics": {{
        // 根据类别提取相关数值指标
        // 示例:
        // "distance_km": 5.0,
        // "duration_min": 30,
        // "wake_time": "06:30",
        // "sleep_hours": 7.5,
        // "pages": 20,
        // "count": 1
    }},
    "note": "额外备注或null"
}}
```

规则：
1. **只返回JSON，不要其他文字**
2. category必须是以下之一：运动、学习、睡眠、情绪、饮食、其他
3. mood根据用户情绪判断：
   - positive: 开心、兴奋、满足、有成就感
   - negative: 难过、疲惫、沮丧、焦虑
   - neutral: 其他情况
4. metrics提取所有可量化的数值，如果没有则为空对象 {{}}
5. note记录额外信息，如果没有则为null

示例：
输入: "今天跑了5公里，感觉不错"
输出: {{"category": "运动", "mood": "positive", "metrics": {{"distance_km": 5.0}}, "note": null}}

输入: "今天状态很差，什么都没做"
输出: {{"category": "其他", "mood": "negative", "metrics": {{}}, "note": "状态低落"}}

现在请处理用户输入并返回JSON：
"""

    INTENT_CLASSIFICATION_PROMPT = """你是一个意图分类器。判断用户查询的意图类型。

用户查询: {query}

请返回 ONLY JSON：

```json
{{
    "intent": "CATEGORY",
    "entities": {{
        "category": "运动|学习|睡眠|情绪|饮食|null",
        "timeframe": "today|week|month|null",
        "specific_date": "YYYY-MM-DD|null"
    }}
}}
```

意图类别：
1. **RECORD**: 用户想记录习惯（描述性的输入）
2. **COUNT**: 查询次数/频率（"多少次"、"几次"）
3. **LAST**: 查询最近一次（"上次"、"最后"）
4. **SUMMARY**: 查询总结（"怎么样"、"统计"、"概览"）
5. **COMPARISON**: 对比查询（"对比"、"比上周"、"vs"）
6. **REPORT**: 请求生成报告（"周报"、"月报"、"生成报告"）
7. **GENERAL**: 一般性对话或无法分类

示例：
输入: "我这周运动了几次？"
输出: {{"intent": "COUNT", "entities": {{"category": "运动", "timeframe": "week", "specific_date": null}}}}

输入: "我上周睡得怎么样？"
输出: {{"intent": "SUMMARY", "entities": {{"category": "睡眠", "timeframe": "week", "specific_date": null}}}}

输入: "生成周报"
输出: {{"intent": "REPORT", "entities": {{"category": null, "timeframe": "week", "specific_date": null}}}}

输入: "今天跑了5公里"
输出: {{"intent": "RECORD", "entities": {{"category": null, "timeframe": null, "specific_date": null}}}}

现在请分类：
"""

    # Report Generation Prompts
    WEEKLY_REPORT_PROMPT = """你是一个习惯追踪教练。根据用户本周的数据生成个性化周报。

## 本周数据摘要

{weekly_summary}

## 发现的模式

{patterns}

## 与上周对比

{comparison}

## 任务

请生成一份温暖、鼓励性的周报，包含以下部分：

### 1. 本周回顾 (100-150字)
- 简要总结本周整体表现
- 突出亮点和成就
- 用友好的语气

### 2. 趣味发现 (100-150字)
- 分享2-3个有趣的模式
- 比如"周三运动后心情都很好"
- 用数据说话但不枯燥

### 3. 数据洞察 (100-150字)
- 分析趋势和变化
- 指出积极的改进
- 客观但正面

### 4. 下周建议 (2-3条具体建议)
- 基于数据的可执行建议
- 每条建议都应该：
  - 具体（不是"多运动"而是"每周增加1次运动"）
  - 可衡量
  - 正向激励

## 要求

- **语调**: 友好、鼓励、有洞察力
- **格式**: Markdown，使用标题和列表
- **长度**: 400-600字
- **语言**: 中文

请现在生成周报：
"""

    # Response Formatting Prompts
    QUERY_RESPONSE_PROMPT = """根据查询结果生成自然语言的回复。

用户问题: {query}

查询结果: {results}

请生成一个友好、自然的回复：
- 直接回答用户的问题
- 如果结果为空，委婉说明
- 可以提供建议或追问
- 保持对话感
- 100字以内

生成回复：
"""

    PATTERN_ANALYSIS_PROMPT = """分析习惯数据中的有趣模式。

数据：
{data}

请分析并返回JSON：

```json
{{
    "patterns": [
        {{
            "description": "模式描述",
            "evidence": "支持这一模式的数据",
            "suggestion": "基于这一模式的建议"
        }}
    ]
}}
```

重点发现：
1. 日期/时间模式（如"周三状态通常不好"）
2. 相关性（如"运动后情绪更好"）
3. 趋势（如"早起天数在增加"）
4. 异常（如"某天明显不同"）

请现在分析：
"""

    @classmethod
    def get_extraction_prompt(cls, user_input: str) -> str:
        """
        Get the extraction prompt with user input filled in.

        Args:
            user_input: Raw user input text

        Returns:
            Formatted prompt string
        """
        return cls.EXTRACTION_PROMPT.format(user_input=user_input)

    @classmethod
    def get_classification_prompt(cls, query: str) -> str:
        """
        Get the classification prompt with query filled in.

        Args:
            query: User query text

        Returns:
            Formatted prompt string
        """
        return cls.INTENT_CLASSIFICATION_PROMPT.format(query=query)

    @classmethod
    def get_report_prompt(
        cls,
        weekly_summary: str,
        patterns: str,
        comparison: str
    ) -> str:
        """
        Get the weekly report generation prompt.

        Args:
            weekly_summary: Summary statistics
            patterns: Detected patterns
            comparison: Comparison with previous week

        Returns:
            Formatted prompt string
        """
        return cls.WEEKLY_REPORT_PROMPT.format(
            weekly_summary=weekly_summary,
            patterns=patterns,
            comparison=comparison
        )

    @classmethod
    def get_query_response_prompt(cls, query: str, results: str) -> str:
        """
        Get the query response prompt.

        Args:
            query: User's question
            results: Query results as string

        Returns:
            Formatted prompt string
        """
        return cls.QUERY_RESPONSE_PROMPT.format(
            query=query,
            results=results
        )


# Convenience function for quick access
def get_prompt(prompt_type: str, **kwargs) -> str:
    """
    Get a formatted prompt by type.

    Args:
        prompt_type: Type of prompt (extraction, classification, report, etc.)
        **kwargs: Variables to fill in the prompt template

    Returns:
        Formatted prompt string

    Example:
        >>> prompt = get_prompt("extraction", user_input="今天跑了5公里")
        >>> print(prompt)
    """
    prompts = Prompts()

    prompt_map = {
        "extraction": prompts.get_extraction_prompt,
        "classification": prompts.get_classification_prompt,
        "report": prompts.get_report_prompt,
        "query_response": prompts.get_query_response_prompt,
    }

    if prompt_type not in prompt_map:
        raise ValueError(f"Unknown prompt type: {prompt_type}")

    return prompt_map[prompt_type](**kwargs)


if __name__ == "__main__":
    # Test: Display sample prompts
    print("=" * 60)
    print("Sample Extraction Prompt")
    print("=" * 60)
    print(Prompts.get_extraction_prompt("今天跑了5公里，感觉不错"))
    print("\n" + "=" * 60)
    print("Sample Classification Prompt")
    print("=" * 60)
    print(Prompts.get_classification_prompt("我这周运动了几次？"))
