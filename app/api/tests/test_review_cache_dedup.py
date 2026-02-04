import hashlib
import sys
import tempfile
import unittest
from datetime import datetime, timezone
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

from config.config import settings
from common.models import Issue, IssueStatusEnum
from database.db_client import SQLiteClient
from database.analysis_issues_repository import AnalysisIssuesRepository
from database.analysis_runs_repository import AnalysisRunsRepository
from database.documents_repository import DocumentsRepository
from database.issues_repository import IssuesRepository
from services.documents_service import DocumentsService
from services.issues_service import IssuesService


class _CountingPipeline:
    def __init__(self) -> None:
        self.calls = 0

    async def stream_issues(self, *, doc_id: str, pdf_path: str, user_id: str, timestamp_iso: str, cache_key: str, custom_rules=None):
        self.calls += 1
        yield [
            Issue(
                id=str(uuid4()),
                doc_id=doc_id,
                text="t",
                type="Grammar & Spelling",
                status=IssueStatusEnum.not_reviewed,
                suggested_fix="s",
                explanation="e",
                risk_level="低",
                location=None,
                review_initiated_by=user_id,
                review_initiated_at_UTC=timestamp_iso,
            )
        ]


class TestReviewCacheDedup(unittest.TestCase):
    def test_same_content_reuses_analysis_but_issues_are_independent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            db_path = tmp_path / "app.db"
            docs_dir = tmp_path / "documents"
            docs_dir.mkdir(parents=True, exist_ok=True)

            original_docs_dir = settings.local_docs_dir
            settings.local_docs_dir = str(docs_dir)
            try:
                db_client = SQLiteClient(db_path=str(db_path))
                documents_repo = DocumentsRepository(db_client)
                issues_repo = IssuesRepository(db_client)
                analysis_runs_repo = AnalysisRunsRepository(db_client)
                analysis_issues_repo = AnalysisIssuesRepository(db_client)
                self._run_async(documents_repo.init())
                self._run_async(issues_repo.init())
                self._run_async(analysis_runs_repo.init())
                self._run_async(analysis_issues_repo.init())

                documents_service = DocumentsService(documents_repo)
                pipeline = _CountingPipeline()
                issues_service = IssuesService(
                    issues_repo,
                    analysis_runs_repo,
                    analysis_issues_repo,
                    documents_repo,
                    pipeline,
                )

                pdf_bytes = b"%PDF-1.4\n%fake\n"
                sha256 = hashlib.sha256(pdf_bytes).hexdigest()
                doc1 = str(uuid4())
                doc2 = str(uuid4())

                for doc_id in (doc1, doc2):
                    (docs_dir / "objects").mkdir(parents=True, exist_ok=True)
                    (docs_dir / "objects" / f"{doc_id}.pdf").write_bytes(pdf_bytes)
                    self._run_async(
                        documents_service.create_document(
                            owner_id="local-user",
                            original_filename="same.pdf",
                            display_name="same.pdf",
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

                ts = datetime.now(timezone.utc)
                rules_snapshot_json = "[]"
                rules_fingerprint = "fp"
                pipeline_version = "pv"

                self._run_async(
                    self._consume(
                        issues_service.initiate_review(
                            document_id=doc1,
                            owner_id="local-user",
                            subtype_id="subtype_labor_contract",
                            pdf_path="unused",
                            user=type("U", (), {"oid": "local-user"})(),
                            time_stamp=ts,
                            rules_snapshot_json=rules_snapshot_json,
                            rules_fingerprint=rules_fingerprint,
                            pipeline_version=pipeline_version,
                            mineru_cache_key=sha256,
                            force=False,
                            custom_rules=[],
                        )
                    )
                )

                issues1 = self._run_async(issues_service.get_issues_data(doc1, owner_id="local-user"))
                self.assertEqual(len(issues1), 1)
                self.assertEqual(pipeline.calls, 1)

                self._run_async(
                    issues_repo.update_issue(
                        issues1[0].id,
                        owner_id="local-user",
                        fields={"status": IssueStatusEnum.accepted.value},
                    )
                )

                self._run_async(
                    self._consume(
                        issues_service.initiate_review(
                            document_id=doc2,
                            owner_id="local-user",
                            subtype_id="subtype_labor_contract",
                            pdf_path="unused",
                            user=type("U", (), {"oid": "local-user"})(),
                            time_stamp=ts,
                            rules_snapshot_json=rules_snapshot_json,
                            rules_fingerprint=rules_fingerprint,
                            pipeline_version=pipeline_version,
                            mineru_cache_key=sha256,
                            force=False,
                            custom_rules=[],
                        )
                    )
                )

                issues2 = self._run_async(issues_service.get_issues_data(doc2, owner_id="local-user"))
                self.assertEqual(len(issues2), 1)
                self.assertEqual(pipeline.calls, 1)
                self.assertNotEqual(issues1[0].id, issues2[0].id)
                self.assertEqual(issues2[0].status, IssueStatusEnum.not_reviewed)
            finally:
                settings.local_docs_dir = original_docs_dir

    async def _consume(self, agen):
        async for _ in agen:
            pass

    def _run_async(self, coro):
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
