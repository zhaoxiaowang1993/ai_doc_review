from common.logger import get_logger
from typing import List, Optional
from common.models import Document
from database.documents_repository import DocumentsRepository
from database.document_assets_repository import DocumentAssetsRepository
from datetime import datetime, timezone
import uuid

logging = get_logger(__name__)


class DocumentsService:
    """文档业务逻辑层：封装文档管理相关业务逻辑"""

    def __init__(self, repository: DocumentsRepository, assets_repository: DocumentAssetsRepository) -> None:
        self.repository = repository
        self.assets_repository = assets_repository

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
        now = datetime.now(timezone.utc).isoformat()
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
            created_at_utc=now,
            created_by=created_by,
            last_run_id=None,
        )
        created = await self.repository.create(document)
        asset_id = str(uuid.uuid4())
        kind = "review_pdf" if (mime_type or "").lower().startswith("application/pdf") else "original"
        await self.assets_repository.create(
            {
                "id": asset_id,
                "document_id": created.id,
                "kind": kind,
                "storage_provider": storage_provider,
                "storage_key": storage_key,
                "mime_type": mime_type,
                "size_bytes": size_bytes,
                "sha256": sha256,
                "created_at_utc": now,
            }
        )
        await self.repository.update_fields(
            created.id,
            owner_id=owner_id,
            fields={
                "primary_asset_id": asset_id,
                "review_asset_id": asset_id,
            },
        )
        return created

    async def get_document(self, doc_id: str, *, owner_id: str) -> Optional[Document]:
        return await self.repository.get_by_id(doc_id, owner_id=owner_id)

    async def get_document_row(self, doc_id: str, *, owner_id: str) -> Optional[dict]:
        return await self.repository.get_row_by_id(doc_id, owner_id=owner_id)

    async def find_existing_by_sha256(self, *, owner_id: str, sha256: str, subtype_id: str) -> Optional[dict]:
        return await self.repository.find_by_sha256(owner_id=owner_id, sha256=sha256, subtype_id=subtype_id)

    async def list_documents(self, *, owner_id: str) -> List[Document]:
        return await self.repository.list_by_owner(owner_id=owner_id)

    async def update_last_run_id(self, doc_id: str, *, owner_id: str, last_run_id: str | None) -> None:
        await self.repository.update_last_run_id(doc_id, owner_id=owner_id, last_run_id=last_run_id)

    async def delete_document(self, doc_id: str, *, owner_id: str) -> None:
        await self.repository.delete(doc_id, owner_id=owner_id)

    async def update_ir_metadata(
        self,
        doc_id: str,
        *,
        owner_id: str,
        ir_status: str | None = None,
        ir_driver_version: str | None = None,
        ir_fingerprint: str | None = None,
        ir_error_message: str | None = None,
        ir_asset_id: str | None = None,
    ) -> None:
        fields: dict = {}
        if ir_status is not None:
            fields["ir_status"] = ir_status
        if ir_driver_version is not None:
            fields["ir_driver_version"] = ir_driver_version
        if ir_fingerprint is not None:
            fields["ir_fingerprint"] = ir_fingerprint
        if ir_error_message is not None:
            fields["ir_error_message"] = ir_error_message
        if ir_asset_id is not None:
            fields["ir_asset_id"] = ir_asset_id
        if fields:
            await self.repository.update_fields(doc_id, owner_id=owner_id, fields=fields)
