from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from typing import List
from config.config import settings


router = APIRouter()


@router.get("/api/v1/files", response_model=List[str])
async def list_files():
    docs_dir = Path(settings.local_docs_dir)
    docs_dir.mkdir(parents=True, exist_ok=True)
    return [p.name for p in docs_dir.glob("*.pdf")]


@router.post("/api/v1/files/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    docs_dir = Path(settings.local_docs_dir)
    docs_dir.mkdir(parents=True, exist_ok=True)
    dest = docs_dir / file.filename
    data = await file.read()
    dest.write_bytes(data)
    return {"filename": file.filename}


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
