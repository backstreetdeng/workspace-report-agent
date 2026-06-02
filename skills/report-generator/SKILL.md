---
name: report-generator
description: "汽车市场分析报告生成：根据分析数据生成专业Markdown格式的战略报告"
metadata: {"clawdbot":{"emoji":"📝"}, "openclaw": {"tools": ["generate"]}}
---

# 市场分析报告生成 Skill

## 功能说明

基于 PEST、波特五力、SWOT、4P 等分析结果，生成专业格式的市场战略分析报告。

## 工具列表

| 工具 | 用途 | 参数 |
|------|------|------|
| `generate` | 生成分析报告 | question, intent_type, pest_result, porter_result, swot_result, fourp_result |

## 输入参数

| 参数 | 类型 | 说明 |
|------|------|------|
| question | string | 用户原始问题 |
| intent_type | string | 意图类型 |
| pest_result | dict | PEST分析结果 |
| porter_result | dict | 波特五力分析结果 |
| swot_result | dict | SWOT分析结果 |
| fourp_result | dict | 4P分析结果 |

## 输出格式

```json
{
  "success": true,
  "markdown": "# 市场分析报告\n\n## 执行摘要\n...",
  "sections": {
    "summary": "执行摘要",
    "pest": "PEST分析",
    "porter": "波特五力",
    "swot": "SWOT分析",
    "fourp": "4P分析",
    "opportunities": "市场机会",
    "risks": "风险提示",
    "suggestions": "战略建议"
  }
}
```

## 报告结构

1. 执行摘要
2. 市场现状与数据
3. PEST宏观分析
4. 竞争格局（波特五力）
5. SWOT战略研判
6. 4P营销分析
7. 市场机会与风险
8. 战略建议

## 使用示例

```prose
session: analyst
  prompt: "使用 report-generator 生成报告：generate(question='...', intent_type='竞品分析', pest_result=..., porter_result=...)"
```

## 技术实现

- 主文件: `report_generator.py`
- 函数: `generate_report(question, intent_type, pest_result, porter_result, swot_result, fourp_result)`
- 依赖: LLM API (MiniMax/OpenAI)
