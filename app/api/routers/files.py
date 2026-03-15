from uuid import uuid4
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from fastapi.responses import FileResponse
from typing import List
from common.models import Document
from services.documents_service import DocumentsService
from services.storage_provider import LocalStorageProvider
from security.auth import validate_authenticated
from dependencies import get_documents_service, get_issues_service, get_storage_provider
from services.issues_service import IssuesService
import asyncio
import json
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from services.ir_build_service import build_ir_in_background
import hashlib


router = APIRouter()


@router.get("/api/v1/documents", response_model=List[Document])
async def list_documents(
    user=Depends(validate_authenticated),
    documents_service: DocumentsService = Depends(get_documents_service),
    issues_service: IssuesService = Depends(get_issues_service),
):
    docs = await documents_service.list_documents(owner_id=user.oid)
    out: List[Document] = []
    for d in docs:
        status = await issues_service.get_review_status(d.id, owner_id=user.oid)
        out.append(
            d.model_copy(
                update={
                    "review_status": status.get("status"),
                    "review_error_message": status.get("error_message"),
                }
            )
        )
    return out


@router.post("/api/v1/documents")
async def upload_document(
    file: UploadFile = File(...),
    subtype_id: str = Form(...),
    user=Depends(validate_authenticated),
    documents_service: DocumentsService = Depends(get_documents_service),
    storage: LocalStorageProvider = Depends(get_storage_provider),
):
    filename = file.filename or ""
    if filename.lower().endswith(".doc"):
        raise HTTPException(
            status_code=400,
            detail="暂不支持 .doc 格式，请转换为 .docx 后上传。",
        )
    data = await file.read()
    sha256 = hashlib.sha256(data).hexdigest()
    existing = await documents_service.find_existing_by_sha256(owner_id=user.oid, sha256=sha256, subtype_id=subtype_id)
    if existing:
        if (existing.get("mime_type") or "").lower() != "application/pdf" and (existing.get("ir_status") or "") != "ready":
            asyncio.create_task(
                build_ir_in_background(
                    doc_id=existing["id"],
                    owner_id=user.oid,
                    original_storage_key=existing["storage_key"],
                    original_mime_type=existing["mime_type"],
                    storage=storage,
                    documents_service=documents_service,
                )
            )
        return {
            "doc_id": existing["id"],
            "original_filename": existing.get("original_filename"),
            "display_name": existing.get("display_name"),
            "subtype_id": existing.get("subtype_id"),
            "created_at_utc": existing.get("created_at_utc"),
        }

    doc_id = str(uuid4())
    stored = storage.put_upload(doc_id=doc_id, filename=file.filename, data=data)

    document = await documents_service.create_document(
        owner_id=user.oid,
        original_filename=file.filename,
        display_name=file.filename,
        subtype_id=subtype_id,
        storage_provider=stored.storage_provider,
        storage_key=stored.storage_key,
        mime_type=stored.mime_type,
        size_bytes=stored.size_bytes,
        sha256=stored.sha256,
        created_by=user.oid,
        doc_id=doc_id,
    )

    if stored.mime_type != "application/pdf":
        asyncio.create_task(
            build_ir_in_background(
                doc_id=doc_id,
                owner_id=user.oid,
                original_storage_key=stored.storage_key,
                original_mime_type=stored.mime_type,
                storage=storage,
                documents_service=documents_service,
            )
        )

    return {
        "doc_id": document.id,
        "original_filename": document.original_filename,
        "display_name": document.display_name,
        "subtype_id": document.subtype_id,
        "created_at_utc": document.created_at_utc,
    }


@router.get("/api/v1/documents/{doc_id}")
async def get_document(
    doc_id: str,
    user=Depends(validate_authenticated),
    documents_service: DocumentsService = Depends(get_documents_service),
):
    document = await documents_service.get_document(doc_id, owner_id=user.oid)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    return document


@router.get("/api/v1/documents/{doc_id}/file")
async def download_document(
    doc_id: str,
    user=Depends(validate_authenticated),
    documents_service: DocumentsService = Depends(get_documents_service),
    storage: LocalStorageProvider = Depends(get_storage_provider),
):
    document = await documents_service.get_document(doc_id, owner_id=user.oid)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    path = storage.open(document.storage_key)
    name = document.display_name
    return FileResponse(path, media_type=document.mime_type, filename=name)


class IRStatusResponse(BaseModel):
    doc_id: str
    status: str
    error_message: str | None = None


@router.get("/api/v1/documents/{doc_id}/ir-status", response_model=IRStatusResponse)
async def get_ir_status(
    doc_id: str,
    user=Depends(validate_authenticated),
    documents_service: DocumentsService = Depends(get_documents_service),
):
    row = await documents_service.get_document_row(doc_id, owner_id=user.oid)
    if not row:
        raise HTTPException(status_code=404, detail="文档不存在")
    return IRStatusResponse(
        doc_id=doc_id,
        status=row.get("ir_status") or "none",
        error_message=row.get("ir_error_message"),
    )


@router.get("/api/v1/documents/{doc_id}/ir")
async def get_document_ir(
    doc_id: str,
    user=Depends(validate_authenticated),
    documents_service: DocumentsService = Depends(get_documents_service),
    storage: LocalStorageProvider = Depends(get_storage_provider),
):
    row = await documents_service.get_document_row(doc_id, owner_id=user.oid)
    if not row:
        raise HTTPException(status_code=404, detail="文档不存在")
    st = row.get("ir_status") or "none"
    if st != "ready":
        if st == "failed":
            raise HTTPException(status_code=409, detail=row.get("ir_error_message") or "IR 生成失败")
        raise HTTPException(status_code=409, detail="IR 未就绪")
    ir_asset_id = row.get("ir_asset_id")
    if not ir_asset_id:
        raise HTTPException(status_code=404, detail="IR 不存在")
    asset = await documents_service.assets_repository.get_by_id(ir_asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="IR 不存在")
    path = storage.open(asset["storage_key"])
    data = path.read_bytes()
    return JSONResponse(content=json.loads(data.decode("utf-8")))


@router.get("/api/v1/documents/{doc_id}/issues")
async def get_document_issues(
    doc_id: str,
    user=Depends(validate_authenticated),
    issues_service: IssuesService = Depends(get_issues_service),
):
    issues = await issues_service.get_issues_data(doc_id, owner_id=user.oid)
    if not issues:
        raise HTTPException(status_code=404, detail="not found")
    return issues


@router.delete("/api/v1/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    user=Depends(validate_authenticated),
    documents_service: DocumentsService = Depends(get_documents_service),
    issues_service: IssuesService = Depends(get_issues_service),
    storage: LocalStorageProvider = Depends(get_storage_provider),
):
    document = await documents_service.get_document(doc_id, owner_id=user.oid)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")

    await issues_service.cancel_review(doc_id, owner_id=user.oid)
    await issues_service.issues_repository.delete_issues_by_doc(doc_id, owner_id=user.oid)
    await documents_service.delete_document(doc_id, owner_id=user.oid)
    storage.delete(document.storage_key)
    return {"message": "deleted", "doc_id": doc_id}
