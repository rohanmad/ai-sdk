"""Writes routing decisions to SQLite for observability."""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class RoutingLogEntry:
    request_id: str
    target: str
    reason: str
    complexity_score: float
    sensitivity_flag: bool
    sensitivity_triggers: list[str]
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    estimated_cost_saved_usd: float | None
    mock_execution: bool
    prompt_preview: str


class TelemetryLogger:
    def __init__(self, db_path: str | Path = "telemetry/routing.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS routing_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at REAL NOT NULL,
                    request_id TEXT NOT NULL,
                    target TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    complexity_score REAL NOT NULL,
                    sensitivity_flag INTEGER NOT NULL,
                    sensitivity_triggers TEXT NOT NULL,
                    latency_ms REAL NOT NULL,
                    prompt_tokens INTEGER NOT NULL,
                    completion_tokens INTEGER NOT NULL,
                    estimated_cost_saved_usd REAL,
                    mock_execution INTEGER NOT NULL,
                    prompt_preview TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def log(self, entry: RoutingLogEntry, *, created_at: float | None = None) -> int:
        ts = created_at if created_at is not None else time.time()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO routing_decisions (
                    created_at, request_id, target, reason,
                    complexity_score, sensitivity_flag, sensitivity_triggers,
                    latency_ms, prompt_tokens, completion_tokens,
                    estimated_cost_saved_usd, mock_execution, prompt_preview
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ts,
                    entry.request_id,
                    entry.target,
                    entry.reason,
                    entry.complexity_score,
                    int(entry.sensitivity_flag),
                    json.dumps(entry.sensitivity_triggers),
                    entry.latency_ms,
                    entry.prompt_tokens,
                    entry.completion_tokens,
                    entry.estimated_cost_saved_usd,
                    int(entry.mock_execution),
                    entry.prompt_preview,
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM routing_decisions
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def summary(self) -> dict[str, Any]:
        with self._connect() as conn:
            total = conn.execute(
                "SELECT COUNT(*) AS n FROM routing_decisions"
            ).fetchone()["n"]
            by_target = conn.execute(
                """
                SELECT target, COUNT(*) AS n
                FROM routing_decisions
                GROUP BY target
                """
            ).fetchall()
            avg_latency = conn.execute(
                "SELECT AVG(latency_ms) AS avg_ms FROM routing_decisions"
            ).fetchone()["avg_ms"]
            cost_saved = conn.execute(
                """
                SELECT SUM(estimated_cost_saved_usd) AS total
                FROM routing_decisions
                WHERE estimated_cost_saved_usd IS NOT NULL
                """
            ).fetchone()["total"]

        return {
            "total_requests": total,
            "by_target": {row["target"]: row["n"] for row in by_target},
            "avg_latency_ms": avg_latency,
            "total_cost_saved_usd": cost_saved,
        }

    def all_decision_rows(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT target, prompt_tokens, completion_tokens
                FROM routing_decisions
                ORDER BY created_at ASC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def api_summary(self) -> dict[str, Any]:
        from telemetry.cost import TARGETS, compute_cost_savings

        with self._connect() as conn:
            total = conn.execute(
                "SELECT COUNT(*) AS n FROM routing_decisions"
            ).fetchone()["n"]
            by_target_rows = conn.execute(
                """
                SELECT target, COUNT(*) AS n, AVG(latency_ms) AS avg_latency_ms
                FROM routing_decisions
                GROUP BY target
                """
            ).fetchall()
            cost_rows = conn.execute(
                """
                SELECT target, prompt_tokens, completion_tokens
                FROM routing_decisions
                """
            ).fetchall()

        by_target: dict[str, dict[str, float | int]] = {}
        for target in TARGETS:
            by_target[target] = {"count": 0, "pct": 0.0, "avg_latency_ms": None}

        for row in by_target_rows:
            target = row["target"]
            count = int(row["n"])
            by_target[target] = {
                "count": count,
                "pct": (count / total * 100) if total else 0.0,
                "avg_latency_ms": round(float(row["avg_latency_ms"]), 2)
                if row["avg_latency_ms"] is not None
                else None,
            }

        cost = compute_cost_savings([dict(row) for row in cost_rows])

        from telemetry.quality import load_eval_quality_metrics

        quality = load_eval_quality_metrics()

        return {
            "total_requests": total,
            "by_target": by_target,
            "cost": cost,
            "quality": quality,
            "pricing": {
                "model": "gpt-4o-mini",
                "input_price_per_1m": 0.15,
                "output_price_per_1m": 0.60,
                "local_api_cost_usd": 0.0,
            },
        }

    def api_decisions(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        target: str | None = None,
    ) -> dict[str, Any]:
        limit = max(1, min(limit, 200))
        offset = max(0, offset)

        where = ""
        params: list[Any] = []
        if target:
            where = "WHERE target = ?"
            params.append(target)

        with self._connect() as conn:
            total = conn.execute(
                f"SELECT COUNT(*) AS n FROM routing_decisions {where}",
                params,
            ).fetchone()["n"]
            rows = conn.execute(
                f"""
                SELECT
                    created_at,
                    request_id,
                    prompt_preview,
                    target,
                    reason,
                    complexity_score,
                    sensitivity_flag,
                    latency_ms,
                    prompt_tokens,
                    completion_tokens,
                    estimated_cost_saved_usd,
                    mock_execution
                FROM routing_decisions
                {where}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            ).fetchall()

        decisions = []
        for row in rows:
            decisions.append(
                {
                    "timestamp": row["created_at"],
                    "request_id": row["request_id"],
                    "prompt": row["prompt_preview"],
                    "target": row["target"],
                    "reason": row["reason"],
                    "complexity_score": row["complexity_score"],
                    "sensitivity_flag": bool(row["sensitivity_flag"]),
                    "latency_ms": round(float(row["latency_ms"]), 2),
                    "prompt_tokens": row["prompt_tokens"],
                    "completion_tokens": row["completion_tokens"],
                    "estimated_cost_saved_usd": row["estimated_cost_saved_usd"],
                    "mock_execution": bool(row["mock_execution"]),
                }
            )

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "decisions": decisions,
        }
