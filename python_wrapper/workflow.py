# -*- coding: utf-8 -*-
"""
Market Analysis Workflow Module

Integrates Stage connectors + Skill caller for complete market analysis flow
"""

import asyncio
import time
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass

from stage_connectors import (
    build_stage2_input, build_stage3_input, build_report_input,
    Stage2Input, Stage3Input, ReportInput
)
from skill_caller import get_caller


@dataclass
class WorkflowResult:
    """Workflow execution result"""
    success: bool
    question: str
    intent_type: str
    execution_time: float

    # Stage data
    intent_result: Dict = None
    vector_data: Dict = None
    sql_data: Dict = None
    pest_result: Dict = None
    porter_result: Dict = None
    swot_result: Dict = None
    fourp_result: Dict = None
    brand_result: Dict = None
    report: Dict = None

    # Error info
    error: str = None
    stage_errors: Dict = None

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "question": self.question,
            "intent_type": self.intent_type,
            "execution_time": self.execution_time,
            "intent_result": self.intent_result,
            "vector_data": self.vector_data,
            "sql_data": self.sql_data,
            "pest_result": self.pest_result,
            "porter_result": self.porter_result,
            "swot_result": self.swot_result,
            "fourp_result": self.fourp_result,
            "brand_result": self.brand_result,
            "report": self.report,
            "error": self.error,
            "stage_errors": self.stage_errors
        }


class MarketAnalysisWorkflow:
    """Market Analysis Workflow"""

    def __init__(self):
        self.caller = get_caller()
        self.stage_errors = {}

    def _generate_stage1_summary(self, intent_result: Dict) -> str:
        """生成 Stage1 意图识别的摘要文本"""
        lines = []
        lines.append(f"✓ 完成")
        lines.append("")
        lines.append("**意图识别结果：**")
        lines.append(f"- 分析类型：{intent_result.get('intent_type', '未知')}")
        lines.append(f"- 置信度：{intent_result.get('confidence', 0):.0%}")

        keywords = intent_result.get('keywords', [])
        if keywords:
            lines.append(f"- 关键词：{', '.join(keywords[:5])}")

        brands = intent_result.get('brands_mentioned', [])
        if brands:
            lines.append(f"- 涉及品牌：{', '.join(brands[:3])}")

        return "\n".join(lines)

    def _generate_stage2_summary(self, vector_data: Dict, sql_data: Dict) -> str:
        """生成 Stage2 数据检索的摘要文本"""
        lines = []
        lines.append(f"✓ 完成")
        lines.append("")
        lines.append("**数据检索结果：**")

        # SQL 数据
        if sql_data.get('success') and sql_data.get('results'):
            results = sql_data.get('results', [])
            if results:
                r = results[0]
                total_sales = r.get('total_sales', 0)
                brand_count = r.get('brand_count', 0)
                model_count = r.get('model_count', 0)
                lines.append(f"- SQL查询：{brand_count}个品牌，{model_count}个车型")
                if total_sales:
                    lines.append(f"- 总销量：{total_sales:,}辆")
        elif sql_data.get('error'):
            lines.append(f"- SQL查询：失败 - {sql_data.get('error', '未知错误')}")

        # 向量数据
        vector_results = vector_data.get('results', []) if vector_data else []
        if vector_data.get('success') and vector_results:
            lines.append(f"- 向量检索：{len(vector_results)}条相关文档")
        elif vector_data.get('error'):
            lines.append(f"- 向量检索：失败")

        return "\n".join(lines)

    def _generate_stage3_summary(self, pest_result: Dict, porter_result: Dict, swot_result: Dict, fourp_result: Dict) -> str:
        """生成 Stage3 战略分析的摘要文本"""
        lines = []
        lines.append(f"✓ 完成")
        lines.append("")
        lines.append("**战略分析结果：**")

        # PEST 摘要
        if pest_result and pest_result.get('success'):
            lines.append("")
            lines.append("**PEST分析：**")
            summary = pest_result.get('summary', {})
            sentiment = summary.get('overall_sentiment', '未知')
            lines.append(f"- 整体态势：{sentiment}")

            opportunities = summary.get('key_opportunities', [])
            if opportunities:
                lines.append(f"- 主要机会：{opportunities[0][:50]}...")

            threats = summary.get('key_threats', [])
            if threats:
                lines.append(f"- 主要威胁：{threats[0][:50]}...")

        # Porter 摘要
        if porter_result and porter_result.get('success'):
            lines.append("")
            lines.append("**波特五力分析：**")
            porter_summary = porter_result.get('summary', {})
            score = porter_summary.get('overall_score', 0)
            attractiveness = porter_summary.get('industry_attractiveness', '未知')
            lines.append(f"- 行业吸引力：{attractiveness}")
            lines.append(f"- 综合评分：{score}/10")

        # SWOT 摘要（如果有）
        if swot_result and swot_result.get('success'):
            lines.append("")
            lines.append("**SWOT分析：** ✓ 已完成")

        # 4P 摘要（如果有）
        if fourp_result and fourp_result.get('success'):
            lines.append("")
            lines.append("**4P分析：** ✓ 已完成")

        return "\n".join(lines)

    async def run(self, question: str, progress_callback: Callable = None) -> WorkflowResult:
        """Execute complete workflow"""
        start_time = time.time()
        self.stage_errors = {}

        try:
            # Stage 1: Intent recognition (mandatory)
            if progress_callback:
                await progress_callback("stage1", "running", None)

            intent_result = await self._stage1_intent(question)

            # 生成 Stage1 摘要
            intent_type = intent_result.get('intent_type')
            stage1_summary = self._generate_stage1_summary(intent_result) if intent_type else f"✗ 失败：{intent_result.get('error', '未知错误')}"

            if progress_callback:
                await progress_callback("stage1", "done", {
                    "data": intent_result,
                    "summary": stage1_summary
                })

            if not intent_result.get("intent_type"):
                raise Exception(f"Intent recognition failed: {intent_result.get('error', 'Unknown error')}")

            # Stage 2: Data retrieval (parallel)
            if progress_callback:
                await progress_callback("stage2", "running", None)

            stage2_input = build_stage2_input(intent_result, question)
            vector_data, sql_data = await self._stage2_retrieval(stage2_input)

            # 生成 Stage2 摘要
            stage2_summary = self._generate_stage2_summary(vector_data, sql_data)

            if progress_callback:
                await progress_callback("stage2", "done", {
                    "data": {
                        "vector": vector_data,
                        "sql": sql_data
                    },
                    "summary": stage2_summary
                })

            # Stage 3/4: Strategic analysis
            if progress_callback:
                await progress_callback("stage3", "running", None)

            stage3_input = build_stage3_input(intent_result, sql_data, vector_data)
            analysis_results = await self._stage3_analysis(stage3_input, sql_data, vector_data)

            pest_result = analysis_results.get("pest")
            porter_result = analysis_results.get("porter")
            swot_result = analysis_results.get("swot")
            fourp_result = analysis_results.get("fourp")

            # 生成 Stage3 摘要
            stage3_summary = self._generate_stage3_summary(pest_result, porter_result, swot_result, fourp_result)

            if progress_callback:
                await progress_callback("stage3", "done", {
                    "data": {
                        "pest": pest_result,
                        "porter": porter_result,
                        "swot": swot_result,
                        "fourp": fourp_result
                    },
                    "summary": stage3_summary
                })

            # Stage 4: Brand analysis
            if progress_callback:
                await progress_callback("stage4", "running", None)

            # 获取品牌名称
            brand = intent_result.get("brands_mentioned", [None])[0] if intent_result.get("brands_mentioned") else None

            # 调用品牌分析skill
            brand_result = None
            if brand:
                try:
                    brand_result = await self.caller.brand_analysis(
                        brand=brand,
                        sql_data=sql_data,
                        vector_data=vector_data,
                        question=question  # 传入原始问题用于品牌提取
                    )
                except Exception as e:
                    self.stage_errors["stage4"] = str(e)
                    brand_result = {"success": False, "error": str(e)}

            # 生成品牌分析摘要
            if brand_result and brand_result.get("success"):
                brand_summary = brand_result.get("summary", f"品牌 {brand} 分析完成")
            else:
                brand_summary = f"品牌 {brand or '未知'} 分析完成"

            if progress_callback:
                await progress_callback("stage4", "done", {
                    "data": brand_result,
                    "summary": brand_summary
                })

            # Stage 5: Report generation
            if progress_callback:
                await progress_callback("stage5", "running", None)

            report = await self._stage5_report(
                intent_result, vector_data, sql_data,
                pest_result, porter_result, swot_result, fourp_result, brand_result
            )

            if progress_callback:
                await progress_callback("stage5", "done", report)

            execution_time = time.time() - start_time

            return WorkflowResult(
                success=True,
                question=question,
                intent_type=intent_result.get("intent_type", "Comprehensive"),
                execution_time=execution_time,
                intent_result=intent_result,
                vector_data=vector_data,
                sql_data=sql_data,
                pest_result=pest_result,
                porter_result=porter_result,
                swot_result=swot_result,
                fourp_result=fourp_result,
                brand_result=brand_result,
                report=report,
                stage_errors=self.stage_errors
            )

        except Exception as e:
            execution_time = time.time() - start_time
            return WorkflowResult(
                success=False,
                question=question,
                intent_type="Unknown",
                execution_time=execution_time,
                error=str(e),
                stage_errors=self.stage_errors
            )

    async def _stage1_intent(self, question: str) -> Dict[str, Any]:
        """Stage 1: Intent recognition"""
        try:
            result = await self.caller.classify_intent(question)
            result["question"] = question
            return result
        except Exception as e:
            self.stage_errors["stage1"] = str(e)
            return {"success": False, "error": str(e)}

    async def _stage2_retrieval(self, stage2_input: Stage2Input) -> tuple:
        """Stage 2: Data retrieval (vector + SQL parallel)"""
        tasks = []

        # Vector search (conditional)
        if stage2_input.run_vector:
            tasks.append(("vector", self.caller.vector_search(
                query=stage2_input.vector_query,
                top_k=6,
                brand=stage2_input.vector_brand_filter,
                search_mode=stage2_input.search_mode
            )))
        else:
            tasks.append(("vector", asyncio.sleep(0, result={"success": True, "results": []})))

        # SQL query (always)
        # 直接传原始问题给 nl2sql，让它自己解析
        tasks.append(("sql", self.caller.sql_query(
            question=stage2_input.original_question or stage2_input.sql_question,
            execute=True
        )))

        # Parallel execution
        results = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)

        vector_data = results[0] if not isinstance(results[0], Exception) else {
            "success": False, "error": str(results[0]), "results": []
        }
        sql_data = results[1] if not isinstance(results[1], Exception) else {
            "success": False, "error": str(results[1]), "results": []
        }

        if isinstance(results[0], Exception):
            self.stage_errors["stage2_vector"] = str(results[0])
        if isinstance(results[1], Exception):
            self.stage_errors["stage2_sql"] = str(results[1])

        return vector_data, sql_data

    async def _stage3_analysis(self, stage3_input: Stage3Input, sql_data: Dict = None, vector_data: Dict = None) -> Dict[str, Any]:
        """Stage 3/4: Strategic analysis"""
        output = {}

        # PEST and Porter MUST run sequentially to avoid import deadlock
        # because they both import from the same automotive-strategy-analysis skill
        pest_task = self.caller.pest_analysis(
            brand=stage3_input.brand,
            segment=stage3_input.segment,
            sql_data=sql_data,
            vector_data=vector_data
        )
        pest_result = await pest_task
        if isinstance(pest_result, Exception):
            output["pest"] = {"success": False, "error": str(pest_result)}
            self.stage_errors["stage3_pest"] = str(pest_result)
        else:
            output["pest"] = pest_result

        porter_task = self.caller.porter_analysis(
            brand=stage3_input.brand,
            segment=stage3_input.segment,
            sql_data=sql_data,
            vector_data=vector_data
        )
        porter_result = await porter_task
        if isinstance(porter_result, Exception):
            output["porter"] = {"success": False, "error": str(porter_result)}
            self.stage_errors["stage3_porter"] = str(porter_result)
        else:
            output["porter"] = porter_result

        # SWOT and 4P can run in parallel with each other (different modules)
        swot_task = None
        fourp_task = None

        if "swot" in stage3_input.frameworks and stage3_input.brand:
            swot_task = self.caller.swot_analysis(brand=stage3_input.brand, sql_data=sql_data)
        else:
            swot_task = asyncio.sleep(0, result=None)

        if "fourp" in stage3_input.frameworks and stage3_input.brand:
            fourp_task = self.caller.fourp_analysis(brand=stage3_input.brand, sql_data=sql_data)
        else:
            fourp_task = asyncio.sleep(0, result=None)

        swot_result, fourp_result = await asyncio.gather(swot_task, fourp_task)

        if isinstance(swot_result, Exception):
            output["swot"] = {"success": False, "error": str(swot_result)}
            self.stage_errors["stage3_swot"] = str(swot_result)
        else:
            output["swot"] = swot_result if swot_result is not None else None

        if isinstance(fourp_result, Exception):
            output["fourp"] = {"success": False, "error": str(fourp_result)}
            self.stage_errors["stage3_fourp"] = str(fourp_result)
        else:
            output["fourp"] = fourp_result if fourp_result is not None else None

        return output

    async def _stage5_report(
        self,
        intent_result: Dict,
        vector_data: Dict,
        sql_data: Dict,
        pest_result: Dict,
        porter_result: Dict,
        swot_result: Dict,
        fourp_result: Dict,
        brand_result: Dict = None
    ) -> Dict[str, Any]:
        """Stage 5: Report generation"""
        try:
            return await self.caller.generate_report(
                question=intent_result.get("question", ""),
                intent_type=intent_result.get("intent_type", "Comprehensive"),
                pest_result=pest_result,
                porter_result=porter_result,
                swot_result=swot_result,
                fourp_result=fourp_result,
                brand_result=brand_result,
                vector_results=vector_data.get("results", []),
                sql_results=sql_data.get("results", [])
            )
        except Exception as e:
            self.stage_errors["stage5"] = str(e)
            return {
                "success": False,
                "error": str(e),
                "markdown": "# Report generation failed\n\n" + str(e)
            }


# Convenience function
async def run_market_analysis(
    question: str,
    progress_callback: Callable = None
) -> WorkflowResult:
    """Run market analysis workflow"""
    workflow = MarketAnalysisWorkflow()
    return await workflow.run(question, progress_callback)


# Test
if __name__ == "__main__":
    import urllib.request
    import json

    async def test():
        print("=" * 60)
        print("Market Analysis Workflow Test")
        print("=" * 60)

        def progress(stage, status, data):
            print(f"[{stage}] {status}")

        result = await run_market_analysis(
            "Analyze BYD market strategy",
            progress_callback=progress
        )

        print("\n" + "=" * 60)
        print("Execution Result")
        print("=" * 60)
        print(f"Success: {result.success}")
        print(f"Intent Type: {result.intent_type}")
        print(f"Execution Time: {result.execution_time:.2f}s")

        if result.report:
            print("\nReport preview:")
            print(result.report.get("markdown", "")[:500])

        if result.stage_errors:
            print("\nStage Errors:")
            for stage, error in result.stage_errors.items():
                print(f"  {stage}: {error}")

    asyncio.run(test())