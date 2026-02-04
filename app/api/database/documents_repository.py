from common.logger import get_logger
from typing import List, Optional
from common.models import Document
from database.db_client import SQLiteClient

logging = get_logger(__name__)


class DocumentsRepository:
    """文档数据访问层：负责 documents 表的 CRUD 操作"""

    def __init__(self, db_client: SQLiteClient) -> None:
        self.db_client = db_client

    async def init(self) -> None:
        await self.db_client.init_db()

    async def create(self, document: Document) -> Document:
        """创建新文档记录"""
        item = document.model_dump()
        await self.db_client.store_item("documents", item)
        logging.info(f"Created document: {document.id}")
        return document

    async def get_by_id(self, doc_id: str, *, owner_id: str) -> Optional[Document]:
        rows = await self.db_client.execute_query(
            "SELECT * FROM documents WHERE id = ? AND owner_id = ?",
            (doc_id, owner_id),
        )
        if not rows:
            return None
        return Document(**rows[0])

    async def list_by_owner(self, *, owner_id: str) -> List[Document]:
        rows = await self.db_client.execute_query(
            "SELECT * FROM documents WHERE owner_id = ? ORDER BY created_at_utc DESC",
            (owner_id,),
        )
        return [Document(**r) for r in rows]

    async def update_last_run_id(self, doc_id: str, *, owner_id: str, last_run_id: str | None) -> None:
        rows = await self.db_client.execute_query(
            "SELECT * FROM documents WHERE id = ? AND owner_id = ?",
            (doc_id, owner_id),
        )
        if not rows:
            raise ValueError(f"Document {doc_id} not found.")
        row = dict(rows[0])
        row["last_run_id"] = last_run_id
        await self.db_client.store_item("documents", row)

    async def delete(self, doc_id: str, *, owner_id: str) -> None:
        deleted = await self.db_client.delete_items_by_values(
            "documents",
            {"id": doc_id, "owner_id": owner_id},
        )
        if deleted == 0:
            raise ValueError(f"Document {doc_id} not found.")
        logging.info(f"Deleted document: {doc_id}")
