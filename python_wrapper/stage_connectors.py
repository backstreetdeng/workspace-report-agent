"""
Stage 衔接器 - 统一管理 Stage 间数据流转

根据 share/stage-connector-design.md 设计实现
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import re


# ==================== 常量定义 ====================

INTENT_STRATEGY = {
    "时机判断": {
        "run_vector": True, "search_mode": "hybrid",
        "sql_query_type": "market_overview", "limit": 20,
        "reason": "需要市场数据+舆情综合判断"
    },
    "趋势分析": {
        "run_vector": True, "search_mode": "hybrid",
        "sql_query_type": "sales_trend", "limit": 50,
        "reason": "需要趋势数据+行业洞察"
    },
    "画像分析": {
        "run_vector": False, "search_mode": "hybrid",
        "sql_query_type": "segment_distribution", "limit": 30,
        "reason": "主要需要结构化细分数据"
    },
    "竞品分析": {
        "run_vector": True, "search_mode": "keyword",
        "sql_query_type": "brand_comparison", "limit": 10,
        "reason": "需要精确对比+品牌资料"
    },
    "机会识别": {
        "run_vector": True, "search_mode": "hybrid",
        "sql_query_type": "sales_by_brand", "limit": 20,
        "reason": "需要市场空白+行业机会"
    },
    "政策解读": {
        "run_vector": True, "search_mode": "keyword",
        "sql_query_type": "market_overview", "limit": 10,
        "reason": "需要精准政策文件"
    },
    "综合分析": {
        "run_vector": True, "search_mode": "hybrid",
        "sql_query_type": "market_overview", "limit": 20,
        "reason": "全面综合分析"
    }
}

# 噪音词
NOISE_WORDS = {
    "分析", "研究", "如何", "怎么样", "什么", "哪些",
    "趋势", "走势", "前景", "机会", "竞争", "对比",
    "用户", "政策", "补贴"
}

# 汽车品牌关键词：自主传统+自主新势力+主流合资+进口豪华全品类
BRAND_KEYWORDS = {
    # 【一、国产传统自主品牌（大厂全系）】
    "比亚迪", "腾势", "仰望", "方程豹",
    "吉利", "领克", "银河",
    "长城", "哈弗", "魏牌", "坦克", "欧拉",
    "长安", "深蓝", "阿维塔", "启源",
    "奇瑞", "星途", "捷途", "iCAR",
    "红旗", "奔腾",
    "广汽传祺", "埃安", "昊铂",
    "荣威", "名爵", "智己", "飞凡",
    "五菱", "宝骏",
    "岚图", "猛士", "东风奕派", "东风风行",
    "北京汽车", "北京越野", "江淮",

    # 【二、国产新能源新势力（热门在售）】
    "蔚来", "小鹏", "理想", "问界",
    "小米", "极氪", "零跑", "哪吒",
    "合众", "远航", "极狐",

    # 【三、主流合资品牌（国内落地量产主力）】
    "大众", "丰田", "本田", "日产", "马自达",
    "别克", "雪佛兰", "福特", "现代", "起亚",

    # 【四、进口/豪华品牌（国内常态化在售）】
    "宝马", "奔驰", "奥迪",
    "雷克萨斯", "英菲尼迪", "凯迪拉克", "沃尔沃",
    "保时捷", "林肯", "路虎", "捷豹", "斯巴鲁",
    "特斯拉"
}

# 技术类型映射
TECH_MAPPING = {
    "纯电": "纯电动", "电动车": "纯电动", "EV": "纯电动",
    "插混": "插电式混合动力", "PHEV": "插电式混合动力",
    "增程": "增程式", "混动": "混合动力", "HEV": "混合动力",
    "燃油": "汽油"
}

# 细分市场映射
SEGMENT_MAP = {
    "SUV": "SUV市场", "轿车": "轿车市场", "MPV": "MPV市场",
    "紧凑型": "紧凑型车市场", "中型": "中型车市场"
}


# ==================== 数据类 ====================

@dataclass
class Stage2Input:
    """Stage 2 向量检索+SQL查询输入"""
    vector_query: str = ""
    vector_brand_filter: Optional[str] = None
    vector_metadata_filter: Dict = field(default_factory=dict)
    search_mode: str = "hybrid"

    original_question: str = ""  # 原始问题，用于直接传给 nl2sql
    sql_question: str = ""
    sql_conditions: List[str] = field(default_factory=list)
    query_type: str = "market_overview"
    limit: int = 20

    run_vector: bool = True
    run_sql: bool = True


@dataclass
class Stage3Input:
    """Stage 3/4 分析框架输入"""
    segment: str = "乘用车市场"
    brand: Optional[str] = None

    market_data: Dict = field(default_factory=dict)
    context_data: List = field(default_factory=list)

    frameworks: List[str] = field(default_factory=lambda: ["pest", "porter"])


@dataclass
class ReportInput:
    """Stage 5 报告生成输入"""
    question: str
    intent_type: str

    intent_result: Dict = field(default_factory=dict)
    vector_data: List = field(default_factory=list)
    sql_data: List = field(default_factory=list)

    pest_data: Optional[Dict] = None
    porter_data: Optional[Dict] = None
    swot_data: Optional[Dict] = None
    fourp_data: Optional[Dict] = None

    data_quality: Dict = field(default_factory=dict)


# ==================== Stage 2 衔接器 ====================

def build_stage2_input(intent_result: Dict, original_question: str = None) -> Stage2Input:
    """根据 intent_result 构建 Stage 2 输入"""

    intent_type = intent_result.get("intent_type", "综合分析")
    dimensions = intent_result.get("dimensions", {})
    brands = intent_result.get("brands_mentioned", [])
    keywords = intent_result.get("keywords", [])
    original_question = original_question or ""

    strategy = INTENT_STRATEGY.get(intent_type, INTENT_STRATEGY["综合分析"])

    # 1. 构建向量检索查询
    semantic_kw = _filter_keywords(keywords)
    for dim in dimensions.values():
        if dim and dim not in semantic_kw:
            semantic_kw.append(dim)

    vector_query = " ".join(semantic_kw) if semantic_kw else original_question

    # 2. 构建向量检索过滤器
    vector_brand = brands[0] if brands else None
    metadata_filter = {k: v for k, v in dimensions.items() if v}

    # 3. 构建SQL条件
    sql_conditions = _build_sql_conditions(brands, dimensions)

    # 4. 构建SQL查询问题
    sql_parts = _build_sql_question(brands, dimensions, intent_type, original_question)

    return Stage2Input(
        vector_query=vector_query,
        vector_brand_filter=vector_brand,
        vector_metadata_filter=metadata_filter,
        search_mode=strategy["search_mode"],
        original_question=original_question,
        sql_question=sql_parts,
        sql_conditions=sql_conditions,
        query_type=strategy["sql_query_type"],
        limit=strategy["limit"],
        run_vector=strategy["run_vector"],
        run_sql=True
    )


def _filter_keywords(keywords: List[str]) -> List[str]:
    """过滤噪音词，保留语义核心词"""
    return [
        kw for kw in keywords
        if kw not in NOISE_WORDS
        and (kw in BRAND_KEYWORDS
             or any(c.isdigit() for c in kw)
             or kw in ["SUV", "轿车", "MPV", "紧凑型", "中型", "纯电", "插混", "增程"])
    ]


def _build_sql_conditions(brands: List[str], dimensions: Dict) -> List[str]:
    """构建SQL WHERE条件"""
    conditions = []

    # 品牌条件
    if brands:
        conditions.append(f'"企业名称" LIKE \'%{brands[0]}%\'')

    # 动力类型条件
    if dimensions.get("动力类型"):
        tech = TECH_MAPPING.get(dimensions["动力类型"])
        if tech:
            conditions.append(f'"技术类型" = \'{tech}\'')

    # 细分市场条件
    if dimensions.get("车型级别"):
        segment = dimensions["车型级别"]
        if not segment.endswith("车"):
            segment += "车"
        conditions.append(f'"乘用车细分" = \'{segment}\'')

    # 价格区间条件
    if dimensions.get("价格区间"):
        conditions.extend(_parse_price_sql(dimensions["价格区间"]))

    return conditions


def _build_sql_question(brands: List[str], dimensions: Dict, intent_type: str, original: str) -> str:
    """构建SQL查询用的问题"""
    parts = []
    if brands:
        parts.append(f"{brands[0]}销量")
    if dimensions.get("价格区间"):
        parts.append(dimensions["价格区间"])
    if "趋势" in intent_type:
        parts.append("趋势")
    return " ".join(parts) if parts else original


def _parse_price_sql(price_str: str) -> List[str]:
    """解析价格区间为SQL条件"""
    conditions = []

    match = re.search(r'(\d+)[到至](\d+)万', price_str)
    if match:
        min_p = int(match.group(1)) * 10000
        max_p = int(match.group(2)) * 10000
        conditions.append(f'"厂商指导价" BETWEEN {min_p} AND {max_p}')
        return conditions

    match = re.search(r'(\d+)万以[下内]', price_str)
    if match:
        conditions.append(f'"厂商指导价" < {int(match.group(1)) * 10000}')
        return conditions

    match = re.search(r'(\d+)万以[上外]', price_str)
    if match:
        conditions.append(f'"厂商指导价" > {int(match.group(1)) * 10000}')
        return conditions

    return conditions


# ==================== Stage 3/4 衔接器 ====================

def build_stage3_input(
    intent_result: Dict,
    sql_data: Dict,
    vector_data: Dict
) -> Stage3Input:
    """构建 Stage 3/4 输入"""

    dimensions = intent_result.get("dimensions", {})
    brands = intent_result.get("brands_mentioned", [])
    intent_type = intent_result.get("intent_type", "综合分析")

    # 推断市场细分
    segment = "乘用车市场"
    if dimensions.get("车型级别"):
        segment = SEGMENT_MAP.get(dimensions["车型级别"], "乘用车市场")

    # 推断品牌
    brand = _infer_brand(intent_result, sql_data)

    # 提取市场数据
    market_data = _extract_market_data(sql_data)

    # 提取上下文
    context_data = _extract_context(vector_data)

    # 选择框架
    frameworks = _select_frameworks(intent_type, brand)

    return Stage3Input(
        segment=segment,
        brand=brand,
        market_data=market_data,
        context_data=context_data,
        frameworks=frameworks
    )


def _infer_brand(intent_result: Dict, sql_data: Dict) -> Optional[str]:
    """推断分析品牌"""
    brands = intent_result.get("brands_mentioned", [])
    if brands:
        return brands[0]

    if sql_data.get("results"):
        for row in sql_data["results"]:
            if "企业名称" in row:
                return row["企业名称"]

    return None


def _extract_market_data(sql_data: Dict) -> Dict:
    """从SQL结果提取市场数据"""
    results = sql_data.get("results", [])
    if not results:
        return {}

    return {
        "brand_ranking": [
            {"brand": r.get("企业名称"), "sales": r.get("sales", 0)}
            for r in results if "企业名称" in r
        ],
        "total_sales": sum(r.get("sales", 0) for r in results if "sales" in r),
        "record_count": len(results)
    }


def _extract_context(vector_data: Dict) -> List[str]:
    """从向量检索结果提取上下文"""
    results = vector_data.get("results", [])
    return [
        r.get("content", "")[:200]
        for r in results
        if r.get("content")
    ][:3]


def _select_frameworks(intent_type: str, brand: Optional[str]) -> List[str]:
    """选择分析框架"""
    frameworks = ["pest", "porter"]

    if brand:
        if intent_type in ["竞品分析", "政策解读", "综合分析"]:
            frameworks.append("swot")
        if intent_type in ["机会识别", "时机判断", "综合分析"]:
            frameworks.append("fourp")

    return frameworks


# ==================== Stage 5 衔接器 ====================

def build_report_input(
    intent_result: Dict,
    vector_results: Dict,
    sql_results: Dict,
    analysis_results: Dict
) -> ReportInput:
    """构建 Stage 5 输入"""

    pest_data = _unwrap_data(analysis_results.get("pest"))
    porter_data = _unwrap_data(analysis_results.get("porter"))
    swot_data = _unwrap_data(analysis_results.get("swot"))
    fourp_data = _unwrap_data(analysis_results.get("fourp"))

    data_quality = {
        "intent": _quality(intent_result),
        "vector": _quality(vector_results),
        "sql": _quality(sql_results),
        "pest": _quality(pest_data),
        "porter": _quality(porter_data),
        "swot": _quality(swot_data),
        "fourp": _quality(fourp_data)
    }

    return ReportInput(
        question=intent_result.get("question", ""),
        intent_type=intent_result.get("intent_type", "综合分析"),
        intent_result=intent_result,
        vector_data=vector_results.get("results", []) if vector_results else [],
        sql_data=sql_results.get("results", []) if sql_results else [],
        pest_data=pest_data,
        porter_data=porter_data,
        swot_data=swot_data,
        fourp_data=fourp_data,
        data_quality=data_quality
    )


def _unwrap_data(data) -> Optional[Dict]:
    """解包 Skill 返回的数据"""
    if not data:
        return None
    if isinstance(data, dict) and data.get("success"):
        return data.get("data")
    return data if isinstance(data, dict) else None


def _quality(data) -> str:
    """评估数据质量"""
    if not data:
        return "missing"
    if isinstance(data, dict) and not data.get("success", True):
        return "error"
    if isinstance(data, (dict, list)) and len(data) == 0:
        return "empty"
    return "good"
