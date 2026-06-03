# -*- coding: utf-8 -*-
"""
FastAPI + SSE 服务

提供 HTTP API 和 SSE 格式响应
"""

import asyncio
import json
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from workflow import MarketAnalysisWorkflow, WorkflowResult


app = FastAPI(
    title="市场战略分析 API",
    version="1.0.0",
    description="汽车市场战略分析 Python Wrapper API"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 工作流实例
workflow = MarketAnalysisWorkflow()


class AnalyzeRequest(BaseModel):
    """分析请求"""
    question: str


@app.get("/")
async def root():
    """API 根路径"""
    return {
        "name": "市场战略分析 API",
        "version": "1.0.0",
        "endpoints": {
            "analyze": "/analyze",
            "analyze_sse": "/analyze_sse",
            "health": "/health",
            "intent_preview": "/intent_preview"
        }
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok"}


@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    """同步分析接口"""
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="question 参数不能为空")

    result = await workflow.run(request.question)

    return {
        "success": result.success,
        "data": result.to_dict(),
        "error": result.error
    }


@app.post("/analyze_sse")
async def analyze_sse(request: AnalyzeRequest):
    """SSE 格式分析接口"""
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="question 参数不能为空")

    stages = {
        "stage1": "意图识别",
        "stage2": "数据检索",
        "stage3": "战略分析",
        "stage4": "品牌分析",
        "stage5": "报告生成"
    }

    # 事件队列（异步共享队列）
    events_queue = asyncio.Queue()

    async def progress_callback(stage: str, status: str, data):
        """进度回调 - 收集事件"""
        summary = _generate_summary(stage, status, data)
        event_data = {
            "stage": stage,
            "stage_name": stages.get(stage, stage),
            "status": status,
            "summary": summary,
            "data": _serialize_data(data)
        }
        # Store as JSON string for SSE compatibility
        await events_queue.put(json.dumps(event_data, ensure_ascii=False))

    async def event_generator():
        """SSE 事件发生器"""
        # 启动工作流任务
        workflow_task = asyncio.create_task(
            workflow.run(request.question, progress_callback)
        )

        # 先发送进度事件
        while not workflow_task.done() or not events_queue.empty():
            try:
                # 等待事件，有超时就继续循环
                event_data_str = await asyncio.wait_for(events_queue.get(), timeout=0.5)
                # Yield as SSE-formatted dict (sse_starlette handles the formatting)
                yield {
                    "event": "progress",
                    "data": event_data_str
                }
            except asyncio.TimeoutError:
                continue

        # 确保剩余事件发送
        while not events_queue.empty():
            event_data_str = await events_queue.get()
            yield {
                "event": "progress",
                "data": event_data_str
            }

        # 获取最终结果
        try:
            result = await workflow_task

            # 发送完成事件
            complete_data = {
                "success": result.success,
                "intent_type": result.intent_type,
                "execution_time": result.execution_time,
                "report": result.report.get("markdown") if result.report else None,
                "errors": result.stage_errors
            }
            yield {
                "event": "complete",
                "data": json.dumps(complete_data, ensure_ascii=False)
            }
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}, ensure_ascii=False)
            }

    return EventSourceResponse(event_generator())


def _serialize_data(data):
    """递归序列化数据为纯 Python 类型"""
    if data is None:
        return None
    if isinstance(data, dict):
        return {k: _serialize_data(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_serialize_data(item) for item in data]
    if hasattr(data, "to_dict"):
        return data.to_dict()
    # 保留标准 JSON 类型，转换其他类型为字符串
    if isinstance(data, (str, int, float, bool, type(None))):
        return data
    return str(data)


def _extract_inner_data(data):
    """从包装的数据结构中提取内部数据"""
    # workflow.py 传递 {data: actual_data, summary: summary_text}
    # 或直接传递 actual_data
    if isinstance(data, dict):
        if "data" in data and "summary" in data:
            # 包装结构，取内层 data
            inner = data.get("data")
            if isinstance(inner, dict):
                return inner
            return data
        return data
    return data


def _generate_summary(stage: str, status: str, data) -> str:
    """根据阶段和数据生成摘要文本"""
    if status == "running":
        return "处理中..."

    if status == "done" and data is None:
        return "完成"

    # 提取内部数据（处理包装结构）
    inner = _extract_inner_data(data)

    if stage == "stage1":
        # 意图识别
        if inner and isinstance(inner, dict):
            intent_type = inner.get("intent_type", "未知")
            confidence = inner.get("confidence", 0)
            keywords = inner.get("keywords", [])
            brands = inner.get("brands_mentioned", [])
            parts = [f"类型：{intent_type}"]
            if confidence > 0:
                parts.append(f"置信度：{confidence:.0%}")
            if keywords:
                parts.append(f"关键词：{', '.join(keywords[:3])}")
            if brands:
                parts.append(f"品牌：{', '.join(brands[:3])}")
            return " | ".join(parts)
        return "完成"

    elif stage == "stage2":
        # 数据检索
        if inner and isinstance(inner, dict):
            parts = []
            vector = inner.get("vector", {})
            sql = inner.get("sql", {})
            if vector and vector.get("success"):
                count = len(vector.get("results", []))
                parts.append(f"向量检索：{count}条")
            if sql and sql.get("success"):
                results = sql.get("results", [])
                if results:
                    r = results[0]
                    # 检查是否是聚合查询（market_overview）还是明细查询（sales_by_model/sales_with_price）
                    if "brand_count" in r and "model_count" in r:
                        # 聚合查询格式
                        total = r.get("total_sales", 0)
                        brand_count = r.get("brand_count", 0)
                        model_count = r.get("model_count", 0)
                        parts.append(f"SQL查询：{brand_count}品牌/{model_count}车型")
                        if total > 0:
                            parts.append(f"总销量：{total:,}")
                    else:
                        # 明细查询格式 - 从结果中统计品牌和车型数量
                        brands = set()
                        models = set()
                        total_sales = 0
                        for row in results:
                            if row.get("brand"):
                                brands.add(row.get("brand"))
                            if row.get("model"):
                                models.add(row.get("model"))
                            total_sales += row.get("sales", 0) or 0
                        parts.append(f"SQL查询：{len(brands)}品牌/{len(models)}车型")
                        if total_sales > 0:
                            parts.append(f"总销量：{total_sales:,}")
                else:
                    parts.append(f"SQL查询：{sql.get('record_count', 0)}条")
            return " | ".join(parts) if parts else "无数据"
        return "完成"

    elif stage == "stage3":
        # 战略分析
        if inner and isinstance(inner, dict):
            parts = []
            pest = inner.get("pest", {})
            porter = inner.get("porter", {})
            swot = inner.get("swot", {})
            fourp = inner.get("fourp", {})

            if pest and pest.get("success"):
                pest_data = pest.get("data", {})
                summary = pest_data.get("summary", {})
                sentiment = summary.get("overall_sentiment", "")
                if sentiment:
                    parts.append(f"PEST：{sentiment}")
            if porter and porter.get("success"):
                porter_data = porter.get("data", {})
                summary = porter_data.get("summary", {})
                attractiveness = summary.get("industry_attractiveness", "")
                score = summary.get("overall_score", 0)
                if attractiveness:
                    parts.append(f"波特五力：{attractiveness}")
                    if score:
                        parts.append(f"评分：{score}/10")
            if swot and swot.get("success"):
                swot_data = swot.get("data", {})
                summary = swot_data.get("summary", {})
                posture = summary.get("strategic_posture", "")
                if posture:
                    parts.append(f"SWOT：{posture}型")
            if fourp and fourp.get("success"):
                fourp_data = fourp.get("data", {})
                summary = fourp_data.get("summary", {})
                score = summary.get("overall_score", 0)
                level = summary.get("overall_level", "")
                if score:
                    parts.append(f"4P：{score}/10 ({level})")
            return " | ".join(parts) if parts else "分析完成"
        return "完成"

    elif stage == "stage4":
        # 品牌分析
        if inner and isinstance(inner, dict):
            brand = inner.get("brand", "")
            success = inner.get("success", False)
            summary = inner.get("summary", {}) or (inner.get("data", {}) or {}).get("summary", {})
            # summary 可能是字典，需要转换为字符串
            if summary:
                if isinstance(summary, dict):
                    parts = []
                    for k, v in summary.items():
                        if v and isinstance(v, str):
                            parts.append(v)
                    return " | ".join(parts) if parts else f"品牌 {brand} 分析完成" if brand else "品牌分析完成"
                return str(summary)
            if brand:
                return f"品牌 {brand} 分析完成"
            if success:
                return "品牌分析完成"
        return "完成"

    elif stage == "stage5":
        # 报告生成
        if inner and isinstance(inner, dict):
            markdown = inner.get("markdown", "")
            if markdown:
                return f"报告生成完成 ({len(markdown)}字符)"
            success = inner.get("success", False)
            if success:
                return "报告生成完成"
        return "完成"

    return "完成"


@app.get("/intent_preview")
async def intent_preview(question: str):
    """意图预览接口"""
    if not question or not question.strip():
        raise HTTPException(status_code=400, detail="question 参数不能为空")

    from skill_caller import get_caller
    caller = get_caller()
    result = await caller.classify_intent(question)

    return {
        "success": True,
        "intent_type": result.get("intent_type", "未知"),
        "confidence": result.get("confidence", 0),
        "keywords": result.get("keywords", []),
        "brands_mentioned": result.get("brands_mentioned", []),
        "dimensions": result.get("dimensions", {})
    }


# ==================== 启动 ====================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "sse_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )