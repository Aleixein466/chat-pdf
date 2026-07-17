from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models import Document, DocumentChunk
from app.schemas.chat import (
    ChatAnswerResponse,
    ChatQuestionRequest,
    DocumentQuestionsRequest,
    DocumentQuestionsResponse,
    DocumentSummaryRequest,
    DocumentSummaryResponse,
)
from app.services.chat_service import ChatService
from app.services.ollama_service import OllamaService
from app.services.prompt_builder import build_questions_prompt, build_summary_prompt


router = APIRouter()


def _get_document_context(document_id: int, db: Session, max_chunks: int = 8) -> tuple[str, str]:
    """Recupera los primeros N chunks de un documento como contexto y su nombre."""
    doc = db.get(Document, document_id)
    if doc is None:
        raise ValueError("Documento no encontrado.")

    rows = db.execute(
        select(DocumentChunk.content)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.page_number, DocumentChunk.chunk_index)
        .limit(max_chunks)
    ).scalars().all()

    context = "\n\n".join(rows)
    return context, doc.file_name


@router.post("/ask", response_model=ChatAnswerResponse)
def ask_question(payload: ChatQuestionRequest, db: Session = Depends(get_db)) -> ChatAnswerResponse:
    service = ChatService(db)
    return service.ask(question=payload.question, top_k=payload.top_k, document_id=payload.document_id)


@router.post("/summary", response_model=DocumentSummaryResponse)
def get_document_summary(payload: DocumentSummaryRequest, db: Session = Depends(get_db)) -> DocumentSummaryResponse:
    """Genera un resumen del documento usando sus primeros chunks."""
    context, file_name = _get_document_context(payload.document_id, db, max_chunks=10)
    prompt = build_summary_prompt(context)
    ollama = OllamaService()
    summary = ollama.generate_answer(question="resumen", context=prompt.user_message)
    return DocumentSummaryResponse(summary=summary, file_name=file_name)


@router.post("/questions", response_model=DocumentQuestionsResponse)
def get_document_questions(payload: DocumentQuestionsRequest, db: Session = Depends(get_db)) -> DocumentQuestionsResponse:
    """Genera 3 preguntas sugeridas sobre el documento."""
    context, file_name = _get_document_context(payload.document_id, db, max_chunks=8)
    prompt = build_questions_prompt(context)
    ollama = OllamaService()
    raw = ollama.generate_answer(question="preguntas", context=prompt.user_message)
    questions = [q.strip() for q in raw.strip().splitlines() if q.strip()][:3]
    return DocumentQuestionsResponse(questions=questions, file_name=file_name)

