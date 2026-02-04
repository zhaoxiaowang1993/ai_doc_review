import sys
import unittest
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

from dependencies import get_issues_service
from routers import issues as issues_router


class _FakeIssuesService:
    async def add_feedback(self, issue_id: str, user, dismissal_feedback=None):
        return {
            "id": issue_id,
            "doc_id": "doc",
            "owner_id": getattr(user, "oid", "local-user"),
            "source_run_id": "run",
            "source_issue_id": None,
            "text": "t",
            "type": "Grammar & Spelling",
            "status": "dismissed",
            "suggested_fix": "s",
            "explanation": "e",
            "risk_level": None,
            "location": None,
            "review_initiated_by": "local-user",
            "review_initiated_at_UTC": "2026-01-01T00:00:00Z",
            "resolved_by": "local-user",
            "resolved_at_UTC": "2026-01-01T00:00:00Z",
            "modified_fields": None,
            "dismissal_feedback": None,
            "feedback": None,
        }


class TestIssueFeedbackOptional(unittest.TestCase):
    def test_feedback_body_can_be_empty(self):
        app = FastAPI()
        app.include_router(issues_router.router)
        app.dependency_overrides[get_issues_service] = lambda: _FakeIssuesService()
        client = TestClient(app)

        issue_id = str(uuid4())
        resp = client.patch(f"/api/v1/review/doc/issues/{issue_id}/feedback")
        self.assertEqual(resp.status_code, 200)

        resp2 = client.patch(f"/api/v1/review/doc/issues/{issue_id}/feedback", json={})
        self.assertEqual(resp2.status_code, 200)

