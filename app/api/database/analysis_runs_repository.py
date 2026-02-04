from common.logger import get_logger
from typing import Any, Dict, Optional
from database.db_client import SQLiteClient

logging = get_logger(__name__)


class AnalysisRunsRepository:
    def __init__(self, db_client: SQLiteClient) -> None:
        self.db_client = db_client

    async def init(self) -> None:
        await self.db_client.init_db()

    async def get_by_id(self, run_id: str, *, owner_id: str) -> Optional[Dict[str, Any]]:
        rows = await self.db_client.execute_query(
            "SELECT * FROM analysis_runs WHERE id = ? AND owner_id = ?",
            (run_id, owner_id),
        )
        return dict(rows[0]) if rows else None

    async def get_by_key(
        self,
        *,
        owner_id: str,
        sha256: str,
        rules_fingerprint: str,
        pipeline_version: str,
    ) -> Optional[Dict[str, Any]]:
        rows = await self.db_client.execute_query(
            """
            SELECT *
            FROM analysis_runs
            WHERE owner_id = ? AND sha256 = ? AND rules_fingerprint = ? AND pipeline_version = ?
            """,
            (owner_id, sha256, rules_fingerprint, pipeline_version),
        )
        return dict(rows[0]) if rows else None

    async def create(self, row: Dict[str, Any]) -> Dict[str, Any]:
        await self.db_client.store_item("analysis_runs", row)
        logging.info(f"Created analysis_run: {row.get('id')}")
        return row

    async def update(self, run_id: str, *, owner_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        existing = await self.get_by_id(run_id, owner_id=owner_id)
        if not existing:
            raise ValueError(f"Analysis run {run_id} not found.")
        existing.update(fields)
        await self.db_client.store_item("analysis_runs", existing)
        return existing
