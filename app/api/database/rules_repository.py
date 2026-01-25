from common.logger import get_logger
from typing import Any, Dict, List, Optional
from common.models import (
    ReviewRule, DocumentType, DocumentSubtype, RuleSubtypeRelation
)
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
        rules = []
        for item in items:
            rule_data = self._deserialize_rule(item)
            rule_data["type_ids"] = await self.get_rule_type_relations(rule_data["id"])
            rule_data["subtype_ids"] = await self.get_rule_subtype_relations(rule_data["id"])
            rules.append(ReviewRule(**rule_data))
        return rules

    async def get_active_rules(self) -> List[ReviewRule]:
        logging.info("Retrieving active rules.")
        items = await self.db_client.retrieve_items_by_values("rules", {"status": "active"})
        logging.info(f"Retrieved {len(items)} active rules.")
        rules = []
        for item in items:
            rule_data = self._deserialize_rule(item)
            rule_data["type_ids"] = await self.get_rule_type_relations(rule_data["id"])
            rule_data["subtype_ids"] = await self.get_rule_subtype_relations(rule_data["id"])
            rules.append(ReviewRule(**rule_data))
        return rules

    async def get_rule(self, rule_id: str) -> ReviewRule:
        item = await self.db_client.retrieve_item_by_id("rules", rule_id)
        if not item:
            raise ValueError(f"Rule {rule_id} not found.")
        rule_data = self._deserialize_rule(item)
        rule_data["type_ids"] = await self.get_rule_type_relations(rule_id)
        rule_data["subtype_ids"] = await self.get_rule_subtype_relations(rule_id)
        return ReviewRule(**rule_data)

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
        await self.db_client.delete_items_by_values("rule_subtype_relations", {"rule_id": rule_id})
        await self.db_client.delete_items_by_values("rule_type_relations", {"rule_id": rule_id})
        logging.info(f"Rule {rule_id} deleted.")

    # ========== Document Types CRUD ==========

    async def get_all_document_types(self) -> List[DocumentType]:
        logging.info("Retrieving all document types.")
        items = await self.db_client.retrieve_items_by_values("document_types", {})
        return [DocumentType(**item) for item in items]

    async def get_document_type(self, type_id: str) -> Optional[DocumentType]:
        item = await self.db_client.retrieve_item_by_id("document_types", type_id)
        return DocumentType(**item) if item else None

    async def create_document_type(self, doc_type: DocumentType) -> DocumentType:
        logging.info(f"Creating document type: {doc_type.name}")
        await self.db_client.store_item("document_types", doc_type.model_dump())
        return doc_type

    async def delete_document_type(self, type_id: str) -> None:
        logging.info(f"Deleting document type {type_id}")
        # Also delete all subtypes under this type
        await self.db_client.delete_items_by_values("document_subtypes", {"type_id": type_id})
        await self.db_client.delete_items_by_values("rule_type_relations", {"type_id": type_id})
        await self.db_client.delete_item("document_types", type_id)

    # ========== Document Subtypes CRUD ==========

    async def get_all_document_subtypes(self) -> List[DocumentSubtype]:
        logging.info("Retrieving all document subtypes.")
        items = await self.db_client.retrieve_items_by_values("document_subtypes", {})
        return [DocumentSubtype(**item) for item in items]

    async def get_subtypes_by_type(self, type_id: str) -> List[DocumentSubtype]:
        logging.info(f"Retrieving subtypes for type {type_id}")
        items = await self.db_client.retrieve_items_by_values("document_subtypes", {"type_id": type_id})
        return [DocumentSubtype(**item) for item in items]

    async def get_document_subtype(self, subtype_id: str) -> Optional[DocumentSubtype]:
        item = await self.db_client.retrieve_item_by_id("document_subtypes", subtype_id)
        return DocumentSubtype(**item) if item else None

    async def create_document_subtype(self, subtype: DocumentSubtype) -> DocumentSubtype:
        logging.info(f"Creating document subtype: {subtype.name}")
        await self.db_client.store_item("document_subtypes", subtype.model_dump())
        return subtype

    async def delete_document_subtype(self, subtype_id: str) -> None:
        logging.info(f"Deleting document subtype {subtype_id}")
        # Also delete rule relations
        await self.db_client.delete_items_by_values("rule_subtype_relations", {"subtype_id": subtype_id})
        await self.db_client.delete_item("document_subtypes", subtype_id)

    # ========== Rule-Subtype Relations ==========

    async def get_rule_subtype_relations(self, rule_id: str) -> List[str]:
        """Get all subtype IDs associated with a rule."""
        items = await self.db_client.retrieve_items_by_values("rule_subtype_relations", {"rule_id": rule_id})
        return [item["subtype_id"] for item in items]

    async def set_rule_subtype_relations(self, rule_id: str, subtype_ids: List[str]) -> None:
        """Replace all subtype relations for a rule."""
        logging.info(f"Setting subtype relations for rule {rule_id}: {subtype_ids}")
        # First delete existing relations
        await self.db_client.delete_items_by_values("rule_subtype_relations", {"rule_id": rule_id})
        # Then add new relations
        for subtype_id in subtype_ids:
            await self.db_client.store_item("rule_subtype_relations", {
                "rule_id": rule_id,
                "subtype_id": subtype_id
            })

    # ========== Rule-Type Relations ==========

    async def get_rule_type_relations(self, rule_id: str) -> List[str]:
        items = await self.db_client.retrieve_items_by_values("rule_type_relations", {"rule_id": rule_id})
        return [item["type_id"] for item in items]

    async def set_rule_type_relations(self, rule_id: str, type_ids: List[str]) -> None:
        logging.info(f"Setting type relations for rule {rule_id}: {type_ids}")
        await self.db_client.delete_items_by_values("rule_type_relations", {"rule_id": rule_id})
        for type_id in type_ids:
            await self.db_client.store_item("rule_type_relations", {
                "rule_id": rule_id,
                "type_id": type_id
            })

    async def get_rules_by_subtype(self, subtype_id: str, include_universal: bool = True) -> List[ReviewRule]:
        """Get all active rules associated with a specific subtype."""
        logging.info(f"Retrieving rules for subtype {subtype_id}")
        if include_universal:
            query = """
                SELECT r.* FROM rules r
                WHERE r.status = 'active'
                  AND (
                    r.is_universal = 1
                    OR EXISTS (
                      SELECT 1 FROM rule_subtype_relations rsr
                      WHERE rsr.rule_id = r.id AND rsr.subtype_id = ?
                    )
                  )
            """
        else:
            query = """
                SELECT r.* FROM rules r
                WHERE r.status = 'active'
                  AND EXISTS (
                    SELECT 1 FROM rule_subtype_relations rsr
                    WHERE rsr.rule_id = r.id AND rsr.subtype_id = ?
                  )
            """
        items = await self.db_client.execute_query(query, (subtype_id,))
        rules = []
        for item in items:
            rule_data = self._deserialize_rule(item)
            rule_data["type_ids"] = await self.get_rule_type_relations(rule_data["id"])
            rule_data["subtype_ids"] = await self.get_rule_subtype_relations(rule_data["id"])
            rules.append(ReviewRule(**rule_data))
        logging.info(f"Found {len(rules)} rules for subtype {subtype_id}")
        return rules

    async def get_rules_for_review(self, subtype_id: str) -> List[ReviewRule]:
        """
        获取审核文书时需要加载的规则，支持多级继承：
        1. 加载关联了当前子类的规则
        2. 加载关联了当前子类所属父类的规则
        3. 加载关联了 'universal' 的通用规则

        Args:
            subtype_id: 文书子类 ID

        Returns:
            适用于该子类的所有活动规则列表
        """
        logging.info(f"Getting rules for review with subtype {subtype_id}")

        # 获取子类的父类 ID
        subtype = await self.get_document_subtype(subtype_id)
        type_id = subtype.type_id if subtype else None

        # 构建多级加载查询
        # 匹配规则：子类精确匹配 OR 父类匹配 OR 通用规则
        if type_id:
            query = """
                SELECT r.* FROM rules r
                WHERE r.status = 'active'
                  AND (
                    r.is_universal = 1
                    OR EXISTS (
                      SELECT 1 FROM rule_subtype_relations rsr
                      WHERE rsr.rule_id = r.id AND rsr.subtype_id = ?
                    )
                    OR EXISTS (
                      SELECT 1 FROM rule_type_relations rtr
                      WHERE rtr.rule_id = r.id AND rtr.type_id = ?
                    )
                  )
            """
            params = (subtype_id, type_id)
        else:
            # 如果找不到子类，只加载通用规则
            query = """
                SELECT r.* FROM rules r
                WHERE r.status = 'active' AND r.is_universal = 1
            """
            params = ()

        items = await self.db_client.execute_query(query, params)
        rules = []
        for item in items:
            rule_data = self._deserialize_rule(item)
            rule_data["type_ids"] = await self.get_rule_type_relations(rule_data["id"])
            rule_data["subtype_ids"] = await self.get_rule_subtype_relations(rule_data["id"])
            rules.append(ReviewRule(**rule_data))
        logging.info(f"Found {len(rules)} rules for review (subtype: {subtype_id}, type: {type_id})")
        return rules

    # ========== Serialization ==========

    def _serialize_rule(self, rule: ReviewRule) -> Dict[str, Any]:
        data = rule.model_dump()
        if "examples" in data and data["examples"] is not None:
            data["examples"] = json.dumps(data["examples"], ensure_ascii=False)
        # subtype_ids is stored in a separate relation table, not in rules table
        data.pop("type_ids", None)
        data.pop("subtype_ids", None)
        return data

    def _serialize_rule_dict(self, item: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(item)
        if "examples" in out and out["examples"] is not None:
            if isinstance(out["examples"], (list, dict)):
                out["examples"] = json.dumps(out["examples"], ensure_ascii=False)
        out.pop("type_ids", None)
        out.pop("subtype_ids", None)
        return out

    def _deserialize_rule(self, item: Dict[str, Any]) -> Dict[str, Any]:
        if "examples" in item and item["examples"] and isinstance(item["examples"], str):
            try:
                item["examples"] = json.loads(item["examples"])
            except Exception:
                item["examples"] = []
        # Provide default values for new fields if missing (migration compatibility)
        if "rule_type" not in item or item["rule_type"] is None:
            item["rule_type"] = "applicable"
        if "source" not in item or item["source"] is None:
            item["source"] = "custom"
        if "is_universal" not in item or item["is_universal"] is None:
            item["is_universal"] = 0
        item["is_universal"] = bool(item["is_universal"])
        if "type_ids" not in item:
            item["type_ids"] = []
        # subtype_ids will be populated separately from relation table
        if "subtype_ids" not in item:
            item["subtype_ids"] = []
        return item
