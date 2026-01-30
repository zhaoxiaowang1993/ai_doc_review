import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI, Response
from fastapi.testclient import TestClient

from spa_staticfiles import SPAStaticFiles


class TestSPAFallback(unittest.TestCase):
    def test_spa_history_routes_fallback_to_index(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            static_dir = Path(tmpdir)
            (static_dir / "assets").mkdir(parents=True, exist_ok=True)
            (static_dir / "index.html").write_text(
                "<html><body>__SPA_INDEX__</body></html>", encoding="utf-8"
            )
            (static_dir / "assets" / "app.js").write_text(
                "console.log('ok');", encoding="utf-8"
            )

            app = FastAPI()

            @app.get("/api/health")
            def health_check():
                return Response(status_code=204)

            app.mount("/", SPAStaticFiles(directory=static_dir, html=True))

            client = TestClient(app)

            for path in ("/", "/terms", "/privacy", "/some-future-page"):
                resp = client.get(path)
                self.assertEqual(resp.status_code, 200, path)
                self.assertIn("__SPA_INDEX__", resp.text, path)

            resp = client.get("/api/health")
            self.assertEqual(resp.status_code, 204)

            resp = client.get("/assets/does-not-exist.js")
            self.assertEqual(resp.status_code, 404)

            resp = client.get("/api/does-not-exist")
            self.assertEqual(resp.status_code, 404)

