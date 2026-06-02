"""
automotive-strategy-analysis skill
汽车市场战略分析技能 - 封装RAG引擎中的四大分析框架

提供：PEST分析、波特五力、SWOT分析、4P营销组合
"""

import sys
import os
import json
import re
from typing import Dict, Any, List, Optional

# 添加RAG引擎路径
RAG_ENGINE_PATH = r"E:\AI\data\envs\car_agent_env\ai-decision\rag-engine"
if RAG_ENGINE_PATH not in sys.path:
    sys.path.insert(0, RAG_ENGINE_PATH)


def load_dotenv():
    """加载环境变量"""
    env_path = os.path.join(os.path.dirname(RAG_ENGINE_PATH), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()


load_dotenv()


def pest_analysis(brand: str = None, segment: str = "乘用车") -> Dict[str, Any]:
    """
    PEST宏观环境分析

    Args:
        brand: 品牌名称（可选）
        segment: 市场细分

    Returns:
        PEST分析结果
    """
    try:
        from market_strategy.tools.analysis_frameworks.pest_analysis import PESTAnalyzer

        analyzer = PESTAnalyzer(market=segment or "乘用车")
        result = analyzer.full_analysis()

        return {
            "success": True,
            "intent_type": "pest_analysis",
            "data": result,
            "summary": result.get("summary", {})
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "intent_type": "pest_analysis"
        }


def porter_analysis(brand: str = None, segment: str = "乘用车") -> Dict[str, Any]:
    """
    波特五力分析

    Args:
        brand: 品牌名称（可选）
        segment: 市场细分

    Returns:
        波特五力分析结果
    """
    try:
        from market_strategy.tools.analysis_frameworks.porter_analysis import PorterAnalyzer

        analyzer = PorterAnalyzer(segment=segment or "乘用车")

        # 尝试加载市场数据
        market_data = None
        try:
            from market_strategy.knowledge_base import MarketKnowledgeBase
            kb = MarketKnowledgeBase()
            brands = kb.get_sales_by_brand(top_n=50)
            market_data = {'brand_ranking': brands}
            kb.close()
        except Exception:
            pass

        result = analyzer.full_analysis(market_data)

        return {
            "success": True,
            "intent_type": "porter_analysis",
            "data": result,
            "summary": result.get("summary", {})
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "intent_type": "porter_analysis"
        }


def swot_analysis(brand: str, segment: str = None) -> Dict[str, Any]:
    """
    SWOT战略分析

    Args:
        brand: 品牌名称（必填）
        segment: 市场细分（可选）

    Returns:
        SWOT分析结果
    """
    try:
        from market_strategy.tools.analysis_frameworks.swot_analysis import SWOTAnalyzer

        analyzer = SWOTAnalyzer(brand=brand)

        # 尝试加载市场数据
        try:
            from market_strategy.knowledge_base import MarketKnowledgeBase
            kb = MarketKnowledgeBase()
            brands = kb.get_sales_by_brand(top_n=50)
            analyzer.market_data = {'brand_ranking': brands}
            kb.close()
        except Exception:
            pass

        result = analyzer.generate_full_analysis()

        return {
            "success": True,
            "intent_type": "swot_analysis",
            "data": result,
            "summary": result.get("summary", {})
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "intent_type": "swot_analysis"
        }


def fourp_analysis(brand: str, segment: str = None) -> Dict[str, Any]:
    """
    4P营销组合分析

    Args:
        brand: 品牌名称（必填）
        segment: 市场细分（可选）

    Returns:
        4P分析结果
    """
    try:
        from market_strategy.tools.analysis_frameworks.marketing_analysis import MarketingAnalyzer

        analyzer = MarketingAnalyzer(brand=brand, segment=segment)
        result = analyzer.full_analysis()

        return {
            "success": True,
            "intent_type": "fourp_analysis",
            "data": result,
            "summary": result.get("summary", {})
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "intent_type": "fourp_analysis"
        }


def comprehensive_analysis(
    brand: str = None,
    segment: str = "乘用车",
    question: str = None
) -> Dict[str, Any]:
    """
    综合战略分析 - 包含四大框架

    Args:
        brand: 品牌名称（可选）
        segment: 市场细分
        question: 用户问题（用于提取品牌信息）

    Returns:
        综合分析结果
    """
    try:
        # 如果没有提供brand，尝试从question中提取
        if not brand and question:
            brand = extract_brand_from_question(question)

        # 执行四大框架分析
        pest_result = pest_analysis(brand, segment)
        porter_result = porter_analysis(brand, segment)

        swot_result = {}
        if brand:
            swot_result = swot_analysis(brand, segment)

        fourp_result = {}
        if brand:
            fourp_result = fourp_analysis(brand, segment)

        # 生成综合摘要
        summary = {
            "market_sentiment": pest_result.get("data", {}).get("summary", {}).get("overall_sentiment", "中性"),
            "industry_attractiveness": porter_result.get("data", {}).get("summary", {}).get("industry_attractiveness", "中等吸引力"),
            "strategic_posture": swot_result.get("data", {}).get("summary", {}).get("strategic_posture", "平衡型")
        }

        return {
            "success": True,
            "intent_type": "comprehensive_analysis",
            "brand": brand,
            "segment": segment,
            "pest": pest_result.get("data", {}),
            "porter": porter_result.get("data", {}),
            "swot": swot_result.get("data", {}),
            "fourp": fourp_result.get("data", {}),
            "summary": summary
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "intent_type": "comprehensive_analysis"
        }


def extract_brand_from_question(question: str) -> Optional[str]:
    """从问题中提取品牌名称"""
    # 常见汽车品牌
    brands = [
        "比亚迪", "特斯拉", "蔚来", "小鹏", "理想",
        "问界", "小米汽车", "极氪", "零跑", "哪吒",
        "长安", "吉利", "长城", "奇瑞", "上汽",
        "广汽", "一汽", "东风", "宝马", "奔驰",
        "奥迪", "大众", "丰田", "本田", "日产"
    ]

    for brand in brands:
        if brand in question:
            return brand

    return None


def analyze(
    question: str,
    brand: str = None,
    segment: str = "乘用车",
    framework: str = "all"
) -> Dict[str, Any]:
    """
    主分析入口

    Args:
        question: 用户问题
        brand: 品牌名称（可选）
        segment: 市场细分
        framework: 分析框架 (all/pest/porter/swot/fourp)

    Returns:
        分析结果
    """
    # 提取品牌
    if not brand:
        brand = extract_brand_from_question(question)

    if framework == "pest":
        return pest_analysis(brand, segment)
    elif framework == "porter":
        return porter_analysis(brand, segment)
    elif framework == "swot":
        if not brand:
            return {"success": False, "error": "SWOT分析需要指定品牌", "intent_type": "swot_analysis"}
        return swot_analysis(brand, segment)
    elif framework == "fourp":
        if not brand:
            return {"success": False, "error": "4P分析需要指定品牌", "intent_type": "fourp_analysis"}
        return fourp_analysis(brand, segment)
    else:
        return comprehensive_analysis(brand, segment, question)


# OpenClaw skill 接口
def skill_main(action: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    OpenClaw skill 主入口

    Args:
        action: 操作类型 (analyze/pest/porter/swot/fourp/comprehensive)
        params: 参数字典

    Returns:
        标准化结果
    """
    if params is None:
        params = {}

    question = params.get("question", params.get("query", ""))
    brand = params.get("brand")
    segment = params.get("segment", "乘用车")
    framework = params.get("framework", "all")

    if action == "analyze":
        return analyze(question, brand, segment, framework)
    elif action == "pest":
        return pest_analysis(brand, segment)
    elif action == "porter":
        return porter_analysis(brand, segment)
    elif action == "swot":
        if not brand:
            return {"success": False, "error": "需要品牌参数"}
        return swot_analysis(brand, segment)
    elif action == "fourp":
        if not brand:
            return {"success": False, "error": "需要品牌参数"}
        return fourp_analysis(brand, segment)
    elif action == "comprehensive":
        return comprehensive_analysis(brand, segment, question)
    else:
        return {"success": False, "error": f"未知操作: {action}"}


if __name__ == "__main__":
    # 命令行测试
    import argparse

    parser = argparse.ArgumentParser(description="汽车市场战略分析")
    parser.add_argument("--action", default="comprehensive", choices=["pest", "porter", "swot", "fourp", "comprehensive"])
    parser.add_argument("--brand", default=None)
    parser.add_argument("--segment", default="乘用车")
    parser.add_argument("--question", default="分析比亚迪的市场战略")

    args = parser.parse_args()

    result = skill_main(args.action, {
        "question": args.question,
        "brand": args.brand,
        "segment": args.segment
    })

    print(json.dumps(result, ensure_ascii=False, indent=2))
