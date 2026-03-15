from common.logger import get_logger
from typing import Any, Dict, List, Optional
from database.db_client import SQLiteClient

logging = get_logger(__name__)


class DocumentAssetsRepository:
    def __init__(self, db_client: SQLiteClient) -> None:
        self.db_client = db_client

    async def init(self) -> None:
        await self.db_client.init_db()

    async def create(self, asset: Dict[str, Any]) -> Dict[str, Any]:
        await self.db_client.store_item("document_assets", asset)
        return asset

    async def get_by_id(self, asset_id: str) -> Optional[Dict[str, Any]]:
        return await self.db_client.retrieve_item_by_id("document_assets", asset_id)

    async def list_by_document(self, document_id: str) -> List[Dict[str, Any]]:
        return await self.db_client.retrieve_items_by_values("document_assets", {"document_id": document_id})

