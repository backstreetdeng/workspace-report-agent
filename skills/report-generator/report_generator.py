"""
report-generator skill
汽车市场战略分析报告生成器

功能：
- 基于分析结果生成结构化报告
- 支持Markdown/JSON格式输出
- 自动汇总各模块分析结论
"""

import sys
import os
import json
from typing import Dict, Any, Optional
from datetime import datetime

# 添加RAG引擎路径
RAG_ENGINE_PATH = r"E:\AI\data\envs\car_agent_env\ai-decision\rag-engine"
if RAG_ENGINE_PATH not in sys.path:
    sys.path.insert(0, RAG_ENGINE_PATH)


def format_market_data(data: Dict[str, Any]) -> str:
    """格式化市场数据 - 支持 HybridAgent 输出格式"""
    if not data:
        return "数据获取失败"

    lines = []

    # HybridAgent 格式: data 本身就有 scale, growth_rate, trend 等字段
    # 原始格式: data 里有 market_overview 嵌套

    # 检查是否是嵌套格式
    if "market_overview" in data:
        data = data["market_overview"]

    if not data:
        return "数据获取失败"

    # HybridAgent 格式
    if data.get("scale"):
        lines.append(f"**市场规模**: {data['scale']}")
    if data.get("growth_rate"):
        lines.append(f"**增速**: {data['growth_rate']}")
    if data.get("concentration"):
        lines.append(f"**集中度**: {data['concentration']}")
    if data.get("trend"):
        lines.append(f"**趋势**: {data['trend']}")

    # 原始格式字段
    if data.get("total_sales"):
        lines.append(f"**市场规模**: {data['total_sales']:,}辆")
    if data.get("brand_count"):
        lines.append(f"**品牌数量**: {data['brand_count']}")
    if data.get("model_count"):
        lines.append(f"**车型数量**: {data['model_count']}")
    if data.get("data_period"):
        lines.append(f"**数据周期**: {data['data_period']}")

    return "\n".join(lines) if lines else "暂无数据"


def format_brand_ranking(brands: list) -> str:
    """格式化品牌排名 - 支持 HybridAgent competitors 格式"""
    if not brands:
        return "暂无数据"

    lines = []
    for i, brand in enumerate(brands[:10], 1):
        # 兼容 HybridAgent competitors 格式
        name = brand.get("brand") or brand.get("name", "N/A")
        # sales 可能是 sales 或 sales_volume
        sales = brand.get("sales") or brand.get("sales_volume", 0)
        # share 可能是 share 或 market_share
        share = brand.get("share")
        if share is None:
            share = brand.get("market_share", 0)

        lines.append(f"{i}. **{name}** - {sales:,}辆 ({share:.1f}%)")

    return "\n".join(lines)


def format_trend(trend: list) -> str:
    """格式化趋势数据"""
    if not trend:
        return "暂无数据"

    lines = []
    for item in trend[-6:]:  # 最近6个月
        month = item.get("month", "N/A")
        sales = item.get("sales", 0)
        yoy = item.get("yoy_growth", 0)
        yoy_str = f"+{yoy}%" if yoy >= 0 else f"{yoy}%"
        lines.append(f"- {month}: {sales:,}辆 (同比{yoy_str})")

    return "\n".join(lines)


def format_pest(pest_data: Dict[str, Any]) -> str:
    """格式化PEST分析"""
    if not pest_data:
        return "暂无数据"

    lines = ["### PEST宏观环境分析\n"]

    dims = pest_data.get("dimensions", {})
    for key, dim in dims.items():
        dim_name = {"political": "政治", "economic": "经济", "social": "社会", "technological": "技术"}.get(key, key)
        sentiment = dim.get("overall_impact", "neutral")
        sentiment_emoji = {"positive": "📈", "negative": "📉", "neutral": "➡️"}.get(sentiment, "")

        lines.append(f"\n#### {dim_name} ({sentiment_emoji})\n")

        items = dim.get("items", [])[:3]  # 只显示前3条
        for item in items:
            impact = "✅" if item.get("impact") == "positive" else "⚠️" if item.get("impact") == "negative" else "➡️"
            lines.append(f"- {impact} {item.get('item', 'N/A')}")

    return "\n".join(lines)


def format_porter(porter_data: Dict[str, Any]) -> str:
    """格式化波特五力分析"""
    if not porter_data:
        return "暂无数据"

    lines = ["### 波特五力竞争分析\n"]

    summary = porter_data.get("summary", {})
    lines.append(f"\n**行业吸引力**: {summary.get('industry_attractiveness', 'N/A')}")
    lines.append(f"**综合评分**: {summary.get('overall_score', 'N/A')}/10")
    lines.append(f"**最大威胁**: {summary.get('most_threatening_force', 'N/A')}\n")

    forces = porter_data.get("forces", {})
    for key, force in forces.items():
        name = force.get("name", "N/A")
        score = force.get("score", 0)
        level = force.get("level", "N/A")
        level_emoji = {"very_high": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(level, "⚪")

        lines.append(f"\n#### {level_emoji} {name} (评分: {score}/10)\n")
        factors = force.get("factors", [])[:2]
        for f in factors:
            lines.append(f"- {f}")

    return "\n".join(lines)


def format_swot(swot_data: Dict[str, Any]) -> str:
    """格式化SWOT分析"""
    if not swot_data:
        return "暂无数据"

    lines = ["### SWOT战略分析\n"]

    swot = swot_data.get("swot", {})

    # 优势
    lines.append("\n#### 💪 优势 (Strengths)\n")
    for item in swot.get("strengths", [])[:3]:
        lines.append(f"- **{item.get('item', 'N/A')}**: {item.get('evidence', '')}")

    # 劣势
    lines.append("\n#### 📉 劣势 (Weaknesses)\n")
    for item in swot.get("weaknesses", [])[:3]:
        lines.append(f"- **{item.get('item', 'N/A')}**: {item.get('evidence', '')}")

    # 机会
    lines.append("\n#### 🚀 机会 (Opportunities)\n")
    for item in swot.get("opportunities", [])[:3]:
        lines.append(f"- **{item.get('item', 'N/A')}**: {item.get('evidence', '')}")

    # 威胁
    lines.append("\n#### ⚠️ 威胁 (Threats)\n")
    for item in swot.get("threats", [])[:3]:
        lines.append(f"- **{item.get('item', 'N/A')}**: {item.get('evidence', '')}")

    # 策略建议
    strategies = swot_data.get("strategies", {})
    if strategies:
        lines.append("\n#### 📋 战略建议\n")
        for so in strategies.get("SO_strategy", [])[:2]:
            lines.append(f"- 📈 **SO**: {so}")
        for wo in strategies.get("WO_strategy", [])[:2]:
            lines.append(f"- 🔧 **WO**: {wo}")

    return "\n".join(lines)


def format_fourp(fourp_data: Dict[str, Any]) -> str:
    """格式化4P分析"""
    if not fourp_data:
        return "暂无数据"

    lines = ["### 4P营销组合分析\n"]

    analysis = fourp_data.get("4p_analysis", {})
    summary = fourp_data.get("summary", {})

    lines.append(f"\n**综合评分**: {summary.get('overall_score', 'N/A')}/10 ({summary.get('overall_level', 'N/A')})")
    lines.append(f"**最佳维度**: {summary.get('best_dimension', 'N/A')}")
    lines.append(f"**短板维度**: {summary.get('weakest_dimension', 'N/A')}\n")

    dims = {
        "product": "📦 产品",
        "price": "💰 价格",
        "place": "🏪 渠道",
        "promotion": "📢 促销"
    }

    for key, name in dims.items():
        dim = analysis.get(key, {})
        score = dim.get("score", 0)
        level = dim.get("level", "N/A")
        lines.append(f"\n#### {name} (评分: {score}/10, {level})\n")

        strengths = dim.get("strengths", [])[:2]
        weaknesses = dim.get("weaknesses", [])[:2]

        if strengths:
            lines.append("**优势:**")
            for s in strengths:
                lines.append(f"- {s}")

        if weaknesses:
            lines.append("**劣势:**")
            for w in weaknesses:
                lines.append(f"- {w}")

    return "\n".join(lines)


def generate_report(
    question: str,
    intent_type: str,
    market_data: Dict[str, Any] = None,
    branch_result: Dict[str, Any] = None,
    pest_result: Dict[str, Any] = None,
    porter_result: Dict[str, Any] = None,
    swot_result: Dict[str, Any] = None,
    fourp_result: Dict[str, Any] = None,
    vector_results: list = None,
    sql_results: list = None,
    sentiment_results: list = None,
    output_format: str = "markdown"
) -> Dict[str, Any]:
    """
    生成分析报告

    Args:
        question: 用户原始问题
        intent_type: 意图类型
        market_data: 市场结构化数据
        branch_result: 分支分析结果
        pest_result: PEST分析结果 (可能是 {"success": True, "data": {...}} 或直接是数据)
        porter_result: 波特五力结果 (可能是 {"success": True, "data": {...}} 或直接是数据)
        swot_result: SWOT分析结果 (可能是 {"success": True, "data": {...}} 或直接是数据)
        fourp_result: 4P分析结果 (可能是 {"success": True, "data": {...}} 或直接是数据)
        vector_results: 向量检索结果
        sql_results: SQL查询结果
        sentiment_results: 舆情结果
        output_format: 输出格式 (markdown/json)

    Returns:
        报告结果
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 解包数据（处理 skill 返回的包装格式）
    pest_data = pest_result.get("data") if isinstance(pest_result, dict) else pest_result
    porter_data = porter_result.get("data") if isinstance(porter_result, dict) else porter_result
    swot_data = swot_result.get("data") if isinstance(swot_result, dict) else swot_result
    fourp_data = fourp_result.get("data") if isinstance(fourp_result, dict) else fourp_result

    # 构建报告内容
    content = {
        "header": {
            "title": "汽车市场战略分析报告",
            "question": question,
            "intent_type": intent_type,
            "timestamp": timestamp
        },
        "executive_summary": _generate_executive_summary(
            intent_type, branch_result, pest_data, porter_data
        ),
        "market_data": market_data,
        "branch_analysis": branch_result,
        "pest_analysis": pest_data,
        "porter_analysis": porter_data,
        "swot_analysis": swot_data,
        "fourp_analysis": fourp_data,
        "reference_materials": {
            "vector_search": vector_results[:3] if vector_results else [],
            "structured_data": sql_results[:5] if sql_results else [],
            "sentiment": sentiment_results[:3] if sentiment_results else []
        }
    }

    # 生成Markdown格式
    markdown_report = _generate_markdown_report(content)

    # 返回结果
    return {
        "success": True,
        "format": output_format,
        "timestamp": timestamp,
        "content": content,
        "markdown": markdown_report,
        "summary": content["executive_summary"]
    }


def _generate_executive_summary(
    intent_type: str,
    branch_result: Dict[str, Any] = None,
    pest_result: Dict[str, Any] = None,
    porter_result: Dict[str, Any] = None
) -> Dict[str, Any]:
    """生成执行摘要"""
    summary = {
        "intent": intent_type,
        "key_findings": [],
        "recommendations": []
    }

    # 从PEST提取关键发现
    if pest_result and isinstance(pest_result, dict):
        summary_data = pest_result.get("summary", {})
        sentiment = summary_data.get("overall_sentiment", "中性")
        opportunities = summary_data.get("key_opportunities", [])[:2]
        threats = summary_data.get("key_threats", [])[:2]

        if sentiment:
            summary["key_findings"].append(f"宏观环境整体{sentiment}，有利于市场发展")
        for opp in opportunities:
            summary["key_findings"].append(f"机会：{opp}")
        for threat in threats:
            summary["key_findings"].append(f"风险：{threat}")

    # 从波特五力提取建议
    if porter_result and isinstance(porter_result, dict):
        porter_summary = porter_result.get("summary", {})
        attractiveness = porter_summary.get("industry_attractiveness", "")
        if attractiveness:
            summary["key_findings"].append(f"行业{attractiveness}")

        recommendations = porter_summary.get("strategic_recommendations", [])[:2]
        for rec in recommendations:
            summary["recommendations"].append(rec)

    return summary


def _generate_markdown_report(content: Dict[str, Any]) -> str:
    """生成Markdown格式报告"""
    lines = []

    # 标题
    lines.append("# 汽车市场战略分析报告\n")
    lines.append(f"**分析时间**: {content['header']['timestamp']}")
    lines.append(f"**原始问题**: {content['header']['question']}")
    lines.append(f"**意图类型**: {content['header']['intent_type']}\n")

    lines.append("---\n")

    # 执行摘要
    lines.append("## 📋 执行摘要\n")
    summary = content.get("executive_summary", {})
    for finding in summary.get("key_findings", []):
        lines.append(f"- {finding}")
    if summary.get("recommendations"):
        lines.append("\n**建议:**")
        for rec in summary.get("recommendations"):
            lines.append(f"- {rec}")

    lines.append("\n---\n")

    # 市场数据 - 支持 HybridAgent 格式
    market_data = content.get("market_data", {})
    if market_data:
        lines.append("## 📊 市场数据\n")

        # HybridAgent 格式: market_overview, competitors
        # 原始格式: market_overview{...}, brand_ranking{...}, sales_trend{...}
        mo = market_data.get("market_overview", {})
        if mo:
            lines.append(format_market_data(mo))

        # 优先使用 competitors（HybridAgent格式）
        competitors = market_data.get("competitors", [])
        if competitors:
            lines.append("\n### 品牌排名 (Top 10)\n")
            lines.append(format_brand_ranking(competitors))
        else:
            # 回退到 brand_ranking（原始格式）
            brands = market_data.get("brand_ranking", [])
            if brands:
                lines.append("\n### 品牌排名 (Top 10)\n")
                lines.append(format_brand_ranking(brands))

        trend = market_data.get("sales_trend", [])
        if trend:
            lines.append("\n### 销量趋势\n")
            lines.append(format_trend(trend))

    lines.append("\n---\n")

    # PEST分析
    pest = content.get("pest_analysis", {})
    if pest:
        lines.append(format_pest(pest))

    lines.append("\n---\n")

    # 波特五力
    porter = content.get("porter_analysis", {})
    if porter:
        lines.append(format_porter(porter))

    lines.append("\n---\n")

    # SWOT
    swot = content.get("swot_analysis", {})
    if swot:
        lines.append(format_swot(swot))

    lines.append("\n---\n")

    # 4P
    fourp = content.get("fourp_analysis", {})
    if fourp:
        lines.append(format_fourp(fourp))

    lines.append("\n---\n")

    # 参考资料
    lines.append("## 📚 参考资料\n")
    ref = content.get("reference_materials", {})
    vector_refs = ref.get("vector_search", [])
    if vector_refs:
        lines.append("\n### 向量检索结果\n")
        for i, r in enumerate(vector_refs, 1):
            lines.append(f"{i}. {r.get('content', '')[:100]}...\n")

    return "\n".join(lines)


# OpenClaw skill 接口
def skill_main(action: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    OpenClaw skill 主入口

    Args:
        action: 操作类型 (generate)
        params: 参数字典

    Returns:
        标准化结果
    """
    if params is None:
        params = {}

    if action == "generate":
        return generate_report(
            question=params.get("question", ""),
            intent_type=params.get("intent_type", "综合分析"),
            market_data=params.get("market_data"),
            branch_result=params.get("branch_result"),
            pest_result=params.get("pest_result"),
            porter_result=params.get("porter_result"),
            swot_result=params.get("swot_result"),
            fourp_result=params.get("fourp_result"),
            vector_results=params.get("vector_results"),
            sql_results=params.get("sql_results"),
            sentiment_results=params.get("sentiment_results"),
            output_format=params.get("format", "markdown")
        )
    else:
        return {"success": False, "error": f"未知操作: {action}"}


if __name__ == "__main__":
    # 命令行测试
    import argparse

    parser = argparse.ArgumentParser(description="报告生成")
    parser.add_argument("--question", default="分析比亚迪的市场战略")
    parser.add_argument("--intent", default="综合分析")

    args = parser.parse_args()

    result = generate_report(
        question=args.question,
        intent_type=args.intent
    )

    print(result["markdown"])
