"""FastAPI app serving routing telemetry JSON API + static dashboard."""

from __future__ import annotations

import argparse
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from packages.sdk.router import Router, RouterConfig
from packages.sdk.types import GenerateTextRequest
from telemetry.dashboard.web.chat_models import ChatErrorResponse, ChatRequest, ChatResponse
from telemetry.logger import TelemetryLogger

WEB_DIR = Path(__file__).resolve().parent
STATIC_DIR = WEB_DIR / "static"
PKG_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB = PKG_ROOT / "telemetry" / "routing.db"
DEFAULT_POLICY = PKG_ROOT / "config" / "policy.yaml"


def create_app(
    db_path: Path | None = None,
    *,
    policy_path: Path | None = None,
    router_config: RouterConfig | None = None,
) -> FastAPI:
    resolved_db = db_path or DEFAULT_DB
    resolved_policy = policy_path or DEFAULT_POLICY
    logger = TelemetryLogger(resolved_db)

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

    @app.post("/api/chat", response_model=ChatResponse, responses={503: {"model": ChatErrorResponse}})
    def post_chat(body: ChatRequest) -> ChatResponse | JSONResponse:
        try:
            result = router.generate_text(
                GenerateTextRequest(
                    prompt=body.prompt,
                    max_tokens=body.max_tokens,
                    temperature=body.temperature,
                )
            )
        except Exception as exc:
            payload = ChatErrorResponse(
                error="Inference failed",
                detail=str(exc),
            )
            return JSONResponse(status_code=503, content=payload.model_dump())

        text = result.choices[0].text if result.choices else ""
        mock = "[mock-" in text or "[mock-cloud:" in text

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
        )

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
