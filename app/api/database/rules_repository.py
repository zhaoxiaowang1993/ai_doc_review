from common.logger import get_logger
from typing import Any, Dict, List
from common.models import ReviewRule, DocumentRuleAssociation
from database.db_client import SQLiteClient
import json

logging = get_logger(__name__)


class RulesRepository:
    def __init__(self, db_client: SQLiteClient) -> None:
        self.db_client = db_client

    async def init(self) -> None:
        await self.db_client.init_db()

    # ========== Rules CRUD ==========

    async def get_all_rules(self) -> List[ReviewRule]:
        logging.info("Retrieving all rules.")
        items = await self.db_client.retrieve_items_by_values("rules", {})
        logging.info(f"Retrieved {len(items)} rules.")
        return [ReviewRule(**self._deserialize_rule(item)) for item in items]

    async def get_active_rules(self) -> List[ReviewRule]:
        logging.info("Retrieving active rules.")
        items = await self.db_client.retrieve_items_by_values("rules", {"status": "active"})
        logging.info(f"Retrieved {len(items)} active rules.")
        return [ReviewRule(**self._deserialize_rule(item)) for item in items]

    async def get_rule(self, rule_id: str) -> ReviewRule:
        item = await self.db_client.retrieve_item_by_id("rules", rule_id)
        if not item:
            raise ValueError(f"Rule {rule_id} not found.")
        return ReviewRule(**self._deserialize_rule(item))

    async def create_rule(self, rule: ReviewRule) -> ReviewRule:
        logging.info(f"Creating rule: {rule.name}")
        await self.db_client.store_item("rules", self._serialize_rule(rule))
        logging.info(f"Rule {rule.id} created successfully.")
        return rule

    async def update_rule(self, rule_id: str, fields: Dict[str, Any]) -> ReviewRule:
        logging.info(f"Updating rule {rule_id}")
        existing = await self.db_client.retrieve_item_by_id("rules", rule_id)
        if not existing:
            raise ValueError(f"Rule {rule_id} not found.")

        existing.update(fields)
        await self.db_client.store_item("rules", self._serialize_rule_dict(existing))
        logging.info(f"Rule {rule_id} updated.")
        return ReviewRule(**self._deserialize_rule(existing))

    async def delete_rule(self, rule_id: str) -> None:
        logging.info(f"Deleting rule {rule_id}")
        await self.db_client.delete_item("rules", rule_id)
        # Also delete document associations
        await self.db_client.delete_items_by_values("document_rules", {"rule_id": rule_id})
        logging.info(f"Rule {rule_id} deleted.")

    # ========== Document-Rule Associations ==========

    async def get_document_rules(self, doc_id: str) -> List[DocumentRuleAssociation]:
        logging.info(f"Retrieving rule associations for document {doc_id}")
        items = await self.db_client.retrieve_items_by_values("document_rules", {"doc_id": doc_id})
        return [DocumentRuleAssociation(
            doc_id=item["doc_id"],
            rule_id=item["rule_id"],
            enabled=bool(item["enabled"])
        ) for item in items]

    async def get_enabled_rules_for_document(self, doc_id: str) -> List[ReviewRule]:
        """Get all rules that are enabled for a specific document."""
        logging.info(f"Retrieving enabled rules for document {doc_id}")
        query = """
            SELECT r.* FROM rules r
            INNER JOIN document_rules dr ON r.id = dr.rule_id
            WHERE dr.doc_id = ? AND dr.enabled = 1 AND r.status = 'active'
        """
        items = await self.db_client.execute_query(query, (doc_id,))
        rules = [ReviewRule(**self._deserialize_rule(item)) for item in items]
        logging.info(f"Found {len(rules)} enabled rules for document {doc_id}")
        return rules

    async def set_document_rule(self, doc_id: str, rule_id: str, enabled: bool) -> None:
        logging.info(f"Setting rule {rule_id} for document {doc_id}: enabled={enabled}")
        await self.db_client.store_item("document_rules", {
            "doc_id": doc_id,
            "rule_id": rule_id,
            "enabled": 1 if enabled else 0
        })

    async def delete_document_rules(self, doc_id: str) -> None:
        logging.info(f"Deleting all rule associations for document {doc_id}")
        await self.db_client.delete_items_by_values("document_rules", {"doc_id": doc_id})

    # ========== Serialization ==========

    def _serialize_rule(self, rule: ReviewRule) -> Dict[str, Any]:
        data = rule.model_dump()
        if "examples" in data and data["examples"] is not None:
            data["examples"] = json.dumps(data["examples"], ensure_ascii=False)
        return data

    def _serialize_rule_dict(self, item: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(item)
        if "examples" in out and out["examples"] is not None:
            if isinstance(out["examples"], (list, dict)):
                out["examples"] = json.dumps(out["examples"], ensure_ascii=False)
        return out

    def _deserialize_rule(self, item: Dict[str, Any]) -> Dict[str, Any]:
        if "examples" in item and item["examples"] and isinstance(item["examples"], str):
            try:
                item["examples"] = json.loads(item["examples"])
            except Exception:
                item["examples"] = []
        return item
