from common.logger import get_logger
from typing import Any, Dict, Optional

from database.db_client import SQLiteClient

logging = get_logger(__name__)


class ReviewRuleSnapshotsRepository:
    def __init__(self, db_client: SQLiteClient) -> None:
        self.db_client = db_client

    async def init(self) -> None:
        await self.db_client.init_db()

    async def get_by_doc_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        items = await self.db_client.retrieve_items_by_values("review_rule_snapshots", {"doc_id": doc_id})
        if not items:
            return None
        return dict(items[0])

    async def upsert(
        self,
        *,
        doc_id: str,
        reviewed_at_UTC: str,
        subtype_id: str | None,
        rules_snapshot: str,
        rules_fingerprint: str,
    ) -> None:
        await self.db_client.store_item(
            "review_rule_snapshots",
            {
                "doc_id": doc_id,
                "reviewed_at_UTC": reviewed_at_UTC,
                "subtype_id": subtype_id,
                "rules_snapshot": rules_snapshot,
                "rules_fingerprint": rules_fingerprint,
            },
        )

    async def delete_by_doc_id(self, doc_id: str) -> int:
        return await self.db_client.delete_items_by_values("review_rule_snapshots", {"doc_id": doc_id})

