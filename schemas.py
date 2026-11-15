from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ChatMessage(Model):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(Model):
    question: str = Field(min_length=1)
    history: list[ChatMessage] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_question(self) -> "ChatRequest":
        if not self.question.strip():
            raise ValueError("Введите вопрос")
        return self


class Fragment(Model):
    source_id: str = Field(min_length=1)
    fragment_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    section: str | None
    text: str = Field(min_length=1)


class SearchRequest(Model):
    query: str = Field(min_length=1)
    event_date: date | None = None
    event_date_end: date | None = None

    @model_validator(mode="after")
    def check_period(self) -> "SearchRequest":
        if self.event_date_end and (not self.event_date or self.event_date_end < self.event_date):
            raise ValueError("Invalid event period")
        return self


class SearchResult(Model):
    status: Literal["ok", "not_found", "date_required", "edition_unavailable"]
    fragments: list[Fragment]

    @model_validator(mode="after")
    def check_fragments(self) -> "SearchResult":
        if (self.status == "ok") != bool(self.fragments):
            raise ValueError("Only an ok search result must contain fragments")
        return self


class Citation(Model):
    source_id: str = Field(min_length=1)
    fragment_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    section: str | None
    quote: str = Field(min_length=1)


class ChatResponse(Model):
    status: Literal["answered", "partial", "clarify", "insufficient", "refused"]
    answer: str = Field(min_length=1)
    citations: list[Citation]


class Document(Model):
    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    text: str = Field(min_length=1)


class ApiError(Model):
    error: str
