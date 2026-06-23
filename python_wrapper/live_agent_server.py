# -*- coding: utf-8 -*-
"""Live frontend bridge for the market strategy agent.

Formal architecture:
- Frontend -> this FastAPI bridge
- this bridge -> strategy-orchestrator ReAct loop
- this bridge streams progress and relays the final result

The bridge must not be the market-analysis brain. It must not sequence SQL,
RAG, Tavily, framework, and report tools by itself.
"""

from __future__ import annotations

import asyncio
import html
import json
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
RAG_ENGINE_ROOT = Path(r"E:\AI\data\envs\car_agent_env\ai-decision\rag-engine")
STRATEGY_ORCHESTRATOR_ROOT = WORKSPACE_ROOT / "agents" / "strategy-orchestrator"
TEMP_ROOT = WORKSPACE_ROOT / "temp"
TEMP_ROOT.mkdir(exist_ok=True)
ANALYSIS_TIMEOUT_SECONDS = 90
RUNTIME_ERROR_LOG = TEMP_ROOT / "live_agent_server_runtime_error.log"

for path in (str(RAG_ENGINE_ROOT), str(STRATEGY_ORCHESTRATOR_ROOT), str(WORKSPACE_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from market_strategy.orchestrator_integration import run_orchestrated_analysis  # noqa: E402
from quality.quality_gate import get_quality_gate  # noqa: E402


app = FastAPI(title="Market Strategy Agent Live API", version="3.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/temp", StaticFiles(directory=TEMP_ROOT), name="temp")


class AnalyzeRequest(BaseModel):
    question: str
    time_range: Optional[str] = None
    analysis_type: Optional[str] = None
    max_cycles: int = 3


class PPTRequest(BaseModel):
    question: str
    report_content: Optional[str] = None
    analysis_data: Optional[Dict[str, Any]] = None


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    if hasattr(value, "to_dict"):
        return _jsonable(value.to_dict())
    return str(value)


def _sse(event: str, data: Dict[str, Any]) -> str:
    payload = json.dumps(_jsonable(data), ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def _log_runtime_exception(context: str, exc: BaseException) -> str:
    trace = traceback.format_exc()
    message = (
        f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] {context}\n"
        f"{type(exc).__name__}: {exc}\n{trace}\n"
    )
    try:
        RUNTIME_ERROR_LOG.write_text(
            (RUNTIME_ERROR_LOG.read_text(encoding="utf-8", errors="ignore") if RUNTIME_ERROR_LOG.exists() else "")
            + message,
            encoding="utf-8",
        )
    except Exception:
        pass
    return trace


def _infer_analysis_type(question: str) -> str:
    q = question.lower()
    if any(k in question for k in ("政策", "法规", "补贴", "出口", "泰国", "欧盟", "印尼", "沙特")):
        return "policy"
    if any(k in question for k in ("竞品", "竞争", "对比", "品牌", "比亚迪", "特斯拉", "吉利", "小米")):
        return "competitor"
    if any(k in question for k in ("机会", "空间", "增长", "细分", "SUV", "suv", "价格带", "进入")):
        return "opportunity"
    if any(k in question for k in ("趋势", "宏观", "市场", "销量")) or "trend" in q:
        return "market"
    return "comprehensive"


def _infer_entities(question: str) -> List[str]:
    candidates = [
        "比亚迪", "特斯拉", "吉利", "长安", "长城", "广汽", "上汽", "小米",
        "问界", "理想", "蔚来", "小鹏", "零跑", "埃安", "极氪",
        "泰国", "印尼", "欧盟", "沙特", "新能源SUV", "15-20万",
    ]
    return [item for item in candidates if item in question]


def _normalize_time_range(question: str, requested: Optional[str]) -> str:
    source = requested or question or ""
    if any(k in source for k in ("近半年", "最近半年", "6个月", "六个月")):
        return "最近6个月"
    if any(k in source for k in ("近三个月", "最近3个月", "3个月", "三个月")):
        return "最近3个月"
    if any(k in source for k in ("最近12个月", "近12个月", "12个月", "一年")):
        return "最近12个月"
    return requested or "最近6个月"


def _source_names(result: Dict[str, Any]) -> List[str]:
    names: List[str] = []
    for source in result.get("evidence_sources", []) or []:
        if isinstance(source, dict):
            name = source.get("source") or source.get("tool") or source.get("name")
            if name:
                names.append(str(name))
    return sorted(set(names))


def _quality_summary(result: Dict[str, Any]) -> Dict[str, Any]:
    qg = get_quality_gate()
    passed, checks = qg.run_all(result)
    failed = [
        {
            "check": item.check_name,
            "level": getattr(item.level, "value", str(item.level)),
            "message": item.message,
            "suggestions": item.suggestions,
        }
        for item in checks
        if not item.passed
    ]
    return {"quality_passed": passed, "failed_quality_checks": failed}


def _orchestrator_trace(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    traces = [
        {
            "agent": "market_strategy_agent",
            "skill": "strategy-orchestrator",
            "action": "orchestrate",
            "status": "done" if result.get("success") else "failed",
            "summary": (
                "已调用 strategy-orchestrator ReAct 主循环；"
                f"cycles={result.get('cycles_used', 0)}；stop_reason={result.get('stop_reason') or 'unknown'}"
            ),
        }
    ]
    for source in result.get("evidence_sources", []) or []:
        if not isinstance(source, dict):
            continue
        traces.append(
            {
                "agent": "strategy-orchestrator",
                "skill": source.get("source") or source.get("tool") or "evidence",
                "action": source.get("tool") or "observe",
                "status": "done",
                "summary": source.get("claim") or "证据已进入 orchestrator evidence ledger",
            }
        )
    return traces


def _format_report(question: str, result: Dict[str, Any], quality_passed: bool) -> str:
    facts = result.get("facts", []) or []
    inferences = result.get("inferences", []) or []
    uncertainty = result.get("missing_or_uncertain", []) or []
    sources = _source_names(result)
    answer = result.get("answer") or ""

    lines = [
        "# strategy-orchestrator ReAct 分析结果",
        "",
        f"**问题**：{question}",
        f"**执行状态**：{'成功' if result.get('success') else '失败'}",
        f"**质量门禁**：{'通过' if quality_passed else '未通过'}",
        f"**置信度**：{float(result.get('confidence') or 0):.1%}",
        f"**ReAct 循环轮次**：{result.get('cycles_used', 0)}",
        f"**停止原因**：{result.get('stop_reason') or '未知'}",
        f"**证据来源**：{', '.join(sources) if sources else '无'}",
        "",
        "## 事实依据",
    ]

    if facts:
        for item in facts[:8]:
            source = item.get("source") or item.get("tool") or "evidence"
            claim = item.get("claim") or item.get("content") or str(item)
            content = item.get("content")
            suffix = f"：{content}" if content and content != claim else ""
            lines.append(f"- [{source}] {claim}{suffix}")
    else:
        lines.append("- 暂无结构化事实。")

    lines += ["", "## 分析判断"]
    if inferences:
        for item in inferences[:8]:
            source = item.get("source") or item.get("tool") or "analysis"
            claim = item.get("claim") or item.get("content") or str(item)
            confidence = item.get("confidence")
            suffix = f"（置信度 {float(confidence):.0%}）" if isinstance(confidence, (int, float)) else ""
            lines.append(f"- [{source}] {claim}{suffix}")
    else:
        lines.append("- 暂无额外推断。")

    recommendations = result.get("recommendations") or []
    if recommendations:
        lines += ["", "## 建议动作"]
        for item in recommendations[:8]:
            lines.append(f"- {item}")

    risks = result.get("risks") or []
    if risks:
        lines += ["", "## 风险提示"]
        for item in risks[:8]:
            if isinstance(item, dict):
                lines.append(f"- {item.get('item', '')}: {item.get('mitigation', '')}")
            else:
                lines.append(f"- {item}")

    if uncertainty:
        lines += ["", "## 不确定性与缺口"]
        for item in uncertainty[:8]:
            lines.append(f"- {item}")

    if answer:
        lines += ["", "## Orchestrator 原始回答", "", str(answer)]

    next_steps = result.get("next_steps") or []
    if next_steps:
        lines += ["", "## 下一步"]
        for item in next_steps[:8]:
            lines.append(f"- {item}")

    return "\n".join(lines)


def _run_analysis(request: AnalyzeRequest) -> Dict[str, Any]:
    question = request.question.strip()
    started = time.time()
    analysis_type = request.analysis_type or _infer_analysis_type(question)
    time_range = _normalize_time_range(question, request.time_range)
    entities = _infer_entities(question)

    result = run_orchestrated_analysis(
        query=question,
        time_range=time_range,
        entities=entities,
        analysis_type=analysis_type,
        max_cycles=request.max_cycles,
    )
    result = _jsonable(result)
    quality = _quality_summary(result)
    traces = _orchestrator_trace(result)

    return {
        "success": bool(result.get("success")),
        "question": question,
        "analysis_type": analysis_type,
        "time_range": time_range,
        "entities": entities,
        "confidence": result.get("confidence", 0),
        "cycles_used": result.get("cycles_used", 0),
        "stop_reason": result.get("stop_reason"),
        "sources": _source_names(result),
        "evidence_count": len(result.get("evidence_sources", []) or []),
        "facts_count": len(result.get("facts", []) or []),
        "inferences_count": len(result.get("inferences", []) or []),
        "quality_passed": quality["quality_passed"],
        "failed_quality_checks": quality["failed_quality_checks"],
        "missing_or_uncertain": result.get("missing_or_uncertain", []) or [],
        "errors": result.get("errors", []) or [],
        "report": _format_report(question, result, quality["quality_passed"]),
        "raw": result,
        "execution_trace": traces,
        "skill_trace": traces,
        "execution_time": round(time.time() - started, 2),
    }


def _db_snapshot() -> Dict[str, Any]:
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        from retrieval.vector_store import DB_CONFIG

        conn = psycopg2.connect(**DB_CONFIG, connect_timeout=3, cursor_factory=RealDictCursor)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS cnt FROM documents")
        documents = cur.fetchone()["cnt"]
        cur.execute("SELECT COUNT(*) AS cnt FROM chunks")
        chunks = cur.fetchone()["cnt"]
        cur.close()
        conn.close()
        return {"connected": True, "documents": documents, "chunks": chunks}
    except Exception as exc:
        return {"connected": False, "error": str(exc), "documents": 0, "chunks": 0}


@app.get("/")
async def root() -> Dict[str, Any]:
    return {
        "name": "Market Strategy Agent Live API",
        "status": "ok",
        "mode": "sse_relay_to_strategy_orchestrator",
        "frontend": "/frontend_demo.html",
        "endpoints": ["/health", "/analyze", "/analyze_sse", "/generate_ppt"],
    }


@app.get("/frontend_demo.html")
async def frontend() -> FileResponse:
    html_path = WORKSPACE_ROOT / "frontend_demo.html"
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="frontend_demo.html not found")
    return FileResponse(html_path, media_type="text/html; charset=utf-8")


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "timestamp": time.time(),
        "mode": "sse_relay_to_strategy_orchestrator",
        "db": _db_snapshot(),
    }


@app.post("/analyze")
async def analyze(request: AnalyzeRequest) -> Dict[str, Any]:
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="question cannot be empty")
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_run_analysis, request),
            timeout=ANALYSIS_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError as exc:
        _log_runtime_exception("POST /analyze timeout", exc)
        raise HTTPException(
            status_code=504,
            detail=f"analysis timed out after {ANALYSIS_TIMEOUT_SECONDS}s",
        )
    except Exception as exc:
        _log_runtime_exception("POST /analyze failed", exc)
        raise


@app.post("/analyze_sse")
async def analyze_sse(request: AnalyzeRequest) -> StreamingResponse:
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="question cannot be empty")

    async def stream() -> Iterable[str]:
        question = request.question.strip()
        analysis_type = request.analysis_type or _infer_analysis_type(question)
        time_range = _normalize_time_range(question, request.time_range)
        entities = _infer_entities(question)
        start = time.time()

        yield _sse(
            "progress",
            {
                "stage": "stage1",
                "stage_name": "接收任务",
                "status": "done",
                "summary": f"桥接层接收问题；analysis_type={analysis_type}；time_range={time_range}；entities={entities}",
            },
        )
        yield _sse(
            "progress",
            {
                "stage": "stage2",
                "stage_name": "转交编排器",
                "status": "running",
                "summary": "正在调用 strategy-orchestrator ReAct 主循环；桥接层不再自行顺序调 SQL/RAG/Tavily。",
            },
        )

        task = asyncio.create_task(asyncio.to_thread(_run_analysis, request))
        beat = 0
        while not task.done():
            beat += 1
            elapsed = time.time() - start
            if elapsed > ANALYSIS_TIMEOUT_SECONDS:
                task.cancel()
                yield _sse(
                    "error",
                    {
                        "success": False,
                        "error_type": "TimeoutError",
                        "error": f"analysis timed out after {ANALYSIS_TIMEOUT_SECONDS}s",
                        "execution_time": round(elapsed, 2),
                    },
                )
                return
            yield _sse(
                "progress",
                {
                    "stage": "stage3",
                    "stage_name": "ReAct 编排中",
                    "status": "running",
                    "summary": f"strategy-orchestrator 正在 Plan/Act/Observe/Reflect；已用 {round(time.time() - start, 1)}s。",
                    "heartbeat": beat,
                },
            )
            await asyncio.sleep(2)

        try:
            result = await task
            yield _sse(
                "progress",
                {
                    "stage": "stage4",
                    "stage_name": "结果回传",
                    "status": "done",
                    "summary": (
                        f"orchestrator 完成；cycles={result.get('cycles_used')}；"
                        f"confidence={float(result.get('confidence') or 0):.1%}；"
                        f"quality_passed={result.get('quality_passed')}"
                    ),
                },
            )
            yield _sse("complete", result)
        except Exception as exc:
            trace = _log_runtime_exception("POST /analyze_sse failed", exc)
            yield _sse(
                "error",
                {
                    "success": False,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "traceback_tail": trace[-1200:],
                    "execution_time": round(time.time() - start, 2),
                },
            )

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@app.post("/generate_ppt")
async def generate_ppt(request: PPTRequest) -> Dict[str, Any]:
    """Render a lightweight HTML deck from orchestrator output.

    This is presentation rendering only; it does not perform market analysis.
    """
    try:
        output_path = TEMP_ROOT / f"presentation_{int(time.time())}.html"
        content = request.report_content or (request.analysis_data or {}).get("report") or ""
        title = request.question or "市场战略分析"
        html_text = _presentation_html(title, content, request.analysis_data or {})
        output_path.write_text(html_text, encoding="utf-8")
        return {"success": True, "ppt_path": str(output_path), "ppt_url": "/temp/" + output_path.name, "message": "PPT生成成功"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def _presentation_html(title: str, report_content: str, analysis_data: Dict[str, Any]) -> str:
    confidence = analysis_data.get("confidence", "-")
    cycles = analysis_data.get("cycles_used", "-")
    sources = ", ".join(analysis_data.get("sources") or []) or "无"
    safe_title = html.escape(title)
    safe_report = html.escape(report_content[:1800] or "暂无报告内容")
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title}</title>
  <style>
    body {{ margin:0; font-family: Arial, "Microsoft YaHei", sans-serif; background:#101418; color:#f7f8fa; }}
    section {{ min-height:100vh; padding:64px 8vw; box-sizing:border-box; display:flex; flex-direction:column; justify-content:center; }}
    h1 {{ font-size:48px; margin:0 0 24px; }}
    h2 {{ font-size:34px; margin:0 0 20px; }}
    p, pre {{ font-size:20px; line-height:1.65; color:#d7dce2; white-space:pre-wrap; }}
    .metric {{ display:inline-block; margin:8px 16px 8px 0; padding:12px 16px; border:1px solid #3b4652; border-radius:8px; }}
  </style>
</head>
<body>
  <section><h1>{safe_title}</h1><p>strategy-orchestrator ReAct 分析结果</p></section>
  <section><h2>证据与质量</h2><p><span class="metric">置信度：{confidence}</span><span class="metric">循环：{cycles}</span><span class="metric">来源：{html.escape(sources)}</span></p></section>
  <section><h2>报告摘要</h2><pre>{safe_report}</pre></section>
</body>
</html>"""


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("live_agent_server:app", host="0.0.0.0", port=8003, reload=False)
