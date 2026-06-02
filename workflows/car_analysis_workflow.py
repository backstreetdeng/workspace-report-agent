"""
汽车市场战略分析 - 统一工作流 v2.0
集成 HybridMarketAgent（最新混合检索引擎）+ 四大框架分析

架构：
┌────────────────────────────────────────────────────────────────────┐
│                    car_analysis_workflow.py                          │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                  统一入口：run_analysis(query)                 │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              ↓                                        │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              HybridMarketAgent (最新增强版)                    │   │
│  │  - 自动判断数据源（结构化/RAG/混合）                           │   │
│  │  - 混合检索（向量+关键词+RRF融合）                           │   │
│  │  - 优雅降级（无RAG时纯结构化分析）                           │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              ↓                                        │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              四大框架分析层                                    │   │
│  │  - PEST宏观分析                                              │   │
│  │  - 波特五力分析                                              │   │
│  │  - SWOT战略分析（品牌分析时）                                 │   │
│  │  - 4P营销组合（品牌分析时）                                   │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              ↓                                        │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              报告生成层                                        │   │
│  │  - Markdown格式输出                                          │   │
│  │  - 执行摘要 + 详细分析 + 参考资料                             │   │
│  └──────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────┘
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

# 添加skill路径
SKILLS_PATH = r"C:\Users\11489\.openclaw\workspace-market\skills"
if SKILLS_PATH not in sys.path:
    sys.path.insert(0, SKILLS_PATH)


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


class CarAnalysisWorkflow:
    """汽车市场分析统一工作流 v2.0 - 集成 HybridMarketAgent"""

    # Skill路径
    SKILLS_BASE = r"C:\Users\11489\.openclaw\workspace-market\skills"

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.results = {}
        self._setup_paths()
        self._init_hybrid_agent()

    def _setup_paths(self):
        """设置模块路径"""
        # 添加各skill路径
        for skill_dir in os.listdir(self.SKILLS_BASE):
            skill_path = os.path.join(self.SKILLS_BASE, skill_dir)
            if os.path.isdir(skill_path) and skill_path not in sys.path:
                sys.path.insert(0, skill_path)

    def _init_hybrid_agent(self):
        """初始化 HybridMarketAgent（最新增强版）"""
        try:
            from market_strategy.hybrid_agent import HybridMarketAgent

            self.hybrid_agent = HybridMarketAgent()
            self.hybrid_agent_available = True
            self.log("AGENT", f"✅ HybridMarketAgent 初始化成功")
            self.log("AGENT", f"   RAG可用: {self.hybrid_agent.rag_available}")
        except Exception as e:
            self.hybrid_agent = None
            self.hybrid_agent_available = False
            print(f"⚠️ HybridMarketAgent 初始化失败: {e}")

    def log(self, stage: str, message: str):
        """日志输出"""
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"[{stage}] {message}")
            print('='*60)

    def run(self, question: str) -> Dict[str, Any]:
        """
        执行完整工作流 v2.0

        Args:
            question: 用户问题

        Returns:
            分析结果
        """
        self.log("START", f"问题: {question}")
        start_time = datetime.now()

        try:
            # ==================== 阶段1: 意图识别 ====================
            self.log("STAGE 1", "意图识别")
            intent_result = self._classify_intent(question)
            self.results["intent"] = intent_result
            self.log("INTENT", f"识别结果: {intent_result.get('intent_type')}, 置信度: {intent_result.get('confidence')}")

            # ==================== 阶段2: HybridAgent 分析 ====================
            self.log("STAGE 2", "HybridAgent 混合分析")

            # 使用 HybridMarketAgent 进行核心分析
            hybrid_result = self._run_hybrid_analysis(question)
            self.results["hybrid"] = hybrid_result

            # ==================== 阶段3: 四大框架分析 ====================
            self.log("STAGE 3", "四大框架分析")

            # PEST分析
            self.log("PEST", "执行PEST宏观分析")
            pest_result = self._analyze_pest()
            self.results["pest"] = pest_result

            # 波特五力
            self.log("PORTER", "执行波特五力分析")
            porter_result = self._analyze_porter()
            self.results["porter"] = porter_result

            # SWOT分析（如果识别到品牌）
            brands_mentioned = intent_result.get("brands_mentioned") or []
            brand = brands_mentioned[0] if brands_mentioned else None
            if brand:
                self.log("SWOT", f"执行SWOT分析 ({brand})")
                swot_result = self._analyze_swot(brand)
                self.results["swot"] = swot_result

                self.log("4P", f"执行4P分析 ({brand})")
                fourp_result = self._analyze_fourp(brand)
                self.results["fourp"] = fourp_result
            else:
                self.log("SWOT", "未识别到具体品牌，跳过SWOT/4P")
                swot_result = None
                fourp_result = None
                self.results["swot"] = None
                self.results["fourp"] = None

            # ==================== 阶段4: 报告生成 ====================
            self.log("STAGE 4", "生成分析报告")
            report_result = self._generate_report(question, intent_result)
            self.results["report"] = report_result

            # 统计耗时
            elapsed = (datetime.now() - start_time).total_seconds()

            return {
                "success": True,
                "question": question,
                "intent": intent_result,
                "hybrid": {
                    "success": hybrid_result.get("success", False),
                    "data_source": hybrid_result.get("data_source", "unknown"),
                    "confidence": hybrid_result.get("confidence", 0),
                    "rag_available": self.hybrid_agent_available and self.hybrid_agent.rag_available if self.hybrid_agent else False
                },
                "analysis": {
                    "pest": pest_result.get("success", False),
                    "porter": porter_result.get("success", False),
                    "swot": swot_result.get("success", False) if swot_result else None,
                    "fourp": fourp_result.get("success", False) if fourp_result else None
                },
                "report": report_result,
                "elapsed_seconds": elapsed
            }

        except Exception as e:
            import traceback
            print(f"工作流执行失败: {e}")
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "question": question
            }

    def _run_hybrid_analysis(self, question: str) -> Dict[str, Any]:
        """
        使用 HybridMarketAgent 进行混合分析

        这使用了最新版的混合检索引擎：
        - 自动判断数据源
        - 混合检索（向量+关键词+RRF）
        - 优雅降级
        """
        if not self.hybrid_agent:
            return {"success": False, "error": "HybridAgent未初始化"}

        try:
            from market_strategy.schemas import MarketInput

            # 构建 MarketInput
            market_input = MarketInput(
                query=question,
                analysis_type=None,
                time_range="最近12个月"
            )

            # 调用 HybridMarketAgent.analyze()
            result = self.hybrid_agent.analyze(market_input)

            return {
                "success": result.success,
                "error": getattr(result, 'error', None),
                "data_source": getattr(result, 'data_source', 'unknown'),
                "confidence": result.confidence,
                "market_overview": {
                    "scale": result.market_overview.scale if result.market_overview else None,
                    "growth_rate": result.market_overview.growth_rate if result.market_overview else None,
                    "trend": result.market_overview.trend if result.market_overview else None,
                    "concentration": result.market_overview.concentration if result.market_overview else None
                },
                "competitors": [
                    {
                        "name": c.name,
                        "brand": c.brand,
                        "market_share": c.market_share,
                        "sales_volume": c.sales_volume
                    }
                    for c in result.competitors[:10]
                ] if result.competitors else [],
                "opportunities": [
                    {
                        "item": o.item,
                        "scale": o.scale,
                        "confidence": o.confidence
                    }
                    for o in result.opportunities
                ] if result.opportunities else [],
                "suggestions": result.suggestions or []
            }

        except Exception as e:
            print(f"HybridAgent分析失败: {e}")
            return {"success": False, "error": str(e)}

    def _classify_intent(self, question: str) -> Dict[str, Any]:
        """意图识别"""
        try:
            import intent_classifier
            classifier = intent_classifier.IntentClassifier()
            result = classifier.classify(question)
            return {
                "success": True,
                "intent_type": result.intent_type,
                "confidence": result.confidence,
                "keywords": result.keywords,
                "dimensions": result.dimensions,
                "need_sentiment": result.need_sentiment,
                "brands_mentioned": result.brands_mentioned,
                "price_range": result.price_range,
                "question": question
            }
        except Exception as e:
            print(f"意图识别失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "intent_type": "综合分析",
                "confidence": 0.5,
                "brands_mentioned": [],
                "question": question
            }

    def _analyze_pest(self) -> Dict[str, Any]:
        """PEST分析"""
        try:
            sys.path.insert(0, os.path.join(self.SKILLS_BASE, "automotive-strategy-analysis"))
            import strategy_analysis
            result = strategy_analysis.pest_analysis()
            return result
        except Exception as e:
            print(f"PEST分析失败: {e}")
            return {"success": False, "error": str(e)}

    def _analyze_porter(self) -> Dict[str, Any]:
        """波特五力分析"""
        try:
            sys.path.insert(0, os.path.join(self.SKILLS_BASE, "automotive-strategy-analysis"))
            import strategy_analysis
            result = strategy_analysis.porter_analysis()
            return result
        except Exception as e:
            print(f"波特五力分析失败: {e}")
            return {"success": False, "error": str(e)}

    def _analyze_swot(self, brand: str) -> Dict[str, Any]:
        """SWOT分析"""
        try:
            sys.path.insert(0, os.path.join(self.SKILLS_BASE, "automotive-strategy-analysis"))
            import strategy_analysis
            result = strategy_analysis.swot_analysis(brand)
            return result
        except Exception as e:
            print(f"SWOT分析失败: {e}")
            return {"success": False, "error": str(e)}

    def _analyze_fourp(self, brand: str) -> Dict[str, Any]:
        """4P分析"""
        try:
            sys.path.insert(0, os.path.join(self.SKILLS_BASE, "automotive-strategy-analysis"))
            import strategy_analysis
            result = strategy_analysis.fourp_analysis(brand)
            return result
        except Exception as e:
            print(f"4P分析失败: {e}")
            return {"success": False, "error": str(e)}

    def _generate_report(self, question: str, intent_result: Dict) -> Dict[str, Any]:
        """生成报告"""
        try:
            sys.path.insert(0, os.path.join(self.SKILLS_BASE, "report-generator"))
            import report_generator

            result = report_generator.generate_report(
                question=question,
                intent_type=intent_result.get("intent_type", "综合分析"),
                market_data=self.results.get("hybrid", {}),
                pest_result=self.results.get("pest", {}),
                porter_result=self.results.get("porter", {}),
                swot_result=self.results.get("swot", {}),
                fourp_result=self.results.get("fourp", {})
            )
            return result
        except Exception as e:
            print(f"报告生成失败: {e}")
            return {"success": False, "error": str(e)}


def run_analysis(question: str, verbose: bool = True) -> Dict[str, Any]:
    """
    便捷函数：执行汽车市场分析

    Args:
        question: 用户问题
        verbose: 是否输出详细信息

    Returns:
        分析结果
    """
    workflow = CarAnalysisWorkflow(verbose=verbose)
    return workflow.run(question)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="汽车市场战略分析工作流 v2.0")
    parser.add_argument("--question", "-q", default="分析比亚迪的市场战略")
    parser.add_argument("--verbose", "-v", action="store_true", default=True)
    parser.add_argument("--output", "-o", default=None, help="输出JSON文件路径")

    args = parser.parse_args()

    print(f"\n{'#'*70}")
    print(f"# 汽车市场战略分析智能体 v2.0 (集成 HybridMarketAgent)")
    print(f"# 问题: {args.question}")
    print(f"{'#'*70}\n")

    result = run_analysis(args.question, verbose=args.verbose)

    # 输出报告
    if result.get("success"):
        print(f"\n{'='*70}")
        print("分析报告")
        print('='*70)
        print(result.get("report", {}).get("markdown", ""))

        # 输出 HybridAgent 状态
        hybrid_info = result.get("hybrid", {})
        print(f"\n{'='*70}")
        print("HybridAgent 状态")
        print('='*70)
        print(f"RAG可用: {hybrid_info.get('rag_available', False)}")
        print(f"数据源: {hybrid_info.get('data_source', 'unknown')}")
        print(f"置信度: {hybrid_info.get('confidence', 0):.2f}")
    else:
        print(f"\n❌ 分析失败: {result.get('error')}")

    # 保存JSON
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n📁 结果已保存至: {args.output}")

    print(f"\n⏱️ 耗时: {result.get('elapsed_seconds', 0):.2f}秒")
