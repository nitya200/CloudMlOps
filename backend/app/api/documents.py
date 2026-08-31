"""Document endpoints (UC-05 Upload document)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, UploadFile, status

from app.api.deps import CurrentUser, DbSession, Pagination
from app.core.config import settings
from app.core.exceptions import PayloadTooLargeError, ValidationError
from app.schemas.common import MessageResponse, Page
from app.schemas.document import (
    DocumentDetailResponse,
    DocumentResponse,
    DocumentUploadResponse,
)
from app.services.document_service import DocumentService
from app.services.extraction_service import DocumentExtractorFactory
from app.utils.text_utils import preview

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("/supported-types", summary="List the file types the platform can read")
def supported_types() -> dict[str, object]:
    return {
        "types": DocumentExtractorFactory.supported_types(),
        "max_size_mb": settings.max_upload_size_mb,
    }


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF, DOCX or TXT document and extract its text",
    responses={
        413: {"description": "File exceeds the configured size limit"},
        415: {"description": "Unsupported or mismatched file type"},
        422: {"description": "No readable text could be extracted"},
    },
)
async def upload_document(
    current_user: CurrentUser,
    db: DbSession,
    file: Annotated[UploadFile, File(description="PDF, DOCX or TXT file")],
) -> DocumentUploadResponse:
    """Validate, store and extract text from an uploaded document.

    Validation covers the extension, the declared MIME type, the byte size and
    the file's magic bytes, so a renamed executable cannot slip through.
    """
    if not file.filename:
        raise ValidationError("A file is required.")

    # Read one byte past the limit: enough to detect an oversized upload
    # without pulling an arbitrarily large body into memory.
    limit = settings.max_upload_size_bytes
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise PayloadTooLargeError(
            f"File is larger than the {settings.max_upload_size_mb} MB limit."
        )

    document = DocumentService(db).upload(
        current_user,
        filename=file.filename,
        content_type=file.content_type,
        data=data,
    )
    return DocumentUploadResponse(
        id=document.id,
        filename=document.filename,
        file_type=document.file_type,
        size_bytes=document.size_bytes,
        page_count=document.page_count,
        word_count=document.word_count,
        created_at=document.created_at,
        extracted_characters=document.character_count,
        text_preview=preview(document.extracted_text, 500),
    )


@router.get(
    "",
    response_model=Page[DocumentResponse],
    summary="List the current user's uploaded documents",
)
def list_documents(
    current_user: CurrentUser,
    db: DbSession,
    pagination: Pagination,
) -> Page[DocumentResponse]:
    documents, total = DocumentService(db).list_for_user(
        current_user, limit=pagination.limit, offset=pagination.offset
    )
    return Page.build(
        [DocumentResponse.model_validate(document) for document in documents],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentDetailResponse,
    summary="Get a document with its extracted text",
    responses={404: {"description": "Document not found or not owned by the caller"}},
)
def get_document(
    document_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> DocumentDetailResponse:
    document = DocumentService(db).get_owned(current_user, document_id)
    return DocumentDetailResponse.model_validate(document)


@router.delete(
    "/{document_id}",
    response_model=MessageResponse,
    summary="Delete a document and its stored file",
)
def delete_document(
    document_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> MessageResponse:
    DocumentService(db).delete(current_user, document_id)
    return MessageResponse(message="Document deleted.")
