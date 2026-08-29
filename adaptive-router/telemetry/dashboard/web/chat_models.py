"""Pydantic models for the chat API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=8000)
    max_tokens: int = Field(1024, ge=1, le=2048)
    temperature: float = Field(0.7, ge=0.0, le=2.0)


class ChatResponse(BaseModel):
    request_id: str
    text: str
    target: str
    reason: str
    complexity_score: float
    sensitivity_flag: bool
    sensitivity_triggers: list[str]
    latency_ms: float
    model: str
    mock_execution: bool
    finish_reason: str = "stop"


class ChatErrorResponse(BaseModel):
    error: str
    detail: str | None = None
