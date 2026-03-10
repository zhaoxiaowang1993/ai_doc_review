import argparse
import asyncio
import base64
import json
import os
import re
import time
import zipfile
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable

import httpx


def _normalize_compact(s: str) -> str:
    s = (s or "").replace("\u3000", " ").replace("\r", "").replace("\n", "").replace("\t", "").strip()
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", s)


def _iter_text_boxes(obj: Any) -> Iterable[tuple[str, list[float]]]:
    if isinstance(obj, dict):
        text = obj.get("text") or obj.get("content")
        bbox = obj.get("bbox") or obj.get("box") or obj.get("bounding_box")
        if isinstance(text, str) and isinstance(bbox, list) and len(bbox) in (4, 8):
            try:
                bb = [float(x) for x in bbox]
                yield text, bb
            except Exception:
                pass
        for v in obj.values():
            yield from _iter_text_boxes(v)
    elif isinstance(obj, list):
        for it in obj:
            yield from _iter_text_boxes(it)


def _pick_first_image_path(layout: Any) -> str | None:
    if isinstance(layout, dict):
        for k in ("image_path", "img_path", "imagePath"):
            v = layout.get(k)
            if isinstance(v, str) and v.strip().lower().endswith((".jpg", ".jpeg", ".png")):
                return v
        for v in layout.values():
            p = _pick_first_image_path(v)
            if p:
                return p
    elif isinstance(layout, list):
        for it in layout:
            p = _pick_first_image_path(it)
            if p:
                return p
    return None


def _read_artifacts(cache_key: str) -> tuple[Path, Any, str]:
    base = Path(__file__).resolve().parents[1] / "app" / "data" / "mineru"
    meta_path = base / f"{cache_key}.meta.json"
    if not meta_path.exists():
        raise SystemExit(f"meta not found: {meta_path}")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    zip_path = Path(meta.get("zip_path") or "")
    layout_path = Path(meta.get("layout_path") or "")
    if not zip_path.is_absolute():
        zip_path = (Path(__file__).resolve().parents[1] / zip_path).resolve()
    if not layout_path.is_absolute():
        layout_path = (Path(__file__).resolve().parents[1] / layout_path).resolve()
    if not zip_path.exists():
        raise SystemExit(f"zip not found: {zip_path}")
    if not layout_path.exists():
        raise SystemExit(f"layout not found: {layout_path}")
    layout = json.loads(layout_path.read_text(encoding="utf-8"))
    image_path = _pick_first_image_path(layout)
    if not image_path:
        raise SystemExit("no image_path/img_path found in layout")
    return zip_path, layout, image_path


async def _call_paddleocr_sync(api_url: str, token: str, image_bytes: bytes) -> dict[str, Any]:
    headers = {"Authorization": f"token {token}", "Content-Type": "application/json"}
    payload = {"file": base64.b64encode(image_bytes).decode("ascii"), "fileType": 1}
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(api_url, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()


async def _call_paddleocr_job(
    job_url: str,
    token: str,
    *,
    model: str,
    image_bytes: bytes,
    poll_interval_sec: float = 2.0,
    max_wait_sec: float = 180.0,
) -> dict[str, Any]:
    headers = {"Authorization": f"bearer {token}"}
    data = {"model": model, "optionalPayload": json.dumps({})}
    files = {"file": ("table.jpg", image_bytes, "image/jpeg")}

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(job_url, headers=headers, data=data, files=files)
        resp.raise_for_status()
        payload = resp.json()
        job_id = ((payload.get("data") or {}).get("jobId")) if isinstance(payload, dict) else None
        if not job_id:
            raise RuntimeError(f"job create response missing jobId: {payload}")

        deadline = time.time() + max_wait_sec
        json_url = None
        while True:
            if time.time() > deadline:
                raise TimeoutError("timed out waiting for job result")
            r2 = await client.get(f"{job_url}/{job_id}", headers=headers)
            r2.raise_for_status()
            p2 = r2.json()
            data2 = p2.get("data") if isinstance(p2, dict) else None
            state = (data2 or {}).get("state") if isinstance(data2, dict) else None
            if state == "done":
                result_url = (data2 or {}).get("resultUrl") if isinstance(data2, dict) else None
                if isinstance(result_url, dict):
                    json_url = result_url.get("jsonUrl") or result_url.get("jsonlUrl")
                if not json_url:
                    raise RuntimeError(f"job done but missing resultUrl.jsonUrl: {p2}")
                break
            if state == "failed":
                raise RuntimeError(f"job failed: {(data2 or {}).get('errorMsg')}")
            await asyncio.sleep(poll_interval_sec)  # type: ignore[name-defined]

        r3 = await client.get(json_url)
        r3.raise_for_status()
        lines = [ln for ln in (r3.text or "").splitlines() if ln.strip()]
        if not lines:
            raise RuntimeError("empty jsonl result")
        return json.loads(lines[0])


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-key", required=True)
    parser.add_argument("--query", default="自助上传")
    parser.add_argument("--image-path", default="")
    parser.add_argument("--mode", choices=["sync", "job"], default=os.environ.get("PADDLEOCR_MODE", "job") or "job")
    parser.add_argument("--api-url", default=os.environ.get("PADDLEOCR_API_URL", ""))
    parser.add_argument("--job-url", default=os.environ.get("PADDLEOCR_JOB_URL", ""))
    parser.add_argument("--token", default=os.environ.get("PADDLEOCR_TOKEN", ""))
    parser.add_argument("--model", default=os.environ.get("PADDLEOCR_MODEL", "PaddleOCR-VL-1.5"))
    args = parser.parse_args()

    if not args.token:
        raise SystemExit("missing PADDLEOCR_TOKEN (or pass --token)")
    if args.mode == "sync" and not args.api_url:
        raise SystemExit("missing PADDLEOCR_API_URL (or pass --api-url)")
    if args.mode == "job" and not args.job_url:
        raise SystemExit("missing PADDLEOCR_JOB_URL (or pass --job-url)")

    zip_path, _layout, image_path = _read_artifacts(args.cache_key)
    if args.image_path:
        image_path = args.image_path
    with zipfile.ZipFile(zip_path) as zf:
        data = zf.read(image_path)

    if args.mode == "sync":
        raw = await _call_paddleocr_sync(args.api_url, args.token, data)
    else:
        raw = await _call_paddleocr_job(args.job_url, args.token, model=args.model, image_bytes=data)

    result = raw.get("result") if isinstance(raw, dict) else None
    if not isinstance(result, dict):
        result = raw if isinstance(raw, dict) else {}
    pages = result.get("layoutParsingResults") if isinstance(result, dict) else None
    if not isinstance(pages, list):
        pages = []
    if not pages:
        print(json.dumps({"keys": list(raw.keys()), "raw": raw}, ensure_ascii=False)[:4000])
        return
    page0 = pages[0]
    pruned = page0.get("prunedResult") or {}

    query_norm = _normalize_compact(args.query)
    scored: list[tuple[float, str, list[float]]] = []
    for text, bbox in _iter_text_boxes(pruned):
        tnorm = _normalize_compact(text)
        if not tnorm:
            continue
        ratio = SequenceMatcher(a=query_norm, b=tnorm).ratio() if query_norm else 0.0
        if query_norm and query_norm in tnorm:
            ratio = max(ratio, 1.0)
        scored.append((ratio, text, bbox))
    scored.sort(key=lambda x: x[0], reverse=True)

    top = [
        {"score": round(s, 3), "text": t[:80], "bbox": bb}
        for s, t, bb in scored[:12]
    ]
    out = {
        "cache_key": args.cache_key,
        "image_path": image_path,
        "mode": args.mode,
        "api_url": args.api_url,
        "job_url": args.job_url,
        "model": args.model,
        "result_keys": list(page0.keys()),
        "pruned_keys": list(pruned.keys()) if isinstance(pruned, dict) else [],
        "query": args.query,
        "top_matches": top,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
