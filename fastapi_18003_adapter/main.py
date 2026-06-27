# -*- coding: utf-8 -*-
"""FastAPI adapter that connects chat.html to OpenClaw Gateway sessions.

This adapter is intentionally thin:
- /chat accepts browser messages and sends them to the market_strategy Agent.
- /sse streams callback/progress events to the browser.
- /callback receives ReAct events from independent Agents.

It must not implement market-analysis orchestration in Python.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any, AsyncIterator, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .gateway_client import MARKET_AGENT_ID, post_chat_completion
from .models import CallbackPayload, ChatRequest
from .session_manager import session_manager



async def _db_snapshot() -> Dict[str, Any]:
    """Query the rag-engine database for document/chunk counts."""
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        conn = psycopg2.connect(
            host="192.168.3.146",
            port=5432,
            database="vectordb",
            user="vectordb",
            password="vectordb123",
            connect_timeout=3,
            cursor_factory=RealDictCursor,
        )
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


ADAPTER_BASE_URL = os.environ.get("MARKET_WEB_ADAPTER_BASE_URL", "http://127.0.0.1:18003").rstrip("/")
CALLBACK_HELPER_PATH = Path(__file__).with_name("callback_client.py")
HEARTBEAT_SECONDS = 15
TREE_EVENT_KINDS = {"task_progress", "substep_created", "substep_updated"}
TERMINAL_TIMEOUT_HINTS = ("timed out", "timeout", "operation was aborted", "aborted")

app = FastAPI(title="Market WebChat OpenClaw Adapter", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _sse(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _event_kind(event: Dict[str, Any]) -> str:
    explicit = str(event.get("event") or event.get("type") or "").strip().lower()
    if explicit in {"progress", "react", "complete", "error", *TREE_EVENT_KINDS}:
        return explicit
    phase = str(event.get("phase") or "").strip().lower()
    if phase == "complete" or "report" in event or "answer" in event:
        return "complete"
    if phase == "error" or event.get("error"):
        return "error"
    return "react"


def _is_gateway_watch_error(result: Dict[str, Any]) -> bool:
    error = str(result.get("error") or "").lower()
    return any(hint in error for hint in TERMINAL_TIMEOUT_HINTS)


def _payload_to_dict(payload: Any) -> Dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump()
    if hasattr(payload, "dict"):
        return payload.dict()
    return dict(payload or {})


def _normalize_callback_event(payload: Any) -> tuple[str, Dict[str, Any]]:
    data = _payload_to_dict(payload)
    session_id = str(data.get("session_id") or "").strip()
    raw_event = data.get("event") or {}

    if isinstance(raw_event, str):
        event: Dict[str, Any] = {"phase": raw_event}
    elif isinstance(raw_event, dict):
        event = dict(raw_event)
    else:
        event = {"raw_event": raw_event}

    flat_event = {k: v for k, v in data.items() if k not in {"session_id", "event"}}
    event = {**flat_event, **event}
    event.setdefault("timestamp", time.time())
    return session_id, event


def _normalize_task_event(event: Dict[str, Any]) -> Dict[str, Any]:
    event = dict(event)
    status_aliases = {
        "doing": "running",
        "in_progress": "running",
        "success": "done",
        "finished": "done",
        "failed": "error",
    }
    status = str(event.get("status") or "").strip().lower()
    if status:
        event["status"] = status_aliases.get(status, status)

    if "node_id" not in event and event.get("id"):
        event["node_id"] = str(event["id"])
    if "summary" not in event and event.get("name"):
        event["summary"] = str(event["name"])
    if "display_name" not in event and event.get("summary"):
        event["display_name"] = str(event["summary"])

    kind = str(event.get("event") or event.get("type") or "").strip().lower()
    if kind == "substep_created":
        event["is_new_substep"] = True
    if kind in TREE_EVENT_KINDS and "node_id" not in event:
        agent = str(event.get("agent") or "agent").strip().lower().replace(" ", "_")
        phase = str(event.get("phase") or event.get("stage") or kind).strip().lower().replace(" ", "_")
        task_id = str(event.get("task_id") or "").strip().lower().replace(" ", "_")
        event["node_id"] = ":".join(part for part in [agent, phase, task_id] if part)
    return event


def _complete_payload(req: ChatRequest, gateway_result: Dict[str, Any], started_at: float) -> Dict[str, Any]:
    # Try to extract confidence from various possible locations
    confidence = (
        gateway_result.get("confidence")
        or gateway_result.get("result", {}).get("confidence")
        or gateway_result.get("quality_check", {}).get("confidence")
        or 0
    )
    
    # Try to extract report from various possible locations (report-agent returns output_path, markdown, etc.)
    report = (
        gateway_result.get("report")
        or gateway_result.get("markdown")
        or gateway_result.get("output_path")
        or gateway_result.get("result", {}).get("markdown")
        or gateway_result.get("text")
        or ""
    )
    text = str(report)
    return {
        "success": bool(gateway_result.get("ok")),
        "question": req.question,
        "analysis_type": req.analysis_type or "",
        "time_range": req.time_range or "",
        "confidence": confidence,
        "quality_passed": bool(gateway_result.get("ok")),
        "evidence_count": 0,
        "execution_time": round(time.time() - started_at, 2),
        "sources": [f"openclaw:{MARKET_AGENT_ID}"],
        "missing_or_uncertain": [] if gateway_result.get("ok") else [gateway_result.get("error") or "Gateway call failed"],
        "report": text,
        "answer": text,
        "raw": {
            "gateway": {k: v for k, v in gateway_result.items() if k != "raw"},
            "session_id": req.session_id,
        },
    }


def build_market_agent_message(req: ChatRequest) -> str:
    callback_url = f"{ADAPTER_BASE_URL}/callback"
    callback_command = (
        f'python "{CALLBACK_HELPER_PATH}" '
        f'--callback-url "{callback_url}" '
        f'--session-id "{req.session_id}" '
        '--phase "Plan" --status "running" '
        '--agent "strategy-orchestrator" '
        '--summary "Planning task and selecting execution agents."'
    )
    payload = {
        "source": "chat.html",
        "session_id": req.session_id,
        "callback_url": callback_url,
        "callback_helper": {
            "path": str(CALLBACK_HELPER_PATH),
            "command_template": callback_command,
            "event_schema": {
                "event": "task_progress | substep_created | substep_updated | complete | error",
                "node_id": "stable unique node id for this step, reused when updating the same step",
                "parent_id": "optional parent node_id for tree nesting",
                "phase": "Plan | Dispatch | DataRunning | DataDone | AnalysisRunning | AnalysisDone | ReportRunning | QualityGate | Complete | Error",
                "status": "running | done | warning | error",
                "display_name": "short node label shown in the task tree",
                "summary": "short user-visible execution update",
                "agent": "agent currently doing the work",
                "task_id": "optional subtask identifier",
                "details": "optional JSON object with source/tool/gap counts",
            },
            "rule": "Use this Python helper for every callback. Do not use curl aliases or shell-specific HTTP snippets.",
        },
        "user_message": req.question,
        "analysis_type": req.analysis_type,
        "time_range": req.time_range,
        "max_cycles": req.max_cycles,
        "routing_contract": {
            "ordinary_chat": "Answer in the current market_strategy OpenClaw session.",
            "complex_market_task": (
                "If analysis_type is business_analysis, opportunity_assessment, "
                "comprehensive_research, or policy_impact, call sessions_send("
                "agentId='strategy-orchestrator', ...) and pass session_id, callback_url, "
                "and the full callback_helper block."
            ),
            "callback_requirement": (
                "The downstream strategy-orchestrator must emit each ReAct event with callback_helper. "
                "Do not use curl -X POST. PowerShell treats curl as Invoke-WebRequest and can break headers. "
                "For every delegated Agent, send a substep_created event when it starts, then substep_updated "
                "events as it runs, using stable node_id and parent_id so chat.html can render a nested task tree. "
                "The final callback should include phase='Complete' and report or answer."
            ),
        },
    }
    return (
        "You are receiving a web chat turn from chat.html through the OpenClaw Gateway.\n"
        "Follow the routing contract exactly. Do not let the FastAPI adapter perform orchestration.\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


async def _run_gateway_turn(req: ChatRequest) -> None:
    started_at = time.time()
    await session_manager.push(
        req.session_id,
        "progress",
        {
            "event": "task_progress",
            "node_id": "gateway_send",
            "phase": "Gateway",
            "stage": "stage1",
            "status": "running",
            "agent": "fastapi_18003_adapter",
            "display_name": "Gateway relay",
            "summary": f"Sending turn to OpenClaw agent={MARKET_AGENT_ID}; session_id={req.session_id}",
        },
    )
    message = build_market_agent_message(req)
    result = await asyncio.to_thread(
        post_chat_completion,
        agent_id=MARKET_AGENT_ID,
        session_id=req.session_id,
        message=message,
    )
    if result.get("ok"):
        await session_manager.push(
            req.session_id,
            "complete",
            _complete_payload(req, result, started_at),
        )
    elif _is_gateway_watch_error(result):
        await session_manager.push(
            req.session_id,
            "task_progress",
            {
                "event": "task_progress",
                "node_id": "gateway_watch",
                "parent_id": "gateway_send",
                "phase": "GatewayWatch",
                "stage": "gateway_watch",
                "status": "warning",
                "agent": "fastapi_18003_adapter",
                "display_name": "Gateway synchronous wait ended",
                "summary": (
                    "Gateway 同步等待已结束，后台智能体可能仍在运行；"
                    "页面继续监听 callback/SSE，不把这次等待结束判定为任务失败。"
                ),
                "details": {
                    "execution_time": round(time.time() - started_at, 2),
                    "raw_error": result.get("error") or "",
                },
            },
        )
    else:
        await session_manager.push(
            req.session_id,
            "error",
            {
                "success": False,
                "error": result.get("error") or "OpenClaw Gateway call failed",
                "execution_time": round(time.time() - started_at, 2),
                "raw": result,
            },
        )


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "mode": "openclaw_gateway_event_adapter",
        "timestamp": time.time(),
        "sessions": await session_manager.snapshot(),
        "db": await _db_snapshot(),
    }


@app.post("/chat")
async def chat(req: ChatRequest) -> Dict[str, Any]:
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="question cannot be empty")
    await session_manager.mark_running(req.session_id)
    await session_manager.push(
        req.session_id,
        "react",
        {
            "event": "task_progress",
            "node_id": "accept",
            "phase": "Accept",
            "stage": "stage0",
            "status": "done",
            "agent": "fastapi_18003_adapter",
            "display_name": "Request accepted",
            "summary": "Accepted browser message; adapter will relay to OpenClaw Gateway.",
        },
    )
    asyncio.create_task(_run_gateway_turn(req))
    return {"accepted": True, "session_id": req.session_id}


@app.get("/sse")
async def sse(session_id: str, after_seq: int = 0) -> StreamingResponse:
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    await session_manager.get_or_create(session_id)

    async def stream() -> AsyncIterator[str]:
        last_sent_seq = after_seq
        if after_seq >= 0:
            history = await session_manager.history(session_id, after_seq=after_seq)
            for item in history["events"]:
                last_sent_seq = max(last_sent_seq, int(item["data"].get("seq") or 0))
                yield _sse(str(item["event"]), item["data"])
        while True:
            item = await session_manager.pop(session_id, timeout=HEARTBEAT_SECONDS)
            if item is None:
                yield _sse(
                    "progress",
                    {
                        "is_heartbeat": True,
                        "phase": "Heartbeat",
                        "stage": "heartbeat",
                        "status": "running",
                        "summary": "Waiting for OpenClaw Agent callback or final response.",
                    },
                )
                continue
            item_seq = int(item["data"].get("seq") or 0)
            if item_seq and item_seq <= last_sent_seq:
                continue
            last_sent_seq = max(last_sent_seq, item_seq)
            yield _sse(str(item["event"]), item["data"])
            if item["event"] in {"complete", "error"}:
                break

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@app.get("/events")
async def events(session_id: str, after_seq: int = 0) -> Dict[str, Any]:
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    return await session_manager.history(session_id, after_seq=after_seq)


@app.post("/callback")
async def callback(payload: CallbackPayload) -> Dict[str, Any]:
    session_id, event = _normalize_callback_event(payload)
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    event = _normalize_task_event(event)
    event_kind = _event_kind(event)
    if event_kind == "complete":
        event.setdefault("success", True)
        event.setdefault("quality_passed", True)
        event.setdefault("confidence", 0)
        if "report" not in event and "answer" in event:
            event["report"] = event["answer"]
    await session_manager.push(session_id, event_kind, event)
    return {"ok": True, "session_id": session_id, "event": event_kind}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("fastapi_18003_adapter.main:app", host="127.0.0.1", port=18003, reload=False)
