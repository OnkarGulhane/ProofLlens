"""Document Ingestion, Validation, Page-Aware Parsing and Storage Service."""

import hashlib
import io
import os
import uuid
from typing import List, Tuple
from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import (
    DocumentValidationError,
    DocumentNotFoundError,
    WorkspaceNotFoundError,
)
from app.models.workspace import Workspace
from app.models.document import Document, DocumentPage


class DocumentService:
    """Service handling PDF ingestion, validation, page extraction, and storage."""

    @staticmethod
    def compute_sha256(content: bytes) -> str:
        """Computes the SHA-256 hash of byte content."""
        return hashlib.sha256(content).hexdigest()

    @classmethod
    def validate_pdf_content(cls, content: bytes, filename: str) -> None:
        """Validates PDF file size and magic bytes."""
        if not content or len(content) == 0:
            raise DocumentValidationError(f"File '{filename}' is empty.")

        if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
            max_mb = settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
            raise DocumentValidationError(
                f"File '{filename}' exceeds maximum allowable size of {max_mb}MB."
            )

        # Validate PDF magic bytes: standard PDFs start with '%PDF-'
        if not content.startswith(b"%PDF"):
            raise DocumentValidationError(
                f"File '{filename}' is not a valid PDF document (invalid magic bytes)."
            )

    @classmethod
    def extract_pages_from_pdf(cls, content: bytes, filename: str) -> Tuple[int, List[Tuple[int, str]]]:
        """
        Extracts text from PDF bytes page by page.
        Returns:
            (total_pages, list of (page_number, page_text))
        Raises:
            DocumentValidationError if file is corrupted or is a scanned image without text.
        """
        try:
            pdf_file = io.BytesIO(content)
            reader = PdfReader(pdf_file)
            total_pages = len(reader.pages)

            if total_pages == 0:
                raise DocumentValidationError(f"PDF document '{filename}' contains 0 pages.")

            extracted_pages: List[Tuple[int, str]] = []
            total_characters = 0

            for index, page in enumerate(reader.pages):
                page_number = index + 1
                try:
                    text = page.extract_text() or ""
                except Exception as extract_err:
                    logger.warning(f"Error extracting text from page {page_number} of '{filename}': {extract_err}")
                    text = ""

                # Normalize whitespace and strip null bytes
                clean_text = text.replace("\x00", "").strip()
                extracted_pages.append((page_number, clean_text))
                total_characters += len(clean_text)

            # Heuristic for scanned/image-only PDFs
            avg_chars_per_page = total_characters / total_pages
            if avg_chars_per_page < 40:
                raise DocumentValidationError(
                    f"Uploaded PDF '{filename}' appears to be a scanned image or lacks a digital text layer "
                    f"(average {avg_chars_per_page:.1f} chars/page). Scanned PDFs are not supported in MVP."
                )

            return total_pages, extracted_pages

        except DocumentValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to parse PDF document '{filename}': {e}")
            raise DocumentValidationError(f"Failed to parse PDF document '{filename}': {str(e)}")

    @classmethod
    async def process_and_store_document(
        cls,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        filename: str,
        content: bytes,
    ) -> Document:
        """
        Validates, saves to disk, extracts pages, and creates Document and DocumentPage records.
        """
        # 1. Verify workspace exists
        ws_stmt = select(Workspace).where(Workspace.id == workspace_id)
        ws_res = await session.execute(ws_stmt)
        workspace = ws_res.scalar_one_or_none()
        if not workspace:
            raise WorkspaceNotFoundError(str(workspace_id))

        # 2. Validate PDF file
        cls.validate_pdf_content(content, filename)
        file_hash = cls.compute_sha256(content)

        # 3. Check duplicate file hash in this workspace
        dup_stmt = select(Document).where(
            Document.workspace_id == workspace_id,
            Document.file_hash_sha256 == file_hash,
        )
        dup_res = await session.execute(dup_stmt)
        if dup_res.scalar_one_or_none() is not None:
            raise DocumentValidationError(
                f"A document with identical content already exists in workspace '{workspace.title}'."
            )

        # 4. Extract page-aware text
        total_pages, extracted_pages = cls.extract_pages_from_pdf(content, filename)

        # 5. Save PDF binary to local storage
        doc_id = uuid.uuid4()
        storage_dir = settings.STORAGE_DIR
        os.makedirs(storage_dir, exist_ok=True)
        disk_filename = f"{doc_id}.pdf"
        disk_path = os.path.join(storage_dir, disk_filename)

        with open(disk_path, "wb") as f:
            f.write(content)

        # 6. Create Document record
        document = Document(
            id=doc_id,
            workspace_id=workspace_id,
            filename=filename,
            file_path=disk_path,
            file_hash_sha256=file_hash,
            file_size_bytes=len(content),
            total_pages=total_pages,
            status="READY",
        )
        session.add(document)

        # 7. Create DocumentPage records
        for page_number, raw_text in extracted_pages:
            page_record = DocumentPage(
                id=uuid.uuid4(),
                document_id=doc_id,
                page_number=page_number,
                raw_text=raw_text,
                character_count=len(raw_text),
            )
            session.add(page_record)

        # 8. Generate Chunks and Embeddings (Phase 4)
        from app.services.chunking_service import ChunkingService
        from app.services.embedding_service import get_embedding_provider
        from app.models.chunk import DocumentChunk

        chunks = ChunkingService.chunk_document_pages(extracted_pages)
        if chunks:
            chunk_texts = [c.content for c in chunks]
            embedding_provider = get_embedding_provider()
            embeddings = await embedding_provider.embed_texts(chunk_texts)

            for chunk_item, vector in zip(chunks, embeddings):
                chunk_record = DocumentChunk(
                    id=uuid.uuid4(),
                    document_id=doc_id,
                    workspace_id=workspace_id,
                    page_number=chunk_item.page_number,
                    chunk_index=chunk_item.chunk_index,
                    content=chunk_item.content,
                    token_count=chunk_item.token_count,
                    embedding=vector,
                )
                session.add(chunk_record)

        await session.commit()
        await session.refresh(document)
        # Attach runtime chunk_count attribute for schema serialization
        document.chunk_count = len(chunks)
        logger.info(
            f"Successfully ingested document '{filename}' (ID: {doc_id}) with {total_pages} pages and {len(chunks)} embedded chunks into workspace {workspace_id}."
        )
        return document

    @classmethod
    async def list_documents(
        cls,
        session: AsyncSession,
        workspace_id: uuid.UUID,
    ) -> List[Document]:
        """Lists all documents belonging to a workspace with their chunk counts."""
        from sqlalchemy import func
        from app.models.chunk import DocumentChunk

        stmt = (
            select(Document, func.count(DocumentChunk.id).label("chunk_count"))
            .outerjoin(DocumentChunk, Document.id == DocumentChunk.document_id)
            .where(Document.workspace_id == workspace_id)
            .group_by(Document.id)
            .order_by(Document.created_at.desc())
        )
        result = await session.execute(stmt)
        docs = []
        for doc, count in result.all():
            doc.chunk_count = count
            docs.append(doc)
        return docs

    @classmethod
    async def get_document(
        cls,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> Document:
        """Retrieves a single document with its pages and chunk count."""
        from sqlalchemy import func
        from app.models.chunk import DocumentChunk

        stmt = select(Document).where(
            Document.id == document_id,
            Document.workspace_id == workspace_id,
        )
        result = await session.execute(stmt)
        document = result.scalar_one_or_none()
        if not document:
            raise DocumentNotFoundError(str(document_id))

        # Query chunk count
        count_stmt = select(func.count(DocumentChunk.id)).where(DocumentChunk.document_id == document_id)
        count_res = await session.execute(count_stmt)
        document.chunk_count = count_res.scalar_one()
        return document

    @classmethod
    async def delete_document(
        cls,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> None:
        """Deletes a document from the database and removes its file from disk."""
        document = await cls.get_document(session, workspace_id, document_id)

        # Remove file from disk
        if os.path.exists(document.file_path):
            try:
                os.remove(document.file_path)
                logger.info(f"Removed physical file from disk: {document.file_path}")
            except Exception as e:
                logger.warning(f"Failed to remove file from disk {document.file_path}: {e}")

        # Delete from DB (cascades to pages and chunks)
        await session.delete(document)
        await session.commit()
        logger.info(f"Deleted document {document_id} from workspace {workspace_id}.")
