from pydantic import BaseModel, Field


class ChatQuestionRequest(BaseModel):
    question: str = Field(..., min_length=3)
    top_k: int | None = Field(default=None, ge=1, le=10)
    document_id: int | None = Field(default=None, ge=1)


class ChatSource(BaseModel):
    file_name: str
    page_number: int
    snippet: str


class ChatAnswerResponse(BaseModel):
    answer: str
    sources: list[ChatSource]


class DocumentSummaryRequest(BaseModel):
    document_id: int = Field(..., ge=1)


class DocumentSummaryResponse(BaseModel):
    summary: str
    file_name: str


class DocumentQuestionsRequest(BaseModel):
    document_id: int = Field(..., ge=1)


class DocumentQuestionsResponse(BaseModel):
    questions: list[str]
    file_name: str
