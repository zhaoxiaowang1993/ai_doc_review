from common.logger import get_logger
from typing import Optional
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

    async def get_by_id(self, doc_id: str) -> Optional[Document]:
        """根据 ID 获取文档"""
        item = await self.db_client.retrieve_item_by_id("documents", doc_id)
        if item is None:
            return None
        return Document(**item)

    async def get_by_filename(self, filename: str) -> Optional[Document]:
        """根据文件名获取文档（用于文件上传后查找）"""
        items = await self.db_client.retrieve_items_by_values(
            "documents", {"filename": filename}
        )
        if not items:
            return None
        return Document(**items[0])

    async def delete(self, doc_id: str) -> None:
        """删除文档"""
        await self.db_client.delete_item("documents", doc_id)
        logging.info(f"Deleted document: {doc_id}")
