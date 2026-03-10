import json
import asyncio
import time
from typing import Any

import httpx


class PaddleOCRJobsClient:
    def __init__(
        self,
        *,
        job_url: str,
        token: str,
        model: str,
        poll_interval_sec: float = 2.0,
        max_wait_sec: float = 180.0,
    ) -> None:
        self.job_url = (job_url or "").strip()
        self.token = (token or "").strip()
        self.model = (model or "").strip() or "PaddleOCR-VL-1.5"
        self.poll_interval_sec = float(poll_interval_sec)
        self.max_wait_sec = float(max_wait_sec)

    async def parse_image(self, image_bytes: bytes) -> dict[str, Any]:
        if not self.job_url or not self.token:
            raise RuntimeError("PaddleOCR job_url/token is not configured")

        headers = {"Authorization": f"bearer {self.token}"}
        data = {"model": self.model, "optionalPayload": json.dumps({})}
        files = {"file": ("image.jpg", image_bytes, "image/jpeg")}

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(self.job_url, headers=headers, data=data, files=files)
            resp.raise_for_status()
            payload = resp.json()
            data_obj = payload.get("data") if isinstance(payload, dict) else None
            job_id = data_obj.get("jobId") if isinstance(data_obj, dict) else None
            if not job_id:
                raise RuntimeError(f"PaddleOCR job create response missing jobId: {payload}")

            deadline = time.time() + self.max_wait_sec
            json_url = None
            while True:
                if time.time() > deadline:
                    raise TimeoutError("PaddleOCR job timed out")
                r2 = await client.get(f"{self.job_url}/{job_id}", headers=headers)
                r2.raise_for_status()
                p2 = r2.json()
                d2 = p2.get("data") if isinstance(p2, dict) else None
                state = d2.get("state") if isinstance(d2, dict) else None
                if state == "done":
                    ru = d2.get("resultUrl") if isinstance(d2, dict) else None
                    if isinstance(ru, dict):
                        json_url = ru.get("jsonUrl") or ru.get("jsonlUrl")
                    if not json_url:
                        raise RuntimeError(f"PaddleOCR job done but missing resultUrl: {p2}")
                    break
                if state == "failed":
                    msg = d2.get("errorMsg") if isinstance(d2, dict) else None
                    raise RuntimeError(f"PaddleOCR job failed: {msg}")
                await asyncio.sleep(self.poll_interval_sec)

            r3 = await client.get(json_url)
            r3.raise_for_status()
            lines = [ln for ln in (r3.text or "").splitlines() if ln.strip()]
            if not lines:
                raise RuntimeError("PaddleOCR job returned empty JSONL")
            first = json.loads(lines[0])
            if isinstance(first, dict) and "result" in first:
                return first
            return {"result": first}
