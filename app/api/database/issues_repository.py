from common.logger import get_logger
from typing import Any, Dict, List
from common.models import Issue
from database.db_client import SQLiteClient

logging = get_logger(__name__)


class IssuesRepository:
    def __init__(self, db_client: SQLiteClient) -> None:
        self.db_client = db_client

    async def init(self) -> None:
        await self.db_client.init_db()

    async def get_issues(self, doc_id: str) -> List[Issue]:
        logging.info(f"Retrieving issues for document {doc_id}.")
        filter = {"doc_id": doc_id}
        items = await self.db_client.retrieve_items_by_values("issues", filter)
        logging.info(f"Retrieved {len(items)} issues for document {doc_id}.")
        return [Issue(**self._deserialize_issue(item)) for item in items]

    async def get_issue(self, issue_id: str) -> Issue:
        item = await self.db_client.retrieve_item_by_id("issues", issue_id)
        if not item:
            raise ValueError(f"Issue {issue_id} not found.")
        return Issue(**self._deserialize_issue(item))

    async def store_issues(self, issues: List[Issue]) -> None:
        logging.info(f"Storing {len(issues)} issues in the database.")
        for issue in issues:
            await self.db_client.store_item("issues", self._serialize_issue(issue))
        logging.info("Issues stored successfully.")

    async def update_issue(self, issue_id: str, fields: Dict[str, Any]) -> Issue:
        logging.info(f"Updating issue {issue_id}")
        existing = await self.db_client.retrieve_item_by_id("issues", issue_id)
        if not existing:
            raise ValueError(f"Issue {issue_id} not found.")

        existing.update(fields)
        # Ensure nested objects are stored as JSON strings (SQLite doesn't support dict binding).
        await self.db_client.store_item("issues", self._serialize_issue_dict(existing))
        logging.info(f"Issue {issue_id} updated.")
        return Issue(**self._deserialize_issue(existing))

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
        # Flatten nested objects to JSON strings for SQLite storage
        for key in ["location", "modified_fields", "dismissal_feedback", "feedback"]:
            if key in data and data[key] is not None:
                data[key] = json.dumps(data[key])
        return data

    def _deserialize_issue(self, item: Dict[str, Any]) -> Dict[str, Any]:
        import json
        for key in ["location", "modified_fields", "dismissal_feedback", "feedback"]:
            if key in item and item[key] and isinstance(item[key], str):
                try:
                    item[key] = json.loads(item[key])
                except Exception:
                    pass
        return item

    async def delete_issues_by_doc(self, doc_id: str) -> int:
        """Delete all issues for a document. Returns number of deleted items."""
        logging.info(f"Deleting issues for document {doc_id}")
        count = await self.db_client.delete_items_by_values("issues", {"doc_id": doc_id})
        logging.info(f"Deleted {count} issues for document {doc_id}")
        return count
