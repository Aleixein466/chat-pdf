from sqlalchemy.orm import Session

from app.schemas.chat import ChatAnswerResponse, ChatSource
from app.services.ollama_service import OllamaService
from app.services.semantic_search import SemanticSearchService


class ChatService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.ollama_service = OllamaService()
        self.semantic_search_service = SemanticSearchService(db=db, ollama_service=self.ollama_service)

    def ask(
        self,
        question: str,
        top_k: int | None = None,
        document_id: int | None = None,
    ) -> ChatAnswerResponse:
        search_response = self.semantic_search_service.search(
            question=question,
            top_k=top_k,
            document_id=document_id,
        )

        context_blocks = []
        sources: list[ChatSource] = []

        for chunk in search_response.results:
            context_blocks.append(
                f"Archivo: {chunk.file_name}\n"
                f"Pagina: {chunk.page_number}\n"
                f"Contenido: {chunk.content}"
            )
            sources.append(
                ChatSource(
                    file_name=chunk.file_name,
                    page_number=chunk.page_number,
                    snippet=chunk.content[:300],
                )
            )

        context = "\n\n".join(context_blocks)
        answer = self.ollama_service.generate_answer(question=question, context=context)

        return ChatAnswerResponse(answer=answer, sources=sources)
