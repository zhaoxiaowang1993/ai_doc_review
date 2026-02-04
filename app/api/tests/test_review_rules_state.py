import tempfile
import sys
import unittest
import hashlib
from pathlib import Path
from uuid import uuid4

API_DIR = Path(__file__).resolve().parents[1]
APP_DIR = API_DIR.parent
ROOT_DIR = APP_DIR.parent
for p in (API_DIR, ROOT_DIR, APP_DIR):
    p_str = str(p)
    if p_str in sys.path:
        sys.path.remove(p_str)
    sys.path.insert(0, p_str)

from fastapi import FastAPI
from fastapi.testclient import TestClient

from config.config import settings
from database.db_client import SQLiteClient
from database.analysis_issues_repository import AnalysisIssuesRepository
from database.analysis_runs_repository import AnalysisRunsRepository
from database.issues_repository import IssuesRepository
from database.rules_repository import RulesRepository
from database.documents_repository import DocumentsRepository
from dependencies import (
    get_documents_service,
    get_issues_service,
    get_rules_service,
    get_storage_provider,
)
from routers import issues as issues_router
from services.documents_service import DocumentsService
from services.issues_service import IssuesService
from services.rules_service import RulesService
from services.storage_provider import LocalStorageProvider


class _FakePipeline:
    async def stream_issues(self, *, doc_id: str, pdf_path: str, user_id: str, timestamp_iso: str, cache_key: str, custom_rules=None):
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
                issues_repo = IssuesRepository(db_client)
                analysis_runs_repo = AnalysisRunsRepository(db_client)
                analysis_issues_repo = AnalysisIssuesRepository(db_client)

                self._run_async(rules_repo.init())
                self._run_async(documents_repo.init())
                self._run_async(issues_repo.init())
                self._run_async(analysis_runs_repo.init())
                self._run_async(analysis_issues_repo.init())

                rules_service = RulesService(rules_repo)
                documents_service = DocumentsService(documents_repo)
                storage = LocalStorageProvider(base_dir=str(docs_dir))

                doc_id = str(uuid4())
                pdf_bytes = b"%PDF-1.4\n%fake\n"
                sha256 = hashlib.sha256(pdf_bytes).hexdigest()
                (docs_dir / "objects").mkdir(parents=True, exist_ok=True)
                (docs_dir / "objects" / f"{doc_id}.pdf").write_bytes(pdf_bytes)
                self._run_async(
                    documents_service.create_document(
                        owner_id="local-user",
                        original_filename="test.pdf",
                        display_name="test.pdf",
                        subtype_id="subtype_labor_contract",
                        storage_provider="local",
                        storage_key=f"objects/{doc_id}.pdf",
                        mime_type="application/pdf",
                        size_bytes=len(pdf_bytes),
                        sha256=sha256,
                        created_by="local-user",
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
                app.dependency_overrides[get_storage_provider] = lambda: storage
                app.dependency_overrides[get_issues_service] = lambda: IssuesService(
                    issues_repo,
                    analysis_runs_repo,
                    analysis_issues_repo,
                    documents_repo,
                    _FakePipeline(),
                )

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
