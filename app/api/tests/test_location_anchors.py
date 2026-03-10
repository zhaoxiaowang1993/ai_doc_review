import sys
import unittest
from pathlib import Path
from unittest.mock import patch

API_DIR = Path(__file__).resolve().parents[1]
APP_DIR = API_DIR.parent
ROOT_DIR = APP_DIR.parent
for p in (API_DIR, ROOT_DIR, APP_DIR):
    p_str = str(p)
    if p_str in sys.path:
        sys.path.remove(p_str)
    sys.path.insert(0, p_str)

import fitz

from services import lc_pipeline as lp
from services.mineru_client import _table_html_to_plain_text


class TestLocationAnchors(unittest.IsolatedAsyncioTestCase):
    def test_table_html_to_plain_text(self):
        s = "<table><tr><td>甲方</td><td>乙方</td></tr><tr><td>张三</td><td>李四</td></tr></table>"
        out = _table_html_to_plain_text(s)
        self.assertIn("甲方", out)
        self.assertIn("乙方", out)
        self.assertIn("张三", out)
        self.assertIn("李四", out)
        self.assertNotIn("<table", out)

    async def test_cross_page_table_search_updates_page_num(self):
        para = {"page_num": 1, "content": "foo", "bbox": [0, 0, 10, 10], "block_type": "table"}
        page_sizes = {1: (100.0, 100.0), 2: (100.0, 100.0), 3: (100.0, 100.0)}

        def _fake_find_pdf_rects(_pdf_path, page_num, *, needle=None, fallback_sentence=None):
            if page_num == 3:
                return [fitz.Rect(10, 10, 20, 20)]
            return []

        with patch.object(lp, "_find_pdf_rects", side_effect=_fake_find_pdf_rects), patch.object(
            lp, "_find_layout_quadpoints", return_value=None
        ):
            page_num, bbox, anchors = await lp._locate_issue_location(
                pdf_path="dummy.pdf",
                para=para,
                para_index=0,
                cache_key="dummy",
                page_sizes=page_sizes,
                page_bbox_space={},
                layout=None,
                needle="foo",
            )

        self.assertEqual(page_num, 3)
        self.assertIsNotNone(anchors)
        self.assertGreaterEqual(len(anchors or []), 1)
        self.assertEqual(anchors[0].page_num, 3)
        self.assertEqual(bbox, anchors[0].bounding_box)
        self.assertEqual(bbox, [10.0, 90.0, 20.0, 90.0, 10.0, 80.0, 20.0, 80.0])

    async def test_multiple_pdf_rects_produces_combined_anchor_first(self):
        para = {"page_num": 2, "content": "foo", "bbox": [0, 0, 10, 10], "block_type": "text"}
        page_sizes = {1: (100.0, 100.0), 2: (100.0, 100.0), 3: (100.0, 100.0)}

        rects = [fitz.Rect(10, 10, 20, 20), fitz.Rect(30, 40, 50, 60)]

        with patch.object(lp, "_find_pdf_rects", return_value=rects), patch.object(
            lp, "_find_layout_quadpoints", return_value=None
        ):
            page_num, bbox, anchors = await lp._locate_issue_location(
                pdf_path="dummy.pdf",
                para=para,
                para_index=0,
                cache_key="dummy",
                page_sizes=page_sizes,
                page_bbox_space={},
                layout=None,
                needle="foo",
            )

        self.assertEqual(page_num, 2)
        self.assertIsNotNone(anchors)
        self.assertGreaterEqual(len(anchors or []), 3)
        self.assertEqual(len(anchors[0].bounding_box), 16)
        self.assertEqual(bbox, anchors[0].bounding_box)

    async def test_fallback_to_para_bbox_when_no_match(self):
        para = {"page_num": 2, "content": "foo", "bbox": [1, 2, 3, 4], "block_type": "table"}
        page_sizes = {1: (100.0, 100.0), 2: (100.0, 100.0), 3: (100.0, 100.0)}

        with patch.object(lp, "_find_pdf_rects", return_value=[]), patch.object(
            lp, "_find_layout_quadpoints", return_value=None
        ), patch.object(lp, "bbox_to_quadpoints", return_value=[1, 1, 2, 2, 3, 3, 4, 4]):
            page_num, bbox, anchors = await lp._locate_issue_location(
                pdf_path="dummy.pdf",
                para=para,
                para_index=0,
                cache_key="dummy",
                page_sizes=page_sizes,
                page_bbox_space={2: {"observed_max": (100, 100), "is_canvas": False}},
                layout=None,
                needle="foo",
            )

        self.assertEqual(page_num, 2)
        self.assertEqual(bbox, [1, 1, 2, 2, 3, 3, 4, 4])
        self.assertIsNone(anchors)
