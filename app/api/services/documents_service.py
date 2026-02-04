from common.logger import get_logger
from typing import List, Optional
from common.models import Document
from database.documents_repository import DocumentsRepository
from datetime import datetime, timezone
import uuid

logging = get_logger(__name__)


class DocumentsService:
    """文档业务逻辑层：封装文档管理相关业务逻辑"""

    def __init__(self, repository: DocumentsRepository) -> None:
        self.repository = repository

    async def create_document(
        self,
        *,
        owner_id: str,
        original_filename: str,
        display_name: str,
        subtype_id: str,
        storage_provider: str,
        storage_key: str,
        mime_type: str,
        size_bytes: int,
        sha256: str,
        created_by: str,
        doc_id: Optional[str] = None,
    ) -> Document:
        document = Document(
            id=doc_id or str(uuid.uuid4()),
            owner_id=owner_id,
            original_filename=original_filename,
            display_name=display_name,
            subtype_id=subtype_id,
            storage_provider=storage_provider,
            storage_key=storage_key,
            mime_type=mime_type,
            size_bytes=size_bytes,
            sha256=sha256,
            created_at_utc=datetime.now(timezone.utc).isoformat(),
            created_by=created_by,
            last_run_id=None,
        )
        return await self.repository.create(document)

    async def get_document(self, doc_id: str, *, owner_id: str) -> Optional[Document]:
        return await self.repository.get_by_id(doc_id, owner_id=owner_id)

    async def list_documents(self, *, owner_id: str) -> List[Document]:
        return await self.repository.list_by_owner(owner_id=owner_id)

    async def update_last_run_id(self, doc_id: str, *, owner_id: str, last_run_id: str | None) -> None:
        await self.repository.update_last_run_id(doc_id, owner_id=owner_id, last_run_id=last_run_id)

    async def delete_document(self, doc_id: str, *, owner_id: str) -> None:
        await self.repository.delete(doc_id, owner_id=owner_id)
