from common.logger import get_logger
from typing import Optional
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
        self, filename: str, subtype_id: str, doc_id: Optional[str] = None
    ) -> Document:
        """
        创建新文档记录。

        Args:
            filename: 文件名
            subtype_id: 文书子类 ID（决定审核时加载哪些规则）
            doc_id: 可选的文档 ID，如果不提供则自动生成

        Returns:
            创建的 Document 对象
        """
        document = Document(
            id=doc_id or str(uuid.uuid4()),
            filename=filename,
            subtype_id=subtype_id,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        return await self.repository.create(document)

    async def get_document(self, doc_id: str) -> Optional[Document]:
        """
        根据文档 ID 获取文档。

        Args:
            doc_id: 文档 ID

        Returns:
            Document 对象，如果不存在则返回 None
        """
        return await self.repository.get_by_id(doc_id)

    async def get_document_by_filename(self, filename: str) -> Optional[Document]:
        """
        根据文件名获取文档。

        Args:
            filename: 文件名

        Returns:
            Document 对象，如果不存在则返回 None
        """
        return await self.repository.get_by_filename(filename)

    async def delete_document(self, doc_id: str) -> None:
        """
        删除文档。

        Args:
            doc_id: 文档 ID
        """
        await self.repository.delete(doc_id)
