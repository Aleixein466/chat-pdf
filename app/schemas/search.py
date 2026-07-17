from pydantic import BaseModel


class SemanticSearchResult(BaseModel):
    chunk_id: int
    document_id: int
    file_name: str
    page_number: int
    chunk_index: int
    content: str
    distance: float


class SemanticSearchResponse(BaseModel):
    question: str
    top_k: int
    results: list[SemanticSearchResult]
