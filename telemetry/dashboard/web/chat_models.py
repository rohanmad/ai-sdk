"""Pydantic models for the chat API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

MAX_CHAT_MESSAGES = 30
MAX_CHAT_CHARS = 12_000


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(..., min_length=1, max_length=8000)


class ChatRequest(BaseModel):
    prompt: str | None = Field(None, min_length=1, max_length=8000)
    messages: list[ChatMessage] | None = None
    session_id: str | None = Field(None, min_length=8, max_length=64)
    stream: bool = False
    max_tokens: int = Field(1024, ge=1, le=2048)
    temperature: float = Field(0.7, ge=0.0, le=2.0)

    @model_validator(mode="after")
    def require_prompt_or_messages(self) -> ChatRequest:
        if not self.prompt and not self.messages:
            raise ValueError("Either prompt or messages is required")
        return self

    def resolved_messages(self) -> list[dict[str, str]]:
        if self.messages:
            raw = [{"role": m.role, "content": m.content} for m in self.messages]
        else:
            raw = [{"role": "user", "content": self.prompt or ""}]

        trimmed = raw[-MAX_CHAT_MESSAGES:]
        total = sum(len(m["content"]) for m in trimmed)
        while trimmed and total > MAX_CHAT_CHARS:
            removed = trimmed.pop(0)
            total -= len(removed["content"])
        return trimmed

    def resolved_prompt(self) -> str:
        for message in reversed(self.resolved_messages()):
            if message["role"] == "user":
                return message["content"]
        return self.resolved_messages()[-1]["content"]


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
