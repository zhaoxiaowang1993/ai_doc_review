import json
import hashlib
from pathlib import Path
from typing import Tuple

from common.models import DocumentIR, IRParagraph, IRTable, IRTableCell, IRTableRow, IRTextRun


def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _canonical_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def build_txt_ir(data: bytes) -> Tuple[DocumentIR, str]:
    text = data.decode("utf-8", errors="replace")
    lines = text.splitlines()
    paras: list[str] = []
    buf: list[str] = []
    for line in lines:
        if line.strip() == "":
            if buf:
                paras.append("\n".join(buf).strip("\n"))
                buf = []
            continue
        buf.append(line)
    if buf:
        paras.append("\n".join(buf).strip("\n"))

    blocks = []
    for i, p in enumerate(paras):
        pid = f"p:{i:05d}"
        rid = f"{pid}/r:00000"
        blocks.append(IRParagraph(id=pid, runs=[IRTextRun(id=rid, text=p)]))

    ir = DocumentIR(blocks=blocks)
    fingerprint = _sha256_text(_canonical_json(ir.model_dump()))
    return ir, fingerprint


def build_docx_ir(path: Path) -> Tuple[DocumentIR, str]:
    import zipfile
    import xml.etree.ElementTree as ET

    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    blocks = []
    p_index = 0
    t_index = 0

    with zipfile.ZipFile(path, "r") as z:
        xml_bytes = z.read("word/document.xml")

    root = ET.fromstring(xml_bytes)
    body = root.find("w:body", ns)
    if body is None:
        ir = DocumentIR(blocks=[])
        fingerprint = _sha256_text(_canonical_json(ir.model_dump()))
        return ir, fingerprint

    def extract_text(el: ET.Element) -> str:
        texts = [t.text or "" for t in el.findall(".//w:t", ns)]
        return "".join(texts)

    for child in list(body):
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            text = extract_text(child)
            if text.strip() == "":
                continue
            pid = f"p:{p_index:05d}"
            rid = f"{pid}/r:00000"
            blocks.append(IRParagraph(id=pid, runs=[IRTextRun(id=rid, text=text)]))
            p_index += 1
        elif tag == "tbl":
            tid = f"t:{t_index:05d}"
            rows = []
            for r_i, tr in enumerate(child.findall(".//w:tr", ns)):
                row_id = f"{tid}/r:{r_i:05d}"
                cells = []
                for c_i, tc in enumerate(tr.findall("./w:tc", ns)):
                    cell_id = f"{row_id}/c:{c_i:05d}"
                    cell_text = extract_text(tc).strip("\n")
                    pid = f"{cell_id}/p:00000"
                    rid = f"{pid}/r:00000"
                    para = IRParagraph(id=pid, runs=[IRTextRun(id=rid, text=cell_text)])
                    cells.append(IRTableCell(id=cell_id, blocks=[para]))
                rows.append(IRTableRow(id=row_id, cells=cells))
            blocks.append(IRTable(id=tid, rows=rows))
            t_index += 1

    ir = DocumentIR(blocks=blocks)
    fingerprint = _sha256_text(_canonical_json(ir.model_dump()))
    return ir, fingerprint
