from pydantic import BaseModel


class PageContent(BaseModel):
    page: int
    text: str


class DocumentPagesResponse(BaseModel):
    document_id: int
    file_name: str
    total_pages: int
    pages: list[PageContent]


class UploadDocumentResponse(BaseModel):
    document_id: int
    file_name: str
    pages_processed: int
    chunks_created: int
    message: str


class BatchUploadDocumentResponse(BaseModel):
    processed_count: int
    documents: list[UploadDocumentResponse]


class DocumentListItemResponse(BaseModel):
    document_id: int
    file_name: str
    total_pages: int
    chunks_count: int


class DocumentListResponse(BaseModel):
    total_documents: int
    documents: list[DocumentListItemResponse]
