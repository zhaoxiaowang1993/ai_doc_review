from common.logger import get_logger
from datetime import datetime, timezone
import json
from typing import Any, Dict, List
from uuid import uuid4

from common.models import Issue
from database.db_client import SQLiteClient

logging = get_logger(__name__)


class AnalysisIssuesRepository:
    def __init__(self, db_client: SQLiteClient) -> None:
        self.db_client = db_client

    async def init(self) -> None:
        await self.db_client.init_db()

    async def list_by_run_id(self, run_id: str, *, owner_id: str) -> List[Dict[str, Any]]:
        rows = await self.db_client.execute_query(
            """
            SELECT ai.*
            FROM analysis_issues ai
            INNER JOIN analysis_runs ar ON ar.id = ai.run_id
            WHERE ai.run_id = ? AND ar.owner_id = ?
            ORDER BY ai.created_at_utc ASC
            """,
            (run_id, owner_id),
        )
        return [dict(r) for r in rows]

    async def store_issues(self, run_id: str, issues: List[Issue]) -> List[Dict[str, Any]]:
        now = datetime.now(timezone.utc).isoformat()
        out: List[Dict[str, Any]] = []
        for issue in issues:
            risk_level = issue.risk_level.value if hasattr(issue.risk_level, "value") else issue.risk_level
            row = {
                "id": str(uuid4()),
                "run_id": run_id,
                "type": issue.type,
                "text": issue.text,
                "explanation": issue.explanation,
                "suggested_fix": issue.suggested_fix,
                "risk_level": risk_level,
                "location_json": json.dumps(issue.location.model_dump(), ensure_ascii=False)
                if issue.location is not None
                else None,
                "para_index": (issue.location.para_index if issue.location is not None else None),
                "created_at_utc": now,
            }
            await self.db_client.store_item("analysis_issues", row)
            out.append(row)
        return out
