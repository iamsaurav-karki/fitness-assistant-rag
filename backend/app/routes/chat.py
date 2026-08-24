import logging

from fastapi import APIRouter, HTTPException

from app.models.chat import ChatRequest, ChatResponse
from app.services.rag import RagService


router = APIRouter(prefix="/api")
rag_service = RagService()
logger = logging.getLogger(__name__)


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        answer, sources = rag_service.answer(request.question)
        return ChatResponse(answer=answer, sources=sources)
    except Exception:
        logger.exception("chat_request_failed")
        raise HTTPException(status_code=502, detail="The fitness assistant is temporarily unavailable.") from None