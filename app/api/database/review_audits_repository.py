from typing import Any, Dict, List

from database.db_client import SQLiteClient


class ReviewAuditsRepository:
    def __init__(self, db_client: SQLiteClient) -> None:
        self.db_client = db_client

    async def init(self) -> None:
        await self.db_client.init_db()

    async def create(self, item: Dict[str, Any]) -> Dict[str, Any]:
        await self.db_client.store_item("review_audits", item)
        return item

    async def list_by_doc(self, *, doc_id: str, owner_id: str, limit: int = 200) -> List[Dict[str, Any]]:
        rows = await self.db_client.execute_query(
            "SELECT * FROM review_audits WHERE owner_id = ? AND document_id = ? ORDER BY created_at_utc DESC LIMIT ?",
            (owner_id, doc_id, limit),
        )
        return [dict(r) for r in rows]
