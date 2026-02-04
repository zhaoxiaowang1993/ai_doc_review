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


router = APIRouter()


@router.get("/api/v1/documents", response_model=List[Document])
async def list_documents(
    user=Depends(validate_authenticated),
    documents_service: DocumentsService = Depends(get_documents_service),
):
    docs = await documents_service.list_documents(owner_id=user.oid)
    return docs


@router.post("/api/v1/documents")
async def upload_document(
    file: UploadFile = File(...),
    subtype_id: str = Form(...),
    user=Depends(validate_authenticated),
    documents_service: DocumentsService = Depends(get_documents_service),
    storage: LocalStorageProvider = Depends(get_storage_provider),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="仅支持 PDF 文件")

    data = await file.read()
    doc_id = str(uuid4())
    stored = storage.put_pdf(doc_id=doc_id, data=data)

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
    if not name.lower().endswith(".pdf"):
        name = f"{name}.pdf"
    return FileResponse(path, media_type=document.mime_type, filename=name)


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

    await issues_service.issues_repository.delete_issues_by_doc(doc_id, owner_id=user.oid)
    await documents_service.delete_document(doc_id, owner_id=user.oid)
    storage.delete(document.storage_key)
    return {"message": "deleted", "doc_id": doc_id}
