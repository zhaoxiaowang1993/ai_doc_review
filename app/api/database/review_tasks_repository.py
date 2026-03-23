from typing import Any, Dict, List, Optional

from database.db_client import SQLiteClient


class ReviewTasksRepository:
    def __init__(self, db_client: SQLiteClient) -> None:
        self.db_client = db_client

    async def init(self) -> None:
        await self.db_client.init_db()

    async def create(self, task: Dict[str, Any]) -> Dict[str, Any]:
        await self.db_client.store_item("review_tasks", task)
        return task

    async def get_by_id(self, task_id: str, *, owner_id: str) -> Optional[Dict[str, Any]]:
        rows = await self.db_client.execute_query(
            "SELECT * FROM review_tasks WHERE id = ? AND owner_id = ?",
            (task_id, owner_id),
        )
        return dict(rows[0]) if rows else None

    async def list_by_doc(self, doc_id: str, *, owner_id: str) -> List[Dict[str, Any]]:
        rows = await self.db_client.execute_query(
            "SELECT * FROM review_tasks WHERE document_id = ? AND owner_id = ? ORDER BY created_at_utc DESC",
            (doc_id, owner_id),
        )
        return [dict(r) for r in rows]

    async def update_fields(self, task_id: str, *, owner_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        rows = await self.db_client.execute_query(
            "SELECT * FROM review_tasks WHERE id = ? AND owner_id = ?",
            (task_id, owner_id),
        )
        if not rows:
            raise ValueError(f"Task {task_id} not found.")
        row = dict(rows[0])
        row.update(fields)
        await self.db_client.store_item("review_tasks", row)
        return row
