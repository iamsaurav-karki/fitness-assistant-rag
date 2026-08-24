from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class Source(BaseModel):
    document: str
    uri: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]