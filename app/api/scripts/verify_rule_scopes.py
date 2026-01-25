import asyncio
import os
import sys
import tempfile


def _ensure_api_on_path() -> None:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    api_root = os.path.join(repo_root, "app", "api")
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    if api_root not in sys.path:
        sys.path.insert(0, api_root)


async def _run() -> None:
    _ensure_api_on_path()

    from database.db_client import SQLiteClient
    from database.rules_repository import RulesRepository
    from services.rules_service import RulesService, RuleValidationError
    from common.models import RiskLevel

    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "verify_rule_scopes.db")

        db_client = SQLiteClient(db_path=db_path)
        rules_repository = RulesRepository(db_client)
        await rules_repository.init()
        rules_service = RulesService(rules_repository)

        universal_rule = await rules_service.create_rule(
            name="通用规则",
            description="适用于所有文书",
            risk_level=RiskLevel.low,
            is_universal=True,
            type_ids=[],
            subtype_ids=[],
        )
        type_rule = await rules_service.create_rule(
            name="父类规则",
            description="适用于法律合同类型",
            risk_level=RiskLevel.medium,
            is_universal=False,
            type_ids=["type_legal"],
            subtype_ids=[],
        )
        subtype_rule = await rules_service.create_rule(
            name="子类规则",
            description="适用于劳动合同子类",
            risk_level=RiskLevel.high,
            is_universal=False,
            type_ids=[],
            subtype_ids=["subtype_labor_contract"],
        )

        review_rules = await rules_repository.get_rules_for_review("subtype_labor_contract")
        review_rule_ids = {r.id for r in review_rules}
        assert universal_rule.id in review_rule_ids
        assert type_rule.id in review_rule_ids
        assert subtype_rule.id in review_rule_ids

        by_subtype_rules = await rules_repository.get_rules_by_subtype(
            "subtype_labor_contract",
            include_universal=True,
        )
        by_subtype_ids = {r.id for r in by_subtype_rules}
        assert universal_rule.id in by_subtype_ids
        assert subtype_rule.id in by_subtype_ids
        assert type_rule.id not in by_subtype_ids

        try:
            await rules_service.create_rule(
                name="非法规则",
                description="通用且指定子类",
                risk_level=RiskLevel.low,
                is_universal=True,
                type_ids=[],
                subtype_ids=["subtype_labor_contract"],
            )
            raise AssertionError("Expected RuleValidationError")
        except RuleValidationError:
            pass


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
