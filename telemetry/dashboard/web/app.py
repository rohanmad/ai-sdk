"""FastAPI app serving routing telemetry JSON API + static dashboard."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from packages.routing_engine.session import SessionRouteStore
from packages.sdk.router import Router, RouterConfig
from packages.sdk.types import GenerateTextRequest
from telemetry.dashboard.web.chat_models import ChatErrorResponse, ChatRequest, ChatResponse
from telemetry.logger import TelemetryLogger

WEB_DIR = Path(__file__).resolve().parent
STATIC_DIR = WEB_DIR / "static"
PKG_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB = PKG_ROOT / "telemetry" / "routing.db"
DEFAULT_POLICY = PKG_ROOT / "config" / "policy.yaml"


def _build_generate_request(body: ChatRequest) -> GenerateTextRequest:
    return GenerateTextRequest(
        prompt=body.resolved_prompt(),
        messages=body.resolved_messages(),
        max_tokens=body.max_tokens,
        temperature=body.temperature,
        session_id=body.session_id,
    )


def _chat_response_from_result(result) -> ChatResponse:
    text = result.choices[0].text if result.choices else ""
    mock = "[mock-" in text or "[mock-cloud:" in text
    finish_reason = result.choices[0].finish_reason if result.choices else "stop"
    return ChatResponse(
        request_id=result.id,
        text=text,
        target=result.routing.target,
        reason=result.routing.reason,
        complexity_score=result.routing.complexity_score,
        sensitivity_flag=result.routing.sensitivity_flag,
        sensitivity_triggers=list(result.routing.sensitivity_triggers),
        latency_ms=round(result.latency_ms, 2),
        model=result.model,
        mock_execution=mock,
        finish_reason=finish_reason,
    )


def _chat_response_from_event(event: dict[str, object]) -> ChatResponse:
    return ChatResponse(
        request_id=str(event["request_id"]),
        text=str(event["text"]),
        target=str(event["target"]),
        reason=str(event["reason"]),
        complexity_score=float(event["complexity_score"]),
        sensitivity_flag=bool(event["sensitivity_flag"]),
        sensitivity_triggers=list(event.get("sensitivity_triggers") or []),
        latency_ms=float(event["latency_ms"]),
        model=str(event["model"]),
        mock_execution=bool(event["mock_execution"]),
        finish_reason=str(event.get("finish_reason") or "stop"),
    )


def create_app(
    db_path: Path | None = None,
    *,
    policy_path: Path | None = None,
    router_config: RouterConfig | None = None,
    session_store: SessionRouteStore | None = None,
) -> FastAPI:
    resolved_db = db_path or DEFAULT_DB
    resolved_policy = policy_path or DEFAULT_POLICY
    logger = TelemetryLogger(resolved_db)
    chat_sessions = session_store or SessionRouteStore()

    if router_config is None:
        router_config = RouterConfig(
            policy_path=resolved_policy,
            telemetry_db=resolved_db,
        )
    elif router_config.telemetry_db == "telemetry/routing.db":
        router_config.telemetry_db = resolved_db
    router = Router.init(router_config)

    app = FastAPI(title="Adaptive Router Telemetry", version="1.0.0")

    @app.get("/api/summary")
    def get_summary() -> dict:
        return logger.api_summary()

    @app.get("/api/decisions")
    def get_decisions(
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
        target: str | None = Query(None),
    ) -> dict:
        return logger.api_decisions(limit=limit, offset=offset, target=target)

    @app.post(
        "/api/chat",
        response_model=ChatResponse,
        responses={503: {"model": ChatErrorResponse}},
    )
    def post_chat(body: ChatRequest) -> ChatResponse | JSONResponse | StreamingResponse:
        request = _build_generate_request(body)

        if body.stream:

            def event_stream():
                try:
                    for event in router.generate_text_stream(
                        request,
                        session_store=chat_sessions,
                    ):
                        yield f"data: {json.dumps(event)}\n\n"
                except Exception as exc:
                    payload = {"type": "error", "error": "Inference failed", "detail": str(exc)}
                    yield f"data: {json.dumps(payload)}\n\n"

            return StreamingResponse(event_stream(), media_type="text/event-stream")

        try:
            result = router.generate_text(request, session_store=chat_sessions)
        except Exception as exc:
            payload = ChatErrorResponse(
                error="Inference failed",
                detail=str(exc),
            )
            return JSONResponse(status_code=503, content=payload.model_dump())

        return _chat_response_from_result(result)

    @app.post("/api/chat/new")
    def new_chat_session(body: dict | None = None) -> dict[str, str]:
        session_id = (body or {}).get("session_id")
        if session_id:
            chat_sessions.clear(str(session_id))
        return {"status": "ok"}

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/chat")
    def chat_page() -> FileResponse:
        return FileResponse(STATIC_DIR / "chat.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run adaptive router web dashboard")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    import uvicorn

    uvicorn.run(
        create_app(args.db, policy_path=args.policy),
        host=args.host,
        port=args.port,
    )


if __name__ == "__main__":
    main()
