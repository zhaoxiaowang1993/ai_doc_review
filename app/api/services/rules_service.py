from common.logger import get_logger
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from common.models import (
    ReviewRule, RiskLevel, RuleExample, RuleStatusEnum,
    RuleTypeEnum, RuleSourceEnum, DocumentType, DocumentSubtype
)
from database.rules_repository import RulesRepository

logging = get_logger(__name__)

class RuleValidationError(Exception):
    pass


class RulesService:
    def __init__(self, rules_repository: RulesRepository) -> None:
        self.rules_repository = rules_repository

    # ========== Rules CRUD ==========

    async def get_all_rules(self) -> List[ReviewRule]:
        return await self.rules_repository.get_all_rules()

    async def get_active_rules(self) -> List[ReviewRule]:
        return await self.rules_repository.get_active_rules()

    async def get_rule(self, rule_id: str) -> ReviewRule:
        return await self.rules_repository.get_rule(rule_id)

    async def create_rule(
        self,
        name: str,
        description: str,
        risk_level: RiskLevel,
        examples: Optional[List[RuleExample]] = None,
        rule_type: RuleTypeEnum = RuleTypeEnum.applicable,
        source: RuleSourceEnum = RuleSourceEnum.custom,
        is_universal: Optional[bool] = None,
        type_ids: Optional[List[str]] = None,
        subtype_ids: Optional[List[str]] = None,
    ) -> ReviewRule:
        resolved_type_ids = list(type_ids or [])
        resolved_subtype_ids = list(subtype_ids or [])

        if "universal" in resolved_subtype_ids:
            if is_universal is False:
                raise RuleValidationError("选择通用规则时，不可同时选择具体类型/子类型")
            is_universal = True
            resolved_subtype_ids = [sid for sid in resolved_subtype_ids if sid != "universal"]

        if is_universal is None:
            is_universal = False

        document_type_ids = {t.id for t in await self.rules_repository.get_all_document_types()}
        moved_type_ids = [sid for sid in resolved_subtype_ids if sid in document_type_ids]
        if moved_type_ids:
            resolved_type_ids.extend(moved_type_ids)
            resolved_subtype_ids = [sid for sid in resolved_subtype_ids if sid not in document_type_ids]

        resolved_type_ids = list(dict.fromkeys(resolved_type_ids))
        resolved_subtype_ids = list(dict.fromkeys(resolved_subtype_ids))

        if is_universal and (resolved_type_ids or resolved_subtype_ids):
            raise RuleValidationError("选择通用规则时，不可同时选择具体类型/子类型")

        rule = ReviewRule(
            id=str(uuid4()),
            name=name,
            description=description,
            risk_level=risk_level,
            examples=examples or [],
            rule_type=rule_type,
            source=source,
            status=RuleStatusEnum.active,
            is_universal=is_universal,
            created_at=datetime.now(timezone.utc).isoformat(),
            type_ids=resolved_type_ids,
            subtype_ids=resolved_subtype_ids,
        )
        created_rule = await self.rules_repository.create_rule(rule)
        if not is_universal:
            if resolved_type_ids:
                await self.rules_repository.set_rule_type_relations(rule.id, resolved_type_ids)
            if resolved_subtype_ids:
                await self.rules_repository.set_rule_subtype_relations(rule.id, resolved_subtype_ids)
        return created_rule

    async def update_rule(self, rule_id: str, fields: Dict[str, Any]) -> ReviewRule:
        fields["updated_at"] = datetime.now(timezone.utc).isoformat()
        subtype_ids = fields.pop("subtype_ids", None)
        type_ids = fields.pop("type_ids", None)
        is_universal = fields.get("is_universal", None)

        if subtype_ids is not None:
            resolved_subtype_ids = list(subtype_ids)
            if "universal" in resolved_subtype_ids:
                if is_universal is False:
                    raise RuleValidationError("选择通用规则时，不可同时选择具体类型/子类型")
                is_universal = True
                fields["is_universal"] = True
                resolved_subtype_ids = [sid for sid in resolved_subtype_ids if sid != "universal"]
            subtype_ids = resolved_subtype_ids

        if subtype_ids is not None:
            document_type_ids = {t.id for t in await self.rules_repository.get_all_document_types()}
            moved_type_ids = [sid for sid in subtype_ids if sid in document_type_ids]
            if moved_type_ids:
                subtype_ids = [sid for sid in subtype_ids if sid not in document_type_ids]
                if type_ids is None:
                    type_ids = []
                type_ids.extend(moved_type_ids)

        if type_ids is not None:
            type_ids = list(dict.fromkeys(type_ids))
        if subtype_ids is not None:
            subtype_ids = list(dict.fromkeys(subtype_ids))

        if is_universal is None and (type_ids is not None or subtype_ids is not None):
            fields["is_universal"] = False
            is_universal = False

        if is_universal is True and ((type_ids and len(type_ids) > 0) or (subtype_ids and len(subtype_ids) > 0)):
            raise RuleValidationError("选择通用规则时，不可同时选择具体类型/子类型")

        updated_rule = await self.rules_repository.update_rule(rule_id, fields)
        if is_universal is True:
            await self.rules_repository.set_rule_type_relations(rule_id, [])
            await self.rules_repository.set_rule_subtype_relations(rule_id, [])
            updated_rule.is_universal = True
            updated_rule.type_ids = []
            updated_rule.subtype_ids = []
            return updated_rule
        if updated_rule.is_universal:
            updated_rule.type_ids = []
            updated_rule.subtype_ids = []
            return updated_rule

        if type_ids is not None:
            await self.rules_repository.set_rule_type_relations(rule_id, type_ids)
            updated_rule.type_ids = type_ids
        else:
            updated_rule.type_ids = await self.rules_repository.get_rule_type_relations(rule_id)
        if subtype_ids is not None:
            await self.rules_repository.set_rule_subtype_relations(rule_id, subtype_ids)
            updated_rule.subtype_ids = subtype_ids
        else:
            updated_rule.subtype_ids = await self.rules_repository.get_rule_subtype_relations(rule_id)
        return updated_rule

    async def delete_rule(self, rule_id: str) -> None:
        await self.rules_repository.delete_rule(rule_id)

    # ========== Document Types ==========

    async def get_all_document_types(self) -> List[DocumentType]:
        return await self.rules_repository.get_all_document_types()

    async def get_document_type(self, type_id: str) -> Optional[DocumentType]:
        return await self.rules_repository.get_document_type(type_id)

    # ========== Document Subtypes ==========

    async def get_all_document_subtypes(self) -> List[DocumentSubtype]:
        return await self.rules_repository.get_all_document_subtypes()

    async def get_subtypes_by_type(self, type_id: str) -> List[DocumentSubtype]:
        return await self.rules_repository.get_subtypes_by_type(type_id)

    async def create_document_subtype(self, subtype: DocumentSubtype) -> DocumentSubtype:
        return await self.rules_repository.create_document_subtype(subtype)

    async def delete_document_subtype(self, subtype_id: str) -> None:
        await self.rules_repository.delete_document_subtype(subtype_id)

    # ========== Rule-Subtype Relations ==========

    async def get_rule_subtype_relations(self, rule_id: str) -> List[str]:
        return await self.rules_repository.get_rule_subtype_relations(rule_id)

    async def get_rules_by_subtype(self, subtype_id: str, include_universal: bool = True) -> List[ReviewRule]:
        return await self.rules_repository.get_rules_by_subtype(subtype_id, include_universal)

    async def get_rules_for_review(self, subtype_id: str) -> List[ReviewRule]:
        """
        获取审核文书时需要加载的规则，支持多级继承。

        Args:
            subtype_id: 文书子类 ID

        Returns:
            适用于该子类的所有活动规则列表（包含子类规则、父类规则、通用规则）
        """
        return await self.rules_repository.get_rules_for_review(subtype_id)

    async def get_rules_by_ids(self, rule_ids: List[str]) -> List[ReviewRule]:
        """Get multiple rules by their IDs."""
        rules = []
        for rule_id in rule_ids:
            try:
                rule = await self.rules_repository.get_rule(rule_id)
                if rule.status == RuleStatusEnum.active:
                    rules.append(rule)
            except ValueError:
                logging.warning(f"Rule {rule_id} not found, skipping.")
        return rules

