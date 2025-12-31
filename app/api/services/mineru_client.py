import httpx
import io
import json
import asyncio
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List

from common.logger import get_logger
from config.config import settings

logging = get_logger(__name__)


class MinerUClient:
    """
    MinerU v4 client (per https://mineru.net/apiManage/docs).

    Notes:
    - `创建解析任务` API does NOT support direct local file upload.
    - For local files, use `文件批量上传解析`:
        1) POST /api/v4/file-urls/batch to get pre-signed upload URL(s)
        2) PUT file bytes to the upload URL
        3) Poll /api/v4/extract-results/batch/{batch_id} for state=done
        4) Download `full_zip_url` and parse a JSON artifact inside
    """

    def __init__(self) -> None:
        self.base_url = settings.mineru_base_url.rstrip("/")
        self.api_key = settings.mineru_api_key
        self.model_version = settings.mineru_model_version
        self.poll_interval_sec = float(settings.mineru_poll_interval_sec)
        self.max_wait_sec = float(settings.mineru_max_wait_sec)

    async def extract(self, file_path: Path) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("MINERU_API_KEY is required.")

        if not file_path.exists():
            raise FileNotFoundError(str(file_path))

        logging.info(f"Calling MinerU (v4) for file: {file_path}")

        batch_id, upload_url = await self._request_upload_url(file_path.name)
        await self._upload_file(upload_url, file_path)
        full_zip_url = await self._poll_batch_until_done(batch_id, file_path.name)
        cache_key = _safe_stem(file_path.stem)
        payload, meta = await self._download_and_parse_zip(full_zip_url, cache_key)
        if settings.debug:
            try:
                out_dir = Path(settings.mineru_cache_dir)
                out_dir.mkdir(parents=True, exist_ok=True)
                out_path = out_dir / f"{cache_key}.json"
                out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                meta_path = out_dir / f"{cache_key}.meta.json"
                meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
                logging.info(f"Saved MinerU parsed JSON to {out_path}")
            except Exception as e:
                logging.warning(f"Failed to save MinerU debug JSON: {e}")
        # Return both content and meta so downstream can do precise bbox mapping.
        return {"content": payload, "meta": meta}

    async def _request_upload_url(self, file_name: str) -> tuple[str, str]:
        url = f"{self.base_url}/api/v4/file-urls/batch"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "*/*",
        }
        body = {
            "files": [{"name": file_name, "data_id": file_name}],
            "model_version": self.model_version,
        }

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, headers=headers, json=body)
            resp.raise_for_status()
            payload = resp.json()

        if payload.get("code") != 0:
            raise RuntimeError(f"MinerU upload-url request failed: {payload.get('msg')} ({payload})")

        data = payload.get("data") or {}
        batch_id = data.get("batch_id")
        file_urls = data.get("file_urls") or data.get("files") or []
        if not batch_id or not file_urls:
            raise RuntimeError(f"MinerU response missing batch_id/file_urls: {payload}")

        return batch_id, file_urls[0]

    async def _upload_file(self, upload_url: str, file_path: Path) -> None:
        async with httpx.AsyncClient(timeout=300) as client:
            with file_path.open("rb") as f:
                resp = await client.put(upload_url, content=f.read())
                resp.raise_for_status()

    async def _poll_batch_until_done(self, batch_id: str, file_name: str) -> str:
        url = f"{self.base_url}/api/v4/extract-results/batch/{batch_id}"
        headers = {"Authorization": f"Bearer {self.api_key}", "Accept": "*/*"}
        deadline = time.time() + self.max_wait_sec

        async with httpx.AsyncClient(timeout=60) as client:
            while True:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                payload = resp.json()

                if payload.get("code") != 0:
                    raise RuntimeError(f"MinerU poll failed: {payload.get('msg')} ({payload})")

                data = payload.get("data") or {}
                results = data.get("extract_result") or data.get("extract_results") or []
                matched = next((r for r in results if r.get("file_name") == file_name), None)

                if matched:
                    state = matched.get("state")
                    if state == "done":
                        full_zip_url = matched.get("full_zip_url")
                        if not full_zip_url:
                            raise RuntimeError(f"MinerU done but missing full_zip_url: {matched}")
                        return full_zip_url
                    if state == "failed":
                        raise RuntimeError(f"MinerU extract failed: {matched.get('err_msg')}")

                if time.time() > deadline:
                    raise TimeoutError(f"Timed out waiting for MinerU result for {file_name} (batch_id={batch_id})")

                await asyncio.sleep(self.poll_interval_sec)

    async def _download_and_parse_zip(self, full_zip_url: str, cache_key: str) -> tuple[Dict[str, Any] | List[Any], Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.get(full_zip_url)
            resp.raise_for_status()
            zip_bytes = resp.content

        meta: Dict[str, Any] = {"zip_url": full_zip_url}
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            json_names = [n for n in zf.namelist() if n.lower().endswith(".json")]
            if not json_names:
                raise RuntimeError("MinerU zip did not contain any JSON files.")

            meta["zip_files"] = zf.namelist()

            if settings.mineru_cache_artifacts:
                try:
                    out_dir = Path(settings.mineru_cache_dir)
                    out_dir.mkdir(parents=True, exist_ok=True)
                    zip_path = out_dir / f"{cache_key}.zip"
                    zip_path.write_bytes(zip_bytes)
                    meta["zip_path"] = str(zip_path)
                except Exception as e:
                    logging.warning(f"Failed to save MinerU zip: {e}")

            # Extract page image sizes (if images are present) for accurate pixel->point mapping.
            page_canvas_sizes = _extract_page_canvas_sizes(zf)
            if page_canvas_sizes:
                meta["page_canvas_sizes"] = page_canvas_sizes

            # Also try to derive canvas sizes from layout.json (works when zip has no rendered images).
            layout_name = next((n for n in zf.namelist() if n.lower().endswith("layout.json")), None)
            if layout_name:
                try:
                    raw = zf.read(layout_name)
                    layout = json.loads(raw.decode("utf-8"))
                    sizes = _extract_page_canvas_sizes_from_layout(layout)
                    if sizes:
                        meta["page_canvas_sizes"] = {**meta.get("page_canvas_sizes", {}), **sizes}
                    if settings.mineru_cache_artifacts:
                        out_dir = Path(settings.mineru_cache_dir)
                        out_dir.mkdir(parents=True, exist_ok=True)
                        layout_path = out_dir / f"{cache_key}.layout.json"
                        layout_path.write_bytes(raw)
                        meta["layout_path"] = str(layout_path)
                        meta["layout_file"] = layout_name
                except Exception as e:
                    logging.warning(f"Failed to parse/cache MinerU layout.json: {e}")

            # Prefer likely structured outputs
            preferred = []
            for n in json_names:
                ln = n.lower()
                if any(k in ln for k in ("layout", "extract", "result", "content")):
                    preferred.append(n)
            candidates = preferred or sorted(json_names)

            best_name = None
            best_score = -1
            best_data: Any = None

            for name in candidates:
                try:
                    with zf.open(name) as f:
                        raw = f.read()
                    data = json.loads(raw.decode("utf-8"))
                    score = _score_extraction_json(data)
                    if score > best_score:
                        best_score = score
                        best_name = name
                        best_data = data
                except Exception:
                    continue

            if best_name is None:
                # Fallback to first JSON
                with zf.open(candidates[0]) as f:
                    best_name = candidates[0]
                    best_data = json.loads(f.read().decode("utf-8"))

            meta["selected_json"] = best_name
            meta["selected_score"] = best_score
            meta["cache_key"] = cache_key
            return best_data, meta

    @staticmethod
    def to_paragraphs(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Normalize MinerU parsed JSON to a list of paragraphs with page and bbox.
        This function is intentionally tolerant to multiple schema variants.
        """
        paragraphs: List[Dict[str, Any]] = []

        # Our extract() returns {"content": ..., "meta": ...}
        meta = None
        if isinstance(payload, dict) and "content" in payload:
            meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else None
            payload = payload.get("content")

        # MinerU artifacts can be a dict OR a list.
        if isinstance(payload, list):
            return _paragraphs_from_blocks_list(payload, meta=meta)
        if not isinstance(payload, dict):
            return paragraphs

        pages = payload.get("pages") or (payload.get("data") or {}).get("pages") or []
        if isinstance(pages, dict):
            pages = pages.get("pages") or pages.get("items") or []

        for page in pages:
            if not isinstance(page, dict):
                continue
            page_num = page.get("page") or page.get("page_num") or page.get("page_number") or 1
            page_height = page.get("height") or page.get("page_height") or page.get("h")
            blocks = page.get("paragraphs") or page.get("blocks") or page.get("content") or []
            if isinstance(blocks, dict):
                blocks = blocks.get("paragraphs") or blocks.get("blocks") or []
            for block in blocks:
                if not isinstance(block, dict):
                    continue
                text = (block.get("text") or block.get("content") or "").strip()
                if not text:
                    continue
                bbox = block.get("bbox") or block.get("bounding_box") or block.get("box")
                canvas = None
                if meta and "page_canvas_sizes" in meta:
                    canvas = meta["page_canvas_sizes"].get(str(page_num)) or meta["page_canvas_sizes"].get(int(page_num))  # type: ignore[arg-type]
                paragraphs.append(
                    {
                        "content": text,
                        "page_num": page_num,
                        "bbox": bbox,
                        "page_height": page_height,
                        "canvas_size": canvas,
                    }
                )

        if not paragraphs and "paragraphs" in payload:
            for para in payload.get("paragraphs", []):
                text = (para.get("text") or para.get("content") or "").strip()
                if not text:
                    continue
                paragraphs.append(
                    {
                        "content": text,
                        "page_num": para.get("page_num", 1),
                        "bbox": para.get("bbox") or para.get("bounding_box"),
                        "page_height": para.get("page_height"),
                        "canvas_size": None,
                    }
                )

        return paragraphs


def _fix_mojibake(text: str) -> str:
    """
    MinerU zip JSON sometimes contains mojibake (UTF-8 bytes decoded as latin-1).
    Try to repair; if it fails, return original.
    """
    if not text:
        return text
    try:
        repaired = text.encode("latin1").decode("utf-8")
        # Heuristic: if repair introduces CJK or removes obvious mojibake markers, prefer it.
        if any("\u4e00" <= ch <= "\u9fff" for ch in repaired) or "å" in text:
            return repaired
    except Exception:
        pass
    return text


def _paragraphs_from_blocks_list(items: List[Any], *, meta: Dict[str, Any] | None) -> List[Dict[str, Any]]:
    paragraphs: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        text = item.get("text") or item.get("content") or ""
        text = _fix_mojibake(str(text)).strip()
        if not text:
            continue
        bbox = item.get("bbox") or item.get("bounding_box") or item.get("box")
        page_idx = item.get("page_idx")
        page_num = (int(page_idx) + 1) if page_idx is not None else item.get("page_num", 1)
        canvas = None
        if meta and "page_canvas_sizes" in meta:
            canvas = meta["page_canvas_sizes"].get(str(page_num))  # type: ignore[union-attr]
        paragraphs.append(
            {
                "content": text,
                "page_num": page_num,
                "bbox": bbox,
                "page_height": None,
                "canvas_size": canvas,
            }
        )
    return paragraphs


def _score_extraction_json(data: Any) -> int:
    """
    Heuristic scoring to pick the best JSON artifact from MinerU zip.
    Higher score means it's more likely to contain per-block text+bbox info.
    """
    try:
        if isinstance(data, list):
            score = 0
            for it in data[:200]:
                if isinstance(it, dict) and ("bbox" in it or "bounding_box" in it) and ("text" in it or "content" in it):
                    score += 1
            return score
        if isinstance(data, dict):
            pages = data.get("pages") or (data.get("data") or {}).get("pages")
            if isinstance(pages, list):
                score = 10
                for p in pages[:10]:
                    if isinstance(p, dict):
                        blocks = p.get("paragraphs") or p.get("blocks") or []
                        if isinstance(blocks, list):
                            score += min(len(blocks), 200)
                return score
    except Exception:
        pass
    return 0


def _extract_page_canvas_sizes(zf: zipfile.ZipFile) -> Dict[str, List[int]]:
    """
    Try to infer per-page rendered image sizes from images in the zip.
    Returns {page_num_str: [width, height]} if possible.
    """
    sizes: Dict[str, List[int]] = {}
    for name in zf.namelist():
        lower = name.lower()
        if not (lower.endswith(".png") or lower.endswith(".jpg") or lower.endswith(".jpeg")):
            continue
        try:
            with zf.open(name) as f:
                head = f.read(4096)
            w_h = None
            if lower.endswith(".png"):
                w_h = _png_size(head)
            else:
                w_h = _jpg_size(head)
            if not w_h:
                continue
            w, h = w_h
            # Heuristic: extract page index from filename like ".../page_1.png" or ".../0.png"
            page_num = _infer_page_num_from_filename(name)
            if page_num is not None:
                sizes[str(page_num)] = [int(w), int(h)]
        except Exception:
            continue
    return sizes


def _infer_page_num_from_filename(name: str) -> int | None:
    import re
    base = Path(name).stem
    # Try common patterns
    m = re.search(r"(?:page|p)[-_]?(\d+)$", base, re.IGNORECASE)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)$", base)
    if m:
        # Often 0-based page index in filenames
        n = int(m.group(1))
        return n + 1
    return None


def _safe_stem(stem: str) -> str:
    return "".join([c if c.isalnum() or c in ("-", "_") else "_" for c in stem])


def _extract_page_canvas_sizes_from_layout(layout: Any) -> Dict[str, List[int]]:
    """
    MinerU layout.json contains per-page `page_size` (pixel canvas) and `page_idx` (0-based).
    Return {page_num_str: [w, h]}.
    """
    try:
        if not isinstance(layout, dict):
            return {}
        pdf_info = layout.get("pdf_info")
        if not isinstance(pdf_info, list):
            return {}
        sizes: Dict[str, List[int]] = {}
        for page in pdf_info:
            if not isinstance(page, dict):
                continue
            page_idx = page.get("page_idx")
            page_size = page.get("page_size")
            if page_idx is None or not isinstance(page_size, (list, tuple)) or len(page_size) != 2:
                continue
            w, h = int(page_size[0]), int(page_size[1])
            if w <= 0 or h <= 0:
                continue
            page_num = int(page_idx) + 1
            sizes[str(page_num)] = [w, h]
        return sizes
    except Exception:
        return {}


def _png_size(buf: bytes) -> tuple[int, int] | None:
    # PNG signature + IHDR chunk starts at offset 8
    if len(buf) < 24 or buf[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    # IHDR chunk: length(4) type(4) data(13) ...
    # Width/Height are first 8 bytes of IHDR data
    try:
        if buf[12:16] != b"IHDR":
            return None
        w = int.from_bytes(buf[16:20], "big")
        h = int.from_bytes(buf[20:24], "big")
        return w, h
    except Exception:
        return None


def _jpg_size(buf: bytes) -> tuple[int, int] | None:
    # Minimal JPEG SOF parser from header bytes
    if len(buf) < 4 or buf[:2] != b"\xff\xd8":
        return None
    i = 2
    try:
        while i + 9 < len(buf):
            if buf[i] != 0xFF:
                i += 1
                continue
            marker = buf[i + 1]
            i += 2
            # SOF0/SOF2
            if marker in (0xC0, 0xC2):
                length = int.from_bytes(buf[i : i + 2], "big")
                if i + length > len(buf):
                    return None
                # precision = buf[i+2]
                h = int.from_bytes(buf[i + 3 : i + 5], "big")
                w = int.from_bytes(buf[i + 5 : i + 7], "big")
                return w, h
            # Skip segment
            if i + 2 > len(buf):
                return None
            seg_len = int.from_bytes(buf[i : i + 2], "big")
            i += seg_len
    except Exception:
        return None
    return None
