from common.logger import get_logger
from typing import Any, Dict, List, Optional
from common.models import Issue
from database.db_client import SQLiteClient

logging = get_logger(__name__)


class IssuesRepository:
    def __init__(self, db_client: SQLiteClient) -> None:
        self.db_client = db_client

    async def init(self) -> None:
        await self.db_client.init_db()

    async def get_issues(self, doc_id: str, *, owner_id: str) -> List[Issue]:
        logging.info(f"Retrieving issues for document {doc_id}.")
        items = await self.db_client.retrieve_items_by_values(
            "issues",
            {"document_id": doc_id, "owner_id": owner_id},
        )
        logging.info(f"Retrieved {len(items)} issues for document {doc_id}.")
        return [Issue(**self._deserialize_issue(self._deserialize_issue_row(item))) for item in items]

    async def get_issue(self, issue_id: str, *, owner_id: str) -> Issue:
        rows = await self.db_client.execute_query(
            "SELECT * FROM issues WHERE id = ? AND owner_id = ?",
            (issue_id, owner_id),
        )
        item = rows[0] if rows else None
        if not item:
            raise ValueError(f"Issue {issue_id} not found.")
        return Issue(**self._deserialize_issue(self._deserialize_issue_row(item)))

    async def store_issues(self, issues: List[Issue]) -> None:
        logging.info(f"Storing {len(issues)} issues in the database.")
        for issue in issues:
            await self.db_client.store_item("issues", self._serialize_issue(issue))
        logging.info("Issues stored successfully.")

    async def update_issue(self, issue_id: str, *, owner_id: str, fields: Dict[str, Any]) -> Issue:
        logging.info(f"Updating issue {issue_id}")
        rows = await self.db_client.execute_query(
            "SELECT * FROM issues WHERE id = ? AND owner_id = ?",
            (issue_id, owner_id),
        )
        existing = rows[0] if rows else None
        if not existing:
            raise ValueError(f"Issue {issue_id} not found.")

        existing.update(fields)
        # Ensure nested objects are stored as JSON strings (SQLite doesn't support dict binding).
        await self.db_client.store_item("issues", self._serialize_issue_dict(existing))
        logging.info(f"Issue {issue_id} updated.")
        return Issue(**self._deserialize_issue(self._deserialize_issue_row(existing)))

    def _serialize_issue_dict(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a DB row/update dict into SQLite-storable types.
        - Keep primitive fields as-is.
        - JSON-encode nested dict/list fields into TEXT columns.
        """
        import json

        out = dict(item)
        for key in ["location", "modified_fields", "dismissal_feedback", "feedback"]:
            if key not in out or out[key] is None:
                continue
            if isinstance(out[key], (dict, list)):
                out[key] = json.dumps(out[key], ensure_ascii=False)
        return out

    def _serialize_issue(self, issue: Issue) -> Dict[str, Any]:
        import json
        data = issue.model_dump()
        if "doc_id" in data:
            data["document_id"] = data.pop("doc_id")
        # Flatten nested objects to JSON strings for SQLite storage
        for key in ["location", "modified_fields", "dismissal_feedback", "feedback"]:
            if key in data and data[key] is not None:
                data[key] = json.dumps(data[key])
        return data

    def _deserialize_issue_row(self, item: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(item)
        if "document_id" in out and "doc_id" not in out:
            out["doc_id"] = out.pop("document_id")
        return out

    def _deserialize_issue(self, item: Dict[str, Any]) -> Dict[str, Any]:
        import json
        for key in ["location", "modified_fields", "dismissal_feedback", "feedback"]:
            if key in item and item[key] and isinstance(item[key], str):
                try:
                    item[key] = json.loads(item[key])
                except Exception:
                    pass
        return item

    async def delete_issues_by_doc(self, doc_id: str, *, owner_id: str) -> int:
        """Delete all issues for a document. Returns number of deleted items."""
        logging.info(f"Deleting issues for document {doc_id}")
        count = await self.db_client.delete_items_by_values(
            "issues",
            {"document_id": doc_id, "owner_id": owner_id},
        )
        logging.info(f"Deleted {count} issues for document {doc_id}")
        return count

    async def any_issues_exist_for_doc(self, doc_id: str, *, owner_id: str) -> bool:
        rows = await self.db_client.execute_query(
            "SELECT 1 FROM issues WHERE document_id = ? AND owner_id = ? LIMIT 1",
            (doc_id, owner_id),
        )
        return bool(rows)

    async def get_distinct_source_run_id_for_doc(self, doc_id: str, *, owner_id: str) -> Optional[str]:
        rows = await self.db_client.execute_query(
            "SELECT source_run_id FROM issues WHERE document_id = ? AND owner_id = ? ORDER BY review_initiated_at_UTC DESC LIMIT 1",
            (doc_id, owner_id),
        )
        if not rows:
            return None
        return rows[0].get("source_run_id")
