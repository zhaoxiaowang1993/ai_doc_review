import tempfile
import sys
import unittest
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
APP_DIR = API_DIR.parent
ROOT_DIR = APP_DIR.parent
for p in (ROOT_DIR, APP_DIR):
    p_str = str(p)
    if p_str in sys.path:
        sys.path.remove(p_str)
    sys.path.insert(0, p_str)

from fastapi import FastAPI
from fastapi.testclient import TestClient

from config.config import settings
from database.db_client import SQLiteClient
from database.rules_repository import RulesRepository
from database.documents_repository import DocumentsRepository
from database.review_rule_snapshots_repository import ReviewRuleSnapshotsRepository
from dependencies import (
    get_documents_service,
    get_issues_service,
    get_review_rule_snapshots_repository,
    get_rules_service,
)
from routers import issues as issues_router
from services.documents_service import DocumentsService
from services.rules_service import RulesService


class _FakeIssuesRepository:
    async def delete_issues_by_doc(self, doc_id: str) -> int:
        return 0


class _FakeIssuesService:
    def __init__(self) -> None:
        self.issues_repository = _FakeIssuesRepository()

    async def get_issues_data(self, doc_id: str):
        return []

    async def initiate_review(self, pdf_path: str, user, time_stamp, custom_rules=None):
        if False:
            yield []
        return


class TestReviewRulesState(unittest.TestCase):
    def test_rules_state_snapshot_and_change_detection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            db_path = tmp_path / "app.db"
            docs_dir = tmp_path / "documents"
            docs_dir.mkdir(parents=True, exist_ok=True)

            original_docs_dir = settings.local_docs_dir
            settings.local_docs_dir = str(docs_dir)
            try:
                db_client = SQLiteClient(db_path=str(db_path))
                rules_repo = RulesRepository(db_client)
                documents_repo = DocumentsRepository(db_client)
                snapshots_repo = ReviewRuleSnapshotsRepository(db_client)

                self._run_async(rules_repo.init())
                self._run_async(documents_repo.init())
                self._run_async(snapshots_repo.init())

                rules_service = RulesService(rules_repo)
                documents_service = DocumentsService(documents_repo)

                doc_id = "test.pdf"
                (docs_dir / doc_id).write_bytes(b"%PDF-1.4\n%fake\n")
                self._run_async(
                    documents_service.create_document(
                        filename=doc_id,
                        subtype_id="subtype_labor_contract",
                        doc_id=doc_id,
                    )
                )

                rule = self._run_async(
                    rules_service.create_rule(
                        name="测试规则A",
                        description="旧描述",
                        risk_level="高",
                        subtype_ids=["subtype_labor_contract"],
                    )
                )

                app = FastAPI()
                app.include_router(issues_router.router)
                app.dependency_overrides[get_rules_service] = lambda: rules_service
                app.dependency_overrides[get_documents_service] = lambda: documents_service
                app.dependency_overrides[get_review_rule_snapshots_repository] = lambda: snapshots_repo
                app.dependency_overrides[get_issues_service] = lambda: _FakeIssuesService()

                client = TestClient(app)

                resp = client.get(f"/api/v1/review/{doc_id}/issues")
                self.assertEqual(resp.status_code, 200)

                state = client.get(f"/api/v1/review/{doc_id}/rules-state").json()
                self.assertFalse(state["rules_changed_since_review"])
                self.assertEqual([r["id"] for r in state["snapshot_rules"]], [rule.id])
                self.assertEqual(state["snapshot_rules"][0]["description"], "旧描述")

                self._run_async(rules_service.update_rule(rule.id, {"description": "新描述"}))

                state2 = client.get(f"/api/v1/review/{doc_id}/rules-state").json()
                self.assertTrue(state2["rules_changed_since_review"])
                self.assertEqual(state2["snapshot_rules"][0]["description"], "旧描述")

                resp2 = client.get(f"/api/v1/review/{doc_id}/issues?force=true")
                self.assertEqual(resp2.status_code, 200)

                state3 = client.get(f"/api/v1/review/{doc_id}/rules-state").json()
                self.assertFalse(state3["rules_changed_since_review"])
                self.assertEqual(state3["snapshot_rules"][0]["description"], "新描述")
            finally:
                settings.local_docs_dir = original_docs_dir

    def _run_async(self, coro):
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
