"""Sticky routing state for multi-turn chat sessions."""

from __future__ import annotations

from dataclasses import dataclass

from packages.routing_engine.decide import DecideOutput
from packages.sdk.types import RoutingTarget


@dataclass
class SessionRoute:
    target: RoutingTarget
    sensitivity_flag: bool
    complexity_level: str


class SessionRouteStore:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionRoute] = {}

    def get(self, session_id: str) -> SessionRoute | None:
        return self._sessions.get(session_id)

    def remember(self, session_id: str, decision: DecideOutput) -> None:
        self._sessions[session_id] = SessionRoute(
            target=decision.target,
            sensitivity_flag=decision.sensitivity_flag,
            complexity_level=decision.complexity_level,
        )

    def clear(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)


def apply_sticky_routing(
    session_id: str | None,
    store: SessionRouteStore,
    decision: DecideOutput,
) -> DecideOutput:
    """Keep a chat session on the same target unless sensitivity forces an upgrade."""
    if not session_id:
        return decision

    previous = store.get(session_id)
    if previous is None:
        store.remember(session_id, decision)
        return decision

    if (
        decision.sensitivity_flag
        and previous.target == "cloud"
        and decision.target != "large_local"
    ):
        upgraded = DecideOutput(
            target="large_local",
            reason=f"{decision.reason}; session:privacy_upgrade->large_local",
            complexity_level=decision.complexity_level,
            sensitivity_flag=decision.sensitivity_flag,
            complexity_score=decision.complexity_score,
            sensitivity_triggers=decision.sensitivity_triggers,
        )
        store.remember(session_id, upgraded)
        return upgraded

    if decision.target != previous.target:
        return DecideOutput(
            target=previous.target,
            reason=f"{decision.reason}; session:sticky->{previous.target}",
            complexity_level=decision.complexity_level,
            sensitivity_flag=decision.sensitivity_flag,
            complexity_score=decision.complexity_score,
            sensitivity_triggers=decision.sensitivity_triggers,
        )

    store.remember(session_id, decision)
    return decision
