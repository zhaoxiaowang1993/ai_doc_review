import json
from datetime import datetime, timezone
from uuid import uuid4

from common.models import DocumentIR
from services.document_ir import build_docx_ir, build_txt_ir
from services.storage_provider import LocalStorageProvider
from services.documents_service import DocumentsService


IR_DRIVER_VERSION = "ir:v1"


async def build_ir_in_background(
    *,
    doc_id: str,
    owner_id: str,
    original_storage_key: str,
    original_mime_type: str,
    storage: LocalStorageProvider,
    documents_service: DocumentsService,
) -> None:
    await documents_service.update_ir_metadata(
        doc_id,
        owner_id=owner_id,
        ir_status="running",
        ir_driver_version=IR_DRIVER_VERSION,
        ir_error_message=None,
    )

    try:
        path = storage.open(original_storage_key)
        if (original_mime_type or "").startswith("text/plain") or path.suffix.lower() == ".txt":
            data = path.read_bytes()
            ir, fingerprint = build_txt_ir(data)
        else:
            docx_path = path
            if path.suffix.lower() == ".doc":
                raise RuntimeError("暂不支持 .doc 格式，请转换为 .docx 后上传。")
            ir, fingerprint = build_docx_ir(docx_path)

        payload = json.dumps(ir.model_dump(), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        stored = storage.put_object(storage_key=f"objects/{doc_id}.ir.json", mime_type="application/json", data=payload)
        asset_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        await documents_service.assets_repository.create(
            {
                "id": asset_id,
                "document_id": doc_id,
                "kind": "ir_json",
                "storage_provider": stored.storage_provider,
                "storage_key": stored.storage_key,
                "mime_type": stored.mime_type,
                "size_bytes": stored.size_bytes,
                "sha256": stored.sha256,
                "created_at_utc": now,
            }
        )
        await documents_service.update_ir_metadata(
            doc_id,
            owner_id=owner_id,
            ir_status="ready",
            ir_driver_version=IR_DRIVER_VERSION,
            ir_fingerprint=fingerprint,
            ir_error_message=None,
            ir_asset_id=asset_id,
        )
    except Exception as e:
        await documents_service.update_ir_metadata(
            doc_id,
            owner_id=owner_id,
            ir_status="failed",
            ir_error_message=str(e),
        )
