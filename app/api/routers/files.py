from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from fastapi.responses import FileResponse
from pathlib import Path
from typing import List, Optional
from config.config import settings
from services.documents_service import DocumentsService
from dependencies import get_documents_service


router = APIRouter()


@router.get("/api/v1/files", response_model=List[str])
async def list_files():
    docs_dir = Path(settings.local_docs_dir)
    docs_dir.mkdir(parents=True, exist_ok=True)
    return [p.name for p in docs_dir.glob("*.pdf")]


@router.post("/api/v1/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    subtype_id: str = Form(...),
    documents_service: DocumentsService = Depends(get_documents_service),
):
    """
    上传文件并创建文档记录。

    Args:
        file: 上传的 PDF 文件
        subtype_id: 文书子类 ID（决定审核时加载哪些规则）
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    docs_dir = Path(settings.local_docs_dir)
    docs_dir.mkdir(parents=True, exist_ok=True)

    doc_id = file.filename

    dest = docs_dir / file.filename
    data = await file.read()
    dest.write_bytes(data)

    await documents_service.create_document(
        filename=file.filename,
        subtype_id=subtype_id,
        doc_id=doc_id,
    )

    return {
        "filename": file.filename,
        "doc_id": doc_id,
        "subtype_id": subtype_id,
    }


@router.get("/api/v1/files/{filename}")
async def download_file(filename: str):
    docs_dir = Path(settings.local_docs_dir)
    file_path = docs_dir / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="application/pdf", filename=filename)


@router.delete("/api/v1/files/{filename}")
async def delete_file(filename: str):
    """删除指定的 PDF 文件"""
    docs_dir = Path(settings.local_docs_dir)
    file_path = docs_dir / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    file_path.unlink()
    return {"message": "File deleted", "filename": filename}


# ========== Document Endpoints ==========

@router.get("/api/v1/documents/{doc_id}")
async def get_document(
    doc_id: str,
    documents_service: DocumentsService = Depends(get_documents_service),
):
    """获取文档元数据（含分类信息）"""
    document = await documents_service.get_document(doc_id)
    if not document:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
    return document
