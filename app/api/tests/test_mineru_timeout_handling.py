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
from database.db_client import SQLiteClient
from database.analysis_issues_repository import AnalysisIssuesRepository
from database.analysis_runs_repository import AnalysisRunsRepository
from database.documents_repository import DocumentsRepository
from database.issues_repository import IssuesRepository
from services.documents_service import DocumentsService
from services.issues_service import IssuesService


class _TimeoutPipeline:
    async def stream_issues(
        self,
        *,
        doc_id: str,
        pdf_path: str,
        user_id: str,
        timestamp_iso: str,
        cache_key: str,
        custom_rules=None,
    ):
        raise TimeoutError("Timed out waiting for MinerU result")
        if False:
            yield []


class TestMinerUTimeoutHandling(unittest.TestCase):
    def test_timeout_updates_run_status_and_raises_friendly_error(self):
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
                pipeline = _TimeoutPipeline()
                issues_service = IssuesService(
                    issues_repo,
                    analysis_runs_repo,
                    analysis_issues_repo,
                    documents_repo,
                    pipeline,
                )

                pdf_bytes = b"%PDF-1.4\n%fake\n"
                sha256 = hashlib.sha256(pdf_bytes).hexdigest()
                doc_id = str(uuid4())
                (docs_dir / "objects").mkdir(parents=True, exist_ok=True)
                (docs_dir / "objects" / f"{doc_id}.pdf").write_bytes(pdf_bytes)
                self._run_async(
                    documents_service.create_document(
                        owner_id="local-user",
                        original_filename="t.pdf",
                        display_name="t.pdf",
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

                with self.assertRaises(RuntimeError) as ctx:
                    self._run_async(
                        self._consume(
                            issues_service.initiate_review(
                                document_id=doc_id,
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
                self.assertIn("任务中断：文档解析超时 (MinerU Timeout)", str(ctx.exception))

                doc = self._run_async(documents_repo.get_by_id(doc_id, owner_id="local-user"))
                self.assertIsNotNone(doc)
                run_id = doc.last_run_id
                self.assertIsInstance(run_id, str)
                row = self._run_async(analysis_runs_repo.get_by_id(run_id, owner_id="local-user"))
                self.assertIsNotNone(row)
                self.assertEqual(row.get("status"), "failed")
                self.assertEqual(row.get("error_message"), "任务中断：文档解析超时 (MinerU Timeout)")
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

