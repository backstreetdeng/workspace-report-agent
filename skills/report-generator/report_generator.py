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


def format_brand_ranking(brands: list, total_sales: int = None) -> str:
    """格式化品牌排名 - 支持品牌聚合格式"""
    if not brands:
        return "暂无数据"

    lines = []
    # 计算总销量（如果没有提供，从数据中计算）
    if total_sales is None or total_sales == 0:
        total_sales = sum(b.get("sales", 0) for b in brands)

    for i, brand in enumerate(brands[:10], 1):
        name = brand.get("brand") or brand.get("name", "N/A")
        sales = brand.get("sales") or brand.get("sales_volume", 0) or 0

        # 计算市场份额
        if total_sales > 0:
            share = (sales / total_sales) * 100
        else:
            share = 0

        lines.append(f"{i}. **{name}** - {sales:,}辆 ({share:.1f}%)")

    return "\n".join(lines)


def format_competitors(competitors: list) -> str:
    """格式化车型详情列表"""
    if not competitors:
        return "暂无数据"

    lines = []
    for i, comp in enumerate(competitors[:15], 1):
        brand = comp.get("brand", "未知")
        model = comp.get("model", "未知")
        sales = comp.get("sales", 0) or 0
        price = comp.get("price", "")
        price_str = f" | {price}" if price else ""

        lines.append(f"{i}. **{brand} {model}** - {sales:,}辆{price_str}")

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
    brand_result: Dict[str, Any] = None,
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
        brand_result: 品牌分析结果
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

    # 如果 market_data 为 None，自动从 sql_results 构建
    if market_data is None and sql_results:
        market_data = _build_market_data_from_sql(sql_results, question)

    # 构建报告内容
    content = {
        "header": {
            "title": "汽车市场战略分析报告",
            "question": question,
            "intent_type": intent_type,
            "timestamp": timestamp
        },
        "executive_summary": _generate_executive_summary(
            intent_type, brand_result, pest_data, porter_data
        ),
        "market_data": market_data,
        "brand_analysis": brand_result,
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
    brand_result: Dict[str, Any] = None,
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


def _get_model_prices_from_db():
    """从数据库获取车型价格映射"""
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        import os

        DB_CONFIG = {
            "host": os.environ.get("DB_HOST", "192.168.3.146"),
            "port": int(os.environ.get("DB_PORT", 5432)),
            "database": os.environ.get("DB_NAME", "vectordb"),
            "user": os.environ.get("DB_USER", "vectordb"),
            "password": os.environ.get("DB_PASSWORD", "vectordb123")
        }

        conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
        cur = conn.cursor()

        sql = """
        SELECT
            "车型名称",
            "厂商",
            "厂商指导价",
            "级别",
            CAST(NULLIF(REGEXP_REPLACE("厂商指导价", '[^0-9.]', '', 'g'), '') AS NUMERIC) * 10000 as price_yuan
        FROM config_data
        WHERE NULLIF(REGEXP_REPLACE("厂商指导价", '[^0-9.]', '', 'g'), '') ~ '^[0-9.]+$'
        """
        cur.execute(sql)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        # 构建映射：车型名称 -> (厂商, 价格)
        price_map = {}
        for r in rows:
            model = r.get("车型名称", "")
            manufacturer = r.get("厂商", "")
            price_str = r.get("厂商指导价", "")
            price_yuan = r.get("price_yuan", 0)
            if model:
                price_map[model] = {
                    "manufacturer": manufacturer,
                    "price": price_str,
                    "price_yuan": float(price_yuan) if price_yuan else 0
                }
        return price_map
    except Exception as e:
        print(f"Error getting model prices: {e}")
        return {}


def _build_market_data_from_sql(sql_results: list, question: str = None) -> Dict[str, Any]:
    """从SQL查询结果构建市场数据"""
    if not sql_results:
        return {}

    market_data = {}

    # 价格区间映射
    price_mapping = {
        "10万以下": (0, 100000),
        "10万以内": (0, 100000),
        "10-15万": (100000, 150000),
        "10-18万": (100000, 180000),
        "10-20万": (100000, 200000),
        "15-20万": (150000, 200000),
        "15-25万": (150000, 250000),
        "20-30万": (200000, 300000),
        "20-35万": (200000, 350000),
        "30-50万": (300000, 500000),
        "30万以上": (300000, 9999999),
        "50万以上": (500000, 9999999)
    }

    # 从问题中提取价格区间
    min_price = 0
    max_price = 99999999
    price_range_text = ""
    if question:
        for keyword, (min_p, max_p) in price_mapping.items():
            if keyword in question:
                min_price = min_p
                max_price = max_p
                price_range_text = keyword
                break

    # 品牌名称映射表（车企 -> 品牌）
    BRAND_NAME_MAP = {
        # 比亚迪
        "比亚迪汽车工业有限公司": "比亚迪",
        "比亚迪汽车有限公司": "比亚迪",
        "比亚迪": "比亚迪",
        # 特斯拉
        "特斯拉(上海)有限公司": "特斯拉",
        "特斯拉": "特斯拉",
        # 零跑
        "零跑汽车有限公司": "零跑",
        "零跑": "零跑",
        # 吉利
        "浙江吉利汽车有限公司": "吉利",
        "吉利汽车集团有限公司": "吉利",
        "吉利": "吉利",
        # 长安
        "重庆长安汽车股份有限公司": "长安",
        "长安": "长安",
        # 小米
        "小米汽车科技有限公司": "小米",
        "小米": "小米",
        # 蔚来
        "蔚来汽车科技（安徽）有限公司": "蔚来",
        "蔚来": "蔚来",
        # 小鹏
        "小鹏": "小鹏",
        # 理想
        "理想汽车": "理想",
        "理想": "理想",
        # 五菱
        "上汽通用五菱汽车股份有限公司": "五菱",
        "五菱": "五菱",
        # 广汽丰田
        "广汽丰田汽车有限公司": "广汽丰田",
        "广汽丰田": "广汽丰田",
        "一汽丰田": "一汽丰田",
        # 广汽
        "广汽埃安新能源汽车股份有限公司": "广汽埃安",
        "广汽埃安": "广汽埃安",
        "广汽乘用车有限公司": "广汽传祺",
        # 奇瑞
        "奇瑞新能源汽车股份有限公司": "奇瑞",
        "奇瑞汽车股份有限公司": "奇瑞",
        "奇瑞": "奇瑞",
        # 大众
        "一汽-大众汽车有限公司": "一汽大众",
        "上汽大众汽车有限公司": "上汽大众",
        # 东风
        "东风汽车集团有限公司": "东风",
        "东风": "东风",
        # 其他
        "长城汽车股份有限公司": "长城",
        "长城": "长城",
        "吉利": "吉利",
        "领克": "领克",
        "极氪": "极氪",
    }

    def normalize_brand(name):
        """标准化品牌名称"""
        if not name:
            return "未知"
        # 先检查完整匹配
        if name in BRAND_NAME_MAP:
            return BRAND_NAME_MAP[name]
        # 检查包含关系
        for full_name, short_name in BRAND_NAME_MAP.items():
            if full_name in name or name in full_name:
                return short_name
        return name

    # 获取车型价格映射
    model_prices = _get_model_prices_from_db()

    def get_model_price(model_name):
        """获取车型的价格信息"""
        if model_name in model_prices:
            return model_prices[model_name]
        # 尝试模糊匹配
        for config_model, price_info in model_prices.items():
            if config_model in model_name or model_name in config_model:
                return price_info
        return None

    # 检查是否是 market_overview 格式（total_sales, brand_count, model_count）
    first = sql_results[0]
    if "total_sales" in first or "brand_count" in first:
        market_data["market_overview"] = {
            "total_sales": first.get("total_sales", 0),
            "brand_count": first.get("brand_count", 0),
            "model_count": first.get("model_count", 0)
        }

    # 检查是否是品牌/车型销量格式
    if "sales" in first or "brand" in first:
        # 为每个结果匹配价格并过滤
        enriched_results = []
        no_price_models = []  # 没有价格信息的车型（暂不包含）

        for row in sql_results:
            model = row.get("model", row.get("通用名称", ""))
            price_info = get_model_price(model)
            price_yuan = price_info["price_yuan"] if price_info else 0

            enriched_row = {
                **row,
                "price": price_info["price"] if price_info else "",
                "price_yuan": price_yuan,
                "has_price": price_info is not None
            }

            # 价格区间过滤（只过滤有价格信息的车型）
            if price_range_text and price_yuan > 0:
                if price_yuan < min_price or price_yuan > max_price:
                    continue  # 跳过价格不符合的车型

            enriched_results.append(enriched_row)

        # 如果过滤后有数据，使用过滤结果；否则使用原始数据
        if enriched_results:
            sql_results = enriched_results

        # 构建品牌排名（去重 + 品牌名映射）
        brand_sales = {}
        model_set = set()  # 用于去重车型
        for row in sql_results:
            raw_brand = row.get("brand", row.get("企业名称", "未知"))
            model = row.get("model", row.get("通用名称", ""))
            sales = row.get("sales", row.get("销量", 0))
            if raw_brand and sales:
                # 标准化品牌名称
                brand = normalize_brand(raw_brand)
                brand_sales[brand] = brand_sales.get(brand, 0) + sales
            if model:
                model_set.add(model)

        # 排序并取Top 10
        sorted_brands = sorted(brand_sales.items(), key=lambda x: x[1], reverse=True)[:10]
        market_data["brand_ranking"] = [
            {"brand": brand, "sales": sales, "rank": i + 1}
            for i, (brand, sales) in enumerate(sorted_brands)
        ]

        # 添加车型详情（去重）
        seen_models = set()
        unique_competitors = []
        for row in sql_results:
            model = row.get("model", row.get("通用名称", ""))
            if model and model not in seen_models:
                seen_models.add(model)
                unique_competitors.append({
                    "brand": normalize_brand(row.get("brand", row.get("企业名称", ""))),
                    "model": model,
                    "sales": row.get("sales", 0),
                    "price": row.get("price", row.get("price_yuan", 0)),
                    "has_price": row.get("has_price", False)
                })
        market_data["competitors"] = unique_competitors[:20]

        # 计算总销量和统计
        total_sales = sum(r.get("sales", 0) for r in sql_results if r.get("sales"))
        market_data["market_overview"] = market_data.get("market_overview", {})
        market_data["market_overview"]["total_sales"] = total_sales
        market_data["market_overview"]["brand_count"] = len(brand_sales)
        market_data["market_overview"]["model_count"] = len(model_set)
        if price_range_text:
            market_data["market_overview"]["price_range"] = price_range_text

    return market_data


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

        mo = market_data.get("market_overview", {})
        if mo:
            lines.append(format_market_data(mo))

        # 品牌排名（使用聚合后的 brand_ranking）
        brands = market_data.get("brand_ranking", [])
        if brands:
            total = mo.get("total_sales", 0) if mo else 0
            lines.append("\n### 品牌排名 (Top 10)\n")
            lines.append(format_brand_ranking(brands, total))

        # 车型详情（使用 competitors）
        competitors = market_data.get("competitors", [])
        if competitors:
            lines.append("\n### 车型详情\n")
            lines.append(format_competitors(competitors))

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
            brand_result=params.get("brand_result"),
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
