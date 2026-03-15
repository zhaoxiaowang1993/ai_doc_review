import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple
from pathlib import Path
import json
from difflib import SequenceMatcher
import hashlib
import re
import html
import zipfile
import struct

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field, model_validator
from typing import Literal
import fitz

from common.logger import get_logger
from common.models import DocumentIR, Issue, IssueStatusEnum, IssueType, Location, LocationAnchor, LocationTypeEnum, ReviewRule, RiskLevel
from config.config import settings
from services.bbox import bbox_to_quadpoints
from services.mineru_client import MinerUClient
from services.paddleocr_client import PaddleOCRJobsClient

logging = get_logger(__name__)

IssueTypeLiteral = Literal["Grammar & Spelling", "Definitive Language"]


class ReviewIssue(BaseModel):
    type: str  # Changed to str to support custom rule names
    text: str = Field(description="A short snippet of the problematic text")
    explanation: str
    suggested_fix: str = ""
    para_index: int = Field(description="Index of the paragraph in the provided chunk input")

    model_config = {"extra": "ignore"}

    @model_validator(mode="before")
    @classmethod
    def _normalize_keys(cls, data: Any):
        if not isinstance(data, dict):
            return data
        if "suggested_fix" not in data:
            for k in ("suggestation", "suggestion", "suggestedFix", "fix"):
                v = data.get(k)
                if isinstance(v, str) and v.strip():
                    data["suggested_fix"] = v
                    break
        if "para_index" in data and not isinstance(data["para_index"], int):
            try:
                data["para_index"] = int(data["para_index"])
            except Exception:
                data["para_index"] = 0
        return data


class ReviewOutput(BaseModel):
    issues: List[ReviewIssue]


def _parse_review_output_best_effort(parser: PydanticOutputParser, content: str) -> List[ReviewIssue]:
    try:
        out = parser.parse(str(content))
        return list(out.issues or [])
    except Exception:
        pass

    s = str(content or "").strip()
    if not s:
        return []
    if "```" in s:
        s = s.replace("```json", "").replace("```JSON", "").replace("```", "").strip()

    start = s.find("{")
    end = s.rfind("}")
    if start < 0 or end <= start:
        return []
    raw = s[start : end + 1]
    try:
        data = json.loads(raw)
    except Exception:
        return []
    issues = data.get("issues") if isinstance(data, dict) else None
    if not isinstance(issues, list):
        return []

    parsed: list[ReviewIssue] = []
    for it in issues:
        if not isinstance(it, dict):
            continue
        try:
            parsed.append(ReviewIssue.model_validate(it))
        except Exception:
            continue
    return parsed


SYSTEM_PROMPT = """You are an expert document reviewer.
Identify issues in the provided text.
Issue types allowed:
- Grammar & Spelling
- Definitive Language

The document may be in Chinese or English. Apply the rules appropriately.
Use the paragraph indices provided in the input (e.g. [0], [1], ...).
Return structured output that matches the requested schema.
"""


def _build_system_prompt(custom_rules: List[ReviewRule] | None = None) -> str:
    """Build system prompt with custom rules if provided."""
    issue_types = ["- Grammar & Spelling", "- Definitive Language"]

    if custom_rules:
        for rule in custom_rules:
            issue_types.append(f"- {rule.name}")

    return f"""你是一位专业的文档审核专家。请识别文本中的真正问题。

允许报告的问题类型：
{chr(10).join(issue_types)}

⚠️ 极其重要的排除规则（以下情况绝对不是问题，必须忽略）：

1. **序号和编号（最常见的误判！）**：
   - 任何形式的列表序号：1、2、3、(1)、(2)、(一)、(二)、①、②、a、b、A、B 等
   - 孤立的数字或字母：如果段落只包含 "1"、"2"、"a" 等单个字符，这是序号，不是错误
   - 带括号的序号：（1）、（2）、(1)、(2)、[1]、[2] 等
   - 即使解析后序号与内容分离，也不是错误

2. **表单模板占位符**：
   - 日期格式：年/月/日、____年____月____日
   - 金额格式：___元、____元整
   - 空白下划线：_____、______
   - 待填写字段

3. **勾选框和选项符号**：口、□、☐、○、◯ 等

4. **格式化标记**：冒号、破折号、分隔线

5. **合同/表单标准文本**：甲方、乙方、签字、盖章、薪资结算、工资发放 等

🚫 特别强调：不要把以下情况报告为错误：
- 段落内容为单个数字（如 "1"、"2"）→ 这是序号
- 段落内容为 "(1)"、"(2)" → 这是带括号的序号
- 段落内容包含 "年 月 日" → 这是日期占位符
- 段落内容包含 "___元" → 这是金额占位符

只报告真正的内容问题（如：错别字、病句、不当承诺语）。
使用输入中提供的段落索引（如 [0], [1], ...）。
对于每条问题，text 必须是可定位的原文片段，优先返回 10-40 个字符的连续片段，避免过短/泛化片段（如“本合同”“甲方”“乙方”等）。
按照要求的 JSON 格式输出结果。
"""


def _build_guidance(custom_rules: List[ReviewRule] | None = None) -> str:
    """Build guidance section with custom rules."""
    lines = [
        "审核指南：",
        "- Grammar & Spelling (语法与拼写): 真正的语病、错别字、标点错误、语法错误。",
        "- Definitive Language (绝对化表述): 在正式承诺或保证语境中使用'必须/保证/一定/完全/绝对'等过度确定措辞。",
        "",
        "⚠️ 再次强调：以下不是错误，请跳过：",
        "- 序号（1、2、(1)、(2)、①、②、一、二 等）",
        "- 孤立数字（如段落只有 '1' 或 '2'）→ 这是列表序号",
        "- 日期占位符（年 月 日、____年____月）",
        "- 金额占位符（___元、计 元）",
        "- 勾选框（口、□）",
        "- 合同模板字段（甲方、乙方、签字盖章）",
        "",
        "如果不确定是否是错误，宁可不报告。",
    ]

    if custom_rules:
        lines.append("")
        lines.append("自定义规则：")
        for rule in custom_rules:
            guidance = f"- {rule.name}: {rule.description}"
            if rule.examples:
                examples_str = "; ".join([f'"{ex.text}"' for ex in rule.examples[:3]])
                guidance += f" 示例: {examples_str}"
            lines.append(guidance)

    return "\n".join(lines)


class LangChainPipeline:
    def __init__(self) -> None:
        # Prefer LangChain v1 provider-based initialization for DeepSeek.
        # This avoids OpenAI "response_format" structured output features that DeepSeek may not support.
        self.llm = _init_deepseek_model()
        self.parser = PydanticOutputParser(pydantic_object=ReviewOutput)
        self.mineru = MinerUClient()

    async def stream_issues(
        self,
        *,
        doc_id: str,
        pdf_path: str,
        user_id: str,
        timestamp_iso: str,
        cache_key: str,
        custom_rules: List[ReviewRule] | None = None,
    ) -> AsyncGenerator[List[Issue], None]:
        """End-to-end: MinerU parse -> chunk -> LLM -> yield Issue list per chunk."""
        payload = await self.mineru.extract(Path(pdf_path), data_id=doc_id, cache_key=cache_key)
        meta = payload.get("meta") if isinstance(payload, dict) else None
        paragraphs = self.mineru.to_paragraphs(payload)
        doc_name = Path(pdf_path).name
        logging.info(f"MinerU paragraphs extracted: {len(paragraphs)} for {doc_name}")
        if custom_rules:
            logging.info(f"Custom rules enabled: {[r.name for r in custom_rules]}")
        if settings.debug and paragraphs:
            logging.debug(f"MinerU paragraph sample: {paragraphs[0].get('content', '')[:200]}")
        if not paragraphs:
            raise RuntimeError("MinerU 解析结果中未提取到段落文本（可能是返回 JSON 结构变化或解析字段不匹配）。")

        page_sizes = _get_pdf_page_sizes(pdf_path)
        page_bbox_space = _get_page_bbox_space(paragraphs)
        layout = _load_mineru_layout(meta, cache_key)

        chunks = self._chunk_paragraphs(paragraphs, settings.pagination)
        logging.info(f"Chunk count: {len(chunks)} (pagination={settings.pagination})")
        for chunk_index, chunk in enumerate(chunks):
            issues = await self._process_chunk(
                chunk,
                chunk_index,
                user_id,
                timestamp_iso,
                doc_id,
                doc_name,
                pdf_path,
                cache_key,
                page_sizes,
                page_bbox_space,
                layout,
                custom_rules,
            )
            if issues:
                yield issues

    async def stream_ir_issues(
        self,
        *,
        doc_id: str,
        ir: DocumentIR,
        user_id: str,
        timestamp_iso: str,
        custom_rules: List[ReviewRule] | None = None,
    ) -> AsyncGenerator[List[Issue], None]:
        paragraphs = self._ir_to_paragraphs(ir)
        if not paragraphs:
            raise RuntimeError("IR 解析结果中未提取到段落文本。")

        chunks = self._chunk_paragraphs(paragraphs, settings.pagination)
        logging.info(f"IR chunk count: {len(chunks)} (pagination={settings.pagination})")
        for chunk_index, chunk in enumerate(chunks):
            issues = await self._process_ir_chunk(
                chunk=chunk,
                chunk_index=chunk_index,
                user_id=user_id,
                timestamp_iso=timestamp_iso,
                doc_id=doc_id,
                custom_rules=custom_rules,
            )
            if issues:
                yield issues

    async def _process_ir_chunk(
        self,
        *,
        chunk: List[Dict[str, Any]],
        chunk_index: int,
        user_id: str,
        timestamp_iso: str,
        doc_id: str,
        custom_rules: List[ReviewRule] | None = None,
    ) -> List[Issue]:
        prepared = "\n".join([f"[{i}]{p['content']}" for i, p in enumerate(chunk)])

        system_prompt = _build_system_prompt(custom_rules)
        guidance = _build_guidance(custom_rules)

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(
                content=(
                    f"Chunk {chunk_index}. Paragraphs with indices:\n{prepared}\n\n"
                    f"{guidance}\n"
                    "Return issues; if none, return an empty list.\n\n"
                    f"{self.parser.get_format_instructions()}"
                )
            ),
        ]

        try:
            resp = await self.llm.ainvoke(messages)
            content = resp.content if hasattr(resp, "content") else resp
            if isinstance(content, list):
                content = "".join([c.get("text", "") if isinstance(c, dict) else str(c) for c in content])
            raw_issues = _parse_review_output_best_effort(self.parser, str(content))
        except Exception as e:
            logging.error(f"LLM output parse failed: {e}")
            return []

        issues: List[Issue] = []
        seen: set[tuple[int, str, str]] = set()
        for raw in raw_issues or []:
            issue_type = raw.type if isinstance(raw, ReviewIssue) else IssueType.GrammarSpelling.value
            risk_level = self._get_risk_level_for_type(issue_type, custom_rules)
            local_index = raw.para_index if isinstance(raw, ReviewIssue) else 0
            para = chunk[local_index] if 0 <= local_index < len(chunk) else chunk[0]
            if "global_index" in para:
                global_index = int(para.get("global_index") or 0)
            else:
                if settings.pagination == -1:
                    global_index = int(local_index)
                else:
                    global_index = int(chunk_index * settings.pagination + local_index)

            needle_text = raw.text if isinstance(raw, ReviewIssue) else None
            key = (
                int(global_index),
                str(issue_type),
                _normalize_for_match(str(needle_text or "")).replace(" ", ""),
            )
            if key in seen:
                continue
            seen.add(key)

            node_id, path, start, end = self._locate_ir_anchor_location(para=para, needle=needle_text)
            location = Location(
                type=LocationTypeEnum.ir_anchor,
                source_sentence=para.get("content"),
                para_index=global_index,
                node_id=node_id,
                path=path,
                start_offset=start,
                end_offset=end,
            )

            issues.append(
                Issue(
                    id=str(uuid.uuid4()),
                    doc_id=doc_id,
                    text=(needle_text if isinstance(needle_text, str) and needle_text.strip() else (para.get("content") or "")[:120]),
                    type=issue_type,
                    status=IssueStatusEnum.not_reviewed,
                    suggested_fix=(raw.suggested_fix if isinstance(raw, ReviewIssue) else ""),
                    explanation=(raw.explanation if isinstance(raw, ReviewIssue) else ""),
                    risk_level=risk_level,
                    location=location,
                    review_initiated_by=user_id,
                    review_initiated_at_UTC=timestamp_iso,
                )
            )

        return issues

    def _chunk_paragraphs(self, paragraphs: List[Dict[str, Any]], size: int) -> List[List[Dict[str, Any]]]:
        if size == -1:
            return [paragraphs]
        return [paragraphs[i : i + size] for i in range(0, len(paragraphs), size)]

    def _ir_to_paragraphs(self, ir: DocumentIR) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        g = 0
        for b in ir.blocks:
            if getattr(b, "type", "") == "paragraph":
                text = "".join([r.text for r in (b.runs or [])])
                out.append(
                    {"content": text, "node_id": b.id, "path": [b.id], "block_type": "paragraph", "global_index": g}
                )
                g += 1
            elif getattr(b, "type", "") == "table":
                for row in b.rows or []:
                    for cell in row.cells or []:
                        for p in cell.blocks or []:
                            text = "".join([r.text for r in (p.runs or [])])
                            out.append(
                                {
                                    "content": text,
                                    "node_id": p.id,
                                    "path": [b.id, row.id, cell.id, p.id],
                                    "block_type": "table",
                                    "global_index": g,
                                }
                            )
                            g += 1
        return out

    def _locate_ir_anchor_location(
        self, *, para: Dict[str, Any], needle: Optional[str]
    ) -> tuple[str | None, list[str] | None, int, int]:
        node_id = para.get("node_id")
        path = para.get("path")
        content = str(para.get("content") or "")
        t = (needle or "").strip()
        if not t:
            start = 0
            end = min(len(content), 64)
            return node_id, path, start, end

        start = content.find(t)
        if start < 0:
            n1 = _normalize_for_match(content).replace(" ", "")
            n2 = _normalize_for_match(t).replace(" ", "")
            idx = n1.find(n2)
            if idx >= 0:
                start = idx
                end = min(len(content), start + len(t))
                return node_id, path, start, end
            start = 0
            end = min(len(content), max(len(t), 64))
            return node_id, path, start, end

        end = start + len(t)
        return node_id, path, start, end

    def _get_risk_level_for_type(
        self,
        issue_type: str,
        custom_rules: List[ReviewRule] | None = None
    ) -> RiskLevel:
        """
        根据问题类型确定风险等级。
        - 预设类型 "Definitive Language" -> 高
        - 预设类型 "Grammar & Spelling" -> 低
        - 自定义规则 -> 使用规则定义的风险等级
        - 未知类型 -> 中
        """
        # 预设类型的风险等级映射
        preset_risk_levels = {
            IssueType.DefinitiveLanguage.value: RiskLevel.high,
            "Definitive Language": RiskLevel.high,
            IssueType.GrammarSpelling.value: RiskLevel.low,
            "Grammar & Spelling": RiskLevel.low,
        }
        
        # 先检查预设类型
        if issue_type in preset_risk_levels:
            return preset_risk_levels[issue_type]
        
        # 检查自定义规则
        if custom_rules:
            for rule in custom_rules:
                if rule.name == issue_type:
                    return rule.risk_level
        
        # 默认返回中等风险
        return RiskLevel.medium

    async def _process_chunk(
        self,
        chunk: List[Dict[str, Any]],
        chunk_index: int,
        user_id: str,
        timestamp_iso: str,
        doc_id: str,
        doc_name: str,
        pdf_path: str,
        cache_key: str,
        page_sizes: Dict[int, tuple[float, float]],
        page_bbox_space: Dict[int, Dict[str, Any]],
        layout: Dict[str, Any] | None,
        custom_rules: List[ReviewRule] | None = None,
    ) -> List[Issue]:
        prepared = "\n".join([f"[{i}]{p['content']}" for i, p in enumerate(chunk)])

        # Build dynamic prompts with custom rules
        system_prompt = _build_system_prompt(custom_rules)
        guidance = _build_guidance(custom_rules)

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(
                content=(
                    f"Chunk {chunk_index}. Paragraphs with indices:\n{prepared}\n\n"
                    f"{guidance}\n"
                    "Return issues; if none, return an empty list.\n\n"
                    f"{self.parser.get_format_instructions()}"
                )
            ),
        ]

        try:
            resp = await self.llm.ainvoke(messages)
            content = resp.content if hasattr(resp, "content") else resp
            if isinstance(content, list):
                content = "".join(
                    [c.get("text", "") if isinstance(c, dict) else str(c) for c in content]
                )
            raw_issues = _parse_review_output_best_effort(self.parser, str(content))
        except Exception as e:
            logging.error(f"LLM output parse failed: {e}")
            return []

        issues: List[Issue] = []
        seen: set[tuple[int, str, str]] = set()
        for raw in raw_issues or []:
            # Use the type directly - it can be a built-in type or custom rule name
            issue_type = raw.type if isinstance(raw, ReviewIssue) else IssueType.GrammarSpelling.value

            # Determine risk level based on issue type
            risk_level = self._get_risk_level_for_type(issue_type, custom_rules)

            para_index = raw.para_index if isinstance(raw, ReviewIssue) else 0
            para = chunk[para_index] if 0 <= para_index < len(chunk) else chunk[0]

            needle_text = raw.text if isinstance(raw, ReviewIssue) else None
            key = (
                int(para_index),
                str(issue_type),
                _normalize_for_match(str(needle_text or "")).replace(" ", ""),
            )
            if key in seen:
                continue
            seen.add(key)

            page_num, bbox, anchors = await _locate_issue_location(
                pdf_path=pdf_path,
                para=para,
                para_index=para_index,
                cache_key=cache_key,
                page_sizes=page_sizes,
                page_bbox_space=page_bbox_space,
                layout=layout,
                needle=needle_text,
            )
            location = Location(
                source_sentence=para["content"],
                page_num=page_num,
                bounding_box=bbox,
                para_index=para_index,
                anchors=anchors,
            )

            display_text = needle_text
            if isinstance(display_text, str) and display_text.strip():
                nn = _normalize_for_match(display_text).replace(" ", "")
                src = str(para.get("content") or "")
                if len(nn) < 8 and src:
                    idx = src.find(display_text)
                    if idx >= 0:
                        a = max(0, idx - 16)
                        b = min(len(src), idx + len(display_text) + 16)
                        display_text = src[a:b].strip() or display_text

            issues.append(
                Issue(
                    id=str(uuid.uuid4()),
                    doc_id=doc_id,
                    text=(display_text if isinstance(display_text, str) else para["content"][:120]),
                    type=issue_type,
                    status=IssueStatusEnum.not_reviewed,
                    suggested_fix=(raw.suggested_fix if isinstance(raw, ReviewIssue) else ""),
                    explanation=(raw.explanation if isinstance(raw, ReviewIssue) else ""),
                    risk_level=risk_level,
                    location=location,
                    review_initiated_by=user_id,
                    review_initiated_at_UTC=timestamp_iso,
                )
            )

        return issues


async def _locate_issue_location(
    *,
    pdf_path: str,
    para: Dict[str, Any],
    para_index: int,
    cache_key: str,
    page_sizes: Dict[int, tuple[float, float]],
    page_bbox_space: Dict[int, Dict[str, Any]],
    layout: Dict[str, Any] | None,
    needle: Optional[str],
) -> Tuple[int, List[float], Optional[List[LocationAnchor]]]:
    para_page = int(para.get("page_num", 1) or 1)
    bt = str(para.get("block_type") or "").lower()
    is_table = bt in ("table", "table_body")
    page_count = max(page_sizes.keys()) if page_sizes else para_page
    search_radius = 24 if is_table else 0
    anchor_text = (needle or "").strip() or None
    fallback_sentence = str(para.get("content") or "").strip() or None

    anchors: list[tuple[float, LocationAnchor]] = []
    attempts: list[dict[str, Any]] = []

    def _sig(s: str | None) -> dict[str, Any]:
        if not s:
            return {"len": 0, "sha256": "", "head": ""}
        t = str(s)
        return {"len": len(t), "sha256": hashlib.sha256(t.encode("utf-8")).hexdigest()[:12], "head": t[:24]}

    def add_pdf_anchors(page_num: int, score: float) -> bool:
        if not anchor_text and not fallback_sentence:
            return False
        text_len = None
        if settings.debug:
            try:
                text_len = _pdf_text_len(pdf_path, page_num)
            except Exception:
                text_len = None
        rects = _find_pdf_rects(pdf_path, page_num, needle=anchor_text, fallback_sentence=fallback_sentence)
        if settings.debug:
            attempts.append(
                {
                    "page_num": page_num,
                    "kind": "pdf",
                    "rects": len(rects or []),
                    "text_len": text_len,
                    "needle": _sig(anchor_text),
                }
            )
        if not rects:
            return False
        page_h = float(page_sizes.get(page_num, (0.0, 0.0))[1] or 0.0)
        if page_h <= 0:
            return False
        rect_quads: list[list[float]] = []
        for r in rects[:6]:
            x0, y0, x1, y1 = float(r.x0), float(r.y0), float(r.x1), float(r.y1)
            quad = [
                round(x0, 2),
                round(page_h - y0, 2),
                round(x1, 2),
                round(page_h - y0, 2),
                round(x0, 2),
                round(page_h - y1, 2),
                round(x1, 2),
                round(page_h - y1, 2),
            ]
            rect_quads.append(quad)
        if not rect_quads:
            return False
        if len(rect_quads) == 1:
            anchors.append((score, LocationAnchor(page_num=page_num, bounding_box=rect_quads[0], source_text=anchor_text)))
            return True
        combined: list[float] = []
        for q in rect_quads:
            combined.extend(q)
        anchors.append((score + 0.01, LocationAnchor(page_num=page_num, bounding_box=combined, source_text=anchor_text)))
        for q in rect_quads:
            anchors.append((score, LocationAnchor(page_num=page_num, bounding_box=q, source_text=anchor_text)))
        return True

    def add_layout_anchor(page_num: int, score: float) -> bool:
        bbox = _find_layout_quadpoints(
            layout,
            page_num,
            page_size_points=page_sizes.get(page_num),
            needle=anchor_text,
            fallback_sentence=fallback_sentence,
        )
        if settings.debug:
            attempts.append(
                {
                    "page_num": page_num,
                    "kind": "layout",
                    "hit": bool(bbox),
                    "needle": _sig(anchor_text),
                }
            )
        if not bbox:
            return False
        anchors.append((score, LocationAnchor(page_num=page_num, bounding_box=bbox, source_text=anchor_text)))
        return True

    async def add_paddleocr_anchor(page_num: int, score: float) -> bool:
        if not is_table:
            return False
        if not settings.paddleocr_enabled or not settings.paddleocr_job_url or not settings.paddleocr_token:
            return False
        queries = [q for q in [anchor_text, fallback_sentence] if q and str(q).strip()]
        if not queries:
            return False
        picked = _pick_layout_table_image(layout, page_num, queries)
        if not picked:
            if settings.debug:
                attempts.append({"page_num": page_num, "kind": "paddleocr", "hit": False, "reason": "no_table_image"})
            return False
        image_path, table_bbox, observed_max = picked
        img_bytes = _read_mineru_cached_image_bytes(cache_key, image_path)
        if not img_bytes:
            if settings.debug:
                attempts.append({"page_num": page_num, "kind": "paddleocr", "hit": False, "reason": "zip_missing"})
            return False
        size = _image_size(img_bytes)
        if not size:
            if settings.debug:
                attempts.append({"page_num": page_num, "kind": "paddleocr", "hit": False, "reason": "image_size"})
            return False
        img_w, img_h = size
        try:
            client = PaddleOCRJobsClient(
                job_url=settings.paddleocr_job_url,
                token=settings.paddleocr_token,
                model=settings.paddleocr_model,
                poll_interval_sec=settings.paddleocr_poll_interval_sec,
                max_wait_sec=settings.paddleocr_max_wait_sec,
            )
            raw = await client.parse_image(img_bytes)
            pruned = _extract_first_pruned_result(raw)
            page_size_points = page_sizes.get(page_num)
            if not page_size_points or page_size_points[0] <= 0 or page_size_points[1] <= 0:
                return False
            page_w, page_h = float(page_size_points[0]), float(page_size_points[1])
            img_ratio = float(img_w) / float(img_h) if img_h else 0.0
            page_ratio = page_w / page_h if page_h else 0.0
            is_full_page = abs(img_ratio - page_ratio) < 0.03 and float(img_w) > page_w * 1.2

            region_px = None
            if is_full_page and isinstance(table_bbox, list) and len(table_bbox) == 4:
                sx = float(img_w) / page_w if page_w else 1.0
                sy = float(img_h) / page_h if page_h else 1.0
                tx0, ty0, tx1, ty1 = [float(v) for v in table_bbox]
                region_px = [tx0 * sx, ty0 * sy, tx1 * sx, ty1 * sy]

            best = _best_text_bbox_px(pruned, queries, image_size=(img_w, img_h), region_px=region_px)
            if not best:
                if settings.debug:
                    attempts.append({"page_num": page_num, "kind": "paddleocr", "hit": False, "reason": "no_match"})
                return False
            bbox_img, best_score = best
            if is_full_page:
                quad = bbox_to_quadpoints(
                    bbox_img,
                    page_size_points,
                    origin="top-left",
                    units="px",
                    observed_max=(float(img_w), float(img_h)),
                    content_coverage=1.0,
                )
            else:
                bbox_page = _map_bbox_from_crop_to_page(bbox_img, (img_w, img_h), table_bbox)
                quad = bbox_to_quadpoints(
                    bbox_page,
                    page_size_points,
                    origin="top-left",
                    units="pt",
                )
            if not quad:
                return False
            anchors.append((score + 0.05 * float(best_score), LocationAnchor(page_num=page_num, bounding_box=quad, source_text=anchor_text)))
            logging.info(
                json.dumps(
                    {
                        "event": "paddleocr_anchor",
                        "page_num": page_num,
                        "para_index": para_index,
                        "score": round(float(best_score), 3),
                        "image": str(Path(image_path).name),
                    },
                    ensure_ascii=False,
                )
            )
            if settings.debug:
                attempts.append(
                    {
                        "page_num": page_num,
                        "kind": "paddleocr",
                        "hit": True,
                        "score": round(float(best_score), 3),
                        "image": str(Path(image_path).name),
                    }
                )
            return True
        except Exception as e:
            if settings.debug:
                attempts.append({"page_num": page_num, "kind": "paddleocr", "hit": False, "error": str(e)[:120]})
            return False

    for pn in _page_window(para_page, page_count, search_radius):
        if add_pdf_anchors(pn, score=1.0 - 0.001 * abs(pn - para_page)):
            break

    if not anchors:
        for pn in _page_window(para_page, page_count, search_radius):
            if await add_paddleocr_anchor(pn, score=0.9 - 0.001 * abs(pn - para_page)):
                break

    if not anchors:
        for pn in _page_window(para_page, page_count, search_radius):
            if add_layout_anchor(pn, score=0.8 - 0.001 * abs(pn - para_page)):
                break

    if anchors:
        anchors.sort(key=lambda x: x[0], reverse=True)
        best = anchors[0][1]
        if settings.debug:
            logging.debug(
                json.dumps(
                    {
                        "event": "locate_issue_location",
                        "para_index": para_index,
                        "para_page": para_page,
                        "is_table": is_table,
                        "resolved_page": best.page_num,
                        "anchors": len(anchors),
                        "attempts": attempts[:16],
                    },
                    ensure_ascii=False,
                )
            )
        return best.page_num, best.bounding_box, [a for _, a in anchors]

    space = page_bbox_space.get(para_page) or {}
    observed_max = space.get("observed_max")
    coverage = 1.0 if space.get("is_canvas") else settings.mineru_bbox_content_coverage
    bbox = bbox_to_quadpoints(
        para.get("bbox"),
        page_sizes.get(para_page),
        origin=settings.mineru_bbox_origin,
        units=settings.mineru_bbox_units,
        observed_max=observed_max,
        content_coverage=coverage,
    )
    if not bbox:
        bbox = [0, 0, 0, 0, 0, 0, 0, 0]
    if settings.debug:
        logging.debug(
            json.dumps(
                {
                    "event": "locate_issue_location",
                    "para_index": para_index,
                    "para_page": para_page,
                    "is_table": is_table,
                    "resolved_page": para_page,
                    "anchors": 0,
                    "fallback": "para_bbox",
                    "attempts": attempts[:16],
                },
                ensure_ascii=False,
            )
        )
    return para_page, bbox, None


def _page_window(center: int, page_count: int, radius: int) -> List[int]:
    if radius <= 0:
        return [max(1, min(page_count, center))]
    out: list[int] = []
    c = max(1, min(page_count, center))
    out.append(c)
    for d in range(1, radius + 1):
        p1 = c + d
        p2 = c - d
        if p1 <= page_count:
            out.append(p1)
        if p2 >= 1:
            out.append(p2)
    return out


def _mineru_cache_base_dir() -> Path:
    base = Path(settings.mineru_cache_dir)
    if base.is_absolute():
        return base
    return (Path(__file__).resolve().parents[1] / base).resolve()


def _read_mineru_cached_image_bytes(cache_key: str, image_path: str) -> bytes | None:
    try:
        zip_path = _mineru_cache_base_dir() / f"{cache_key}.zip"
        if not zip_path.exists():
            return None
        with zipfile.ZipFile(zip_path) as zf:
            try:
                return zf.read(image_path)
            except KeyError:
                alt = f"images/{Path(image_path).name}"
                try:
                    return zf.read(alt)
                except KeyError:
                    return None
    except Exception:
        return None


def _png_size(head: bytes) -> tuple[int, int] | None:
    if len(head) < 24:
        return None
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    try:
        w = struct.unpack(">I", head[16:20])[0]
        h = struct.unpack(">I", head[20:24])[0]
        return int(w), int(h)
    except Exception:
        return None


def _jpg_size(head: bytes) -> tuple[int, int] | None:
    if len(head) < 4 or head[0:2] != b"\xff\xd8":
        return None
    i = 2
    n = len(head)
    while i + 9 < n:
        if head[i] != 0xFF:
            i += 1
            continue
        marker = head[i + 1]
        if marker in (0xC0, 0xC2):
            try:
                h = (head[i + 5] << 8) + head[i + 6]
                w = (head[i + 7] << 8) + head[i + 8]
                return int(w), int(h)
            except Exception:
                return None
        if i + 4 >= n:
            break
        seg_len = (head[i + 2] << 8) + head[i + 3]
        if seg_len <= 0:
            break
        i += 2 + seg_len
    return None


def _image_size(image_bytes: bytes) -> tuple[int, int] | None:
    head = image_bytes[:4096]
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return _png_size(head)
    if head.startswith(b"\xff\xd8"):
        return _jpg_size(head)
    return None


def _extract_first_pruned_result(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        if isinstance(payload.get("prunedResult"), dict):
            return payload["prunedResult"]
        for v in payload.values():
            pr = _extract_first_pruned_result(v)
            if pr:
                return pr
    if isinstance(payload, list):
        for it in payload:
            pr = _extract_first_pruned_result(it)
            if pr:
                return pr
    return {}


def _iter_text_boxes(obj: Any) -> list[tuple[str, list[float]]]:
    out: list[tuple[str, list[float]]] = []
    if isinstance(obj, dict):
        text = obj.get("text") or obj.get("content")
        bbox = obj.get("bbox") or obj.get("box") or obj.get("bounding_box") or obj.get("boundingBox")
        if isinstance(text, str) and isinstance(bbox, list):
            bb = _rect_from_any_bbox(bbox)
            if bb:
                out.append((text, bb))
        for v in obj.values():
            out.extend(_iter_text_boxes(v))
    elif isinstance(obj, list):
        for it in obj:
            out.extend(_iter_text_boxes(it))
    return out


def _rect_from_any_bbox(bbox: Any) -> list[float] | None:
    if not isinstance(bbox, list) or not bbox:
        return None
    if len(bbox) == 4 and all(isinstance(v, (int, float)) for v in bbox):
        x0, y0, x1, y1 = [float(v) for v in bbox]
        return [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)]
    if len(bbox) >= 8 and all(isinstance(v, (int, float)) for v in bbox[:8]):
        coords = [float(v) for v in bbox[:8]]
        xs = coords[0::2]
        ys = coords[1::2]
        return [min(xs), min(ys), max(xs), max(ys)]
    if all(isinstance(p, list) and len(p) >= 2 for p in bbox[:8]):
        xs = [float(p[0]) for p in bbox]
        ys = [float(p[1]) for p in bbox]
        return [min(xs), min(ys), max(xs), max(ys)]
    return None


def _normalize_compact(s: str) -> str:
    t = _normalize_for_match(s)
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", t)


def _match_score(query: str, candidate: str) -> float:
    q = _normalize_compact(query)
    c = _normalize_compact(candidate)
    if not q or not c:
        return 0.0
    if q in c:
        return 1.0
    ratio = SequenceMatcher(a=q, b=c).ratio()
    if len(q) >= 4:
        grams = {q[i : i + 2] for i in range(0, len(q) - 1)}
        if grams:
            hit = sum(1 for g in grams if g in c)
            overlap = hit / len(grams)
            ratio = max(ratio, overlap)
    return float(ratio)


def _best_text_bbox(pruned: Any, queries: list[str]) -> tuple[list[float], float] | None:
    boxes = _iter_text_boxes(pruned)
    best_bbox = None
    best_score = 0.0
    for text, bbox in boxes:
        s = 0.0
        for q in queries:
            s = max(s, _match_score(q, text))
        if s > best_score:
            best_score = s
            best_bbox = bbox
    if not best_bbox or best_score < 0.62:
        return None
    return best_bbox, best_score


def _best_text_bbox_px(
    pruned: Any,
    queries: list[str],
    *,
    image_size: tuple[int, int],
    region_px: list[float] | None = None,
) -> tuple[list[float], float] | None:
    img_w, img_h = float(image_size[0]), float(image_size[1])
    boxes = _iter_text_boxes(pruned)
    best_bbox = None
    best_score = 0.0

    rx0 = ry0 = rx1 = ry1 = None
    if region_px and len(region_px) == 4:
        rx0, ry0, rx1, ry1 = [float(v) for v in region_px]
        if rx0 > rx1:
            rx0, rx1 = rx1, rx0
        if ry0 > ry1:
            ry0, ry1 = ry1, ry0
        pad = max((rx1 - rx0) * 0.02, (ry1 - ry0) * 0.02, 6.0)
        rx0 -= pad
        ry0 -= pad
        rx1 += pad
        ry1 += pad

    for text, bbox in boxes:
        x0, y0, x1, y1 = [float(v) for v in bbox]
        if max(abs(x0), abs(y0), abs(x1), abs(y1)) <= 1.5:
            x0 *= img_w
            x1 *= img_w
            y0 *= img_h
            y1 *= img_h
        bx0, bx1 = (x0, x1) if x0 <= x1 else (x1, x0)
        by0, by1 = (y0, y1) if y0 <= y1 else (y1, y0)

        if rx0 is not None:
            cx = (bx0 + bx1) / 2.0
            cy = (by0 + by1) / 2.0
            if not (rx0 <= cx <= rx1 and ry0 <= cy <= ry1):
                continue

        s = 0.0
        for q in queries:
            s = max(s, _match_score(q, text))
        if s > best_score:
            best_score = s
            best_bbox = [bx0, by0, bx1, by1]

    if not best_bbox or best_score < 0.62:
        return None
    return [round(v, 2) for v in best_bbox], float(best_score)


def _pick_layout_table_image(layout: Any, page_num: int, queries: list[str]) -> tuple[str, list[float], tuple[float, float] | None] | None:
    if not isinstance(layout, dict):
        return None
    pdf_info = layout.get("pdf_info")
    if not isinstance(pdf_info, list):
        return None
    page_obj = next((p for p in pdf_info if isinstance(p, dict) and int(p.get("page_idx", -1)) == page_num - 1), None)
    if not page_obj:
        return None
    observed_max = None
    ps = page_obj.get("page_size")
    if isinstance(ps, (list, tuple)) and len(ps) == 2:
        observed_max = (float(ps[0]), float(ps[1]))
    blocks = page_obj.get("para_blocks") or []
    if not isinstance(blocks, list):
        return None

    best = None
    best_score = 0.0
    for b in blocks:
        if not isinstance(b, dict) or str(b.get("type") or "").lower() != "table":
            continue
        table_bbox = b.get("bbox")
        if not isinstance(table_bbox, list) or len(table_bbox) != 4:
            continue
        spans: list[dict[str, Any]] = []
        for sub in b.get("blocks") or []:
            if not isinstance(sub, dict):
                continue
            for ln in sub.get("lines") or []:
                if not isinstance(ln, dict):
                    continue
                for sp in ln.get("spans") or []:
                    if isinstance(sp, dict):
                        spans.append(sp)
        for sp in spans:
            ip = sp.get("image_path") or sp.get("img_path") or sp.get("imagePath")
            html_s = sp.get("html")
            if not isinstance(ip, str) or not ip:
                continue
            score = 0.0
            if isinstance(html_s, str) and html_s:
                for q in queries:
                    score = max(score, _match_score(q, html_s))
            if score > best_score:
                best_score = score
                best = (ip, [float(v) for v in table_bbox], observed_max)
    if best:
        return best
    for b in blocks:
        if not isinstance(b, dict) or str(b.get("type") or "").lower() != "table":
            continue
        table_bbox = b.get("bbox")
        if not isinstance(table_bbox, list) or len(table_bbox) != 4:
            continue
        for sub in b.get("blocks") or []:
            if not isinstance(sub, dict):
                continue
            for ln in sub.get("lines") or []:
                if not isinstance(ln, dict):
                    continue
                for sp in ln.get("spans") or []:
                    if not isinstance(sp, dict):
                        continue
                    ip = sp.get("image_path") or sp.get("img_path") or sp.get("imagePath")
                    if isinstance(ip, str) and ip:
                        return ip, [float(v) for v in table_bbox], observed_max
    return None


def _map_bbox_from_crop_to_page(bbox_img: list[float], image_size: tuple[int, int], table_bbox: list[float]) -> list[float]:
    img_w, img_h = float(image_size[0]), float(image_size[1])
    x0, y0, x1, y1 = [float(v) for v in bbox_img]
    if max(abs(x0), abs(y0), abs(x1), abs(y1)) <= 1.5:
        x0, x1 = x0 * img_w, x1 * img_w
        y0, y1 = y0 * img_h, y1 * img_h
    tx0, ty0, tx1, ty1 = [float(v) for v in table_bbox]
    tw = max(tx1 - tx0, 1.0)
    th = max(ty1 - ty0, 1.0)
    sx = tw / max(img_w, 1.0)
    sy = th / max(img_h, 1.0)
    px0 = tx0 + min(x0, x1) * sx
    px1 = tx0 + max(x0, x1) * sx
    py0 = ty0 + min(y0, y1) * sy
    py1 = ty0 + max(y0, y1) * sy
    return [round(px0, 2), round(py0, 2), round(px1, 2), round(py1, 2)]


def _find_pdf_rects(
    pdf_path: str,
    page_num: int,
    *,
    needle: str | None,
    fallback_sentence: str | None,
) -> List[fitz.Rect]:
    try:
        doc = fitz.open(pdf_path)
        if page_num < 1 or page_num > doc.page_count:
            doc.close()
            return []
        page = doc.load_page(page_num - 1)

        candidates: list[str] = []
        if needle:
            candidates.append(needle.strip())
        if fallback_sentence:
            candidates.append(str(fallback_sentence).strip())
        candidates.extend([c.replace(" ", "") for c in candidates if " " in c])

        rects: list[fitz.Rect] = []
        for c in candidates:
            if not c:
                continue
            rects = page.search_for(c)
            if rects:
                break

        if not rects and needle:
            short = needle.strip()
            if len(short) > 12:
                rects = page.search_for(short[:12])
        if not rects and needle:
            rects = _find_pdf_rects_fuzzy(page, needle.strip())

        doc.close()
        return rects or []
    except Exception:
        return []


def _find_pdf_rects_fuzzy(page: fitz.Page, needle: str) -> List[fitz.Rect]:
    if not needle:
        return []
    needle_norm = _normalize_for_match(needle).replace(" ", "")
    if not needle_norm:
        return []
    try:
        raw = page.get_text("rawdict")
    except Exception:
        return []
    if not isinstance(raw, dict):
        return []

    chars: list[tuple[str, tuple[float, float, float, float]]] = []
    for b in raw.get("blocks") or []:
        if not isinstance(b, dict):
            continue
        for ln in b.get("lines") or []:
            if not isinstance(ln, dict):
                continue
            for sp in ln.get("spans") or []:
                if not isinstance(sp, dict):
                    continue
                for ch in sp.get("chars") or []:
                    if not isinstance(ch, dict):
                        continue
                    c = str(ch.get("c", ""))
                    bbox = ch.get("bbox")
                    if not c or not isinstance(bbox, list) or len(bbox) != 4:
                        continue
                    c2 = _normalize_for_match(c).replace(" ", "")
                    if not c2:
                        continue
                    x0, y0, x1, y1 = [float(v) for v in bbox]
                    chars.append((c2, (x0, y0, x1, y1)))

    if not chars:
        return []

    text = "".join([c for c, _ in chars])
    if not text:
        return []

    rects: list[fitz.Rect] = []
    start = 0
    while True:
        idx = text.find(needle_norm, start)
        if idx < 0:
            break
        end = idx + len(needle_norm)
        boxes = [bb for _, bb in chars[idx:end] if bb]
        if boxes:
            rects.extend(_cluster_bboxes_to_rects(boxes))
        start = idx + 1
        if len(rects) >= 6:
            break
    return rects[:6]


def _cluster_bboxes_to_rects(boxes: List[tuple[float, float, float, float]]) -> List[fitz.Rect]:
    if not boxes:
        return []
    sorted_boxes = sorted(boxes, key=lambda b: (b[1], b[0]))
    groups: list[list[tuple[float, float, float, float]]] = []
    tol = 2.0
    for b in sorted_boxes:
        y0, y1 = b[1], b[3]
        placed = False
        for g in groups:
            gy0 = sum([x[1] for x in g]) / len(g)
            gy1 = sum([x[3] for x in g]) / len(g)
            if abs(y0 - gy0) <= tol or abs(y1 - gy1) <= tol:
                g.append(b)
                placed = True
                break
        if not placed:
            groups.append([b])
    out: list[fitz.Rect] = []
    for g in groups:
        x0 = min(b[0] for b in g)
        y0 = min(b[1] for b in g)
        x1 = max(b[2] for b in g)
        y1 = max(b[3] for b in g)
        out.append(fitz.Rect(x0, y0, x1, y1))
    return out


def _pdf_text_len(pdf_path: str, page_num: int) -> int:
    doc = fitz.open(pdf_path)
    if page_num < 1 or page_num > doc.page_count:
        doc.close()
        return 0
    page = doc.load_page(page_num - 1)
    try:
        txt = page.get_text("text") or ""
        return len(str(txt).strip())
    finally:
        doc.close()


def _get_pdf_page_sizes(pdf_path: str) -> Dict[int, tuple[float, float]]:
    """Returns PDF page (width,height) in points, keyed by 1-based page number."""
    sizes: Dict[int, tuple[float, float]] = {}
    try:
        doc = fitz.open(pdf_path)
        for i in range(doc.page_count):
            page = doc.load_page(i)
            rect = page.rect
            sizes[i + 1] = (float(rect.width), float(rect.height))
        doc.close()
    except Exception as e:
        logging.warning(f"Unable to read PDF page sizes for bbox conversion: {e}")
    return sizes


def _get_page_bbox_space(paragraphs: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    """
    Compute bbox coordinate space per page.
    Prefer explicit canvas_size (pixel dimensions) if available from MinerU zip.
    """
    space_by_page: Dict[int, Dict[str, Any]] = {}
    for p in paragraphs:
        try:
            page_num = int(p.get("page_num", 1) or 1)
            canvas = p.get("canvas_size")
            if isinstance(canvas, (list, tuple)) and len(canvas) == 2:
                w, h = float(canvas[0]), float(canvas[1])
                if w > 0 and h > 0:
                    space_by_page[page_num] = {"observed_max": (w, h), "is_canvas": True}
                    continue

            bbox = p.get("bbox")
            if not bbox or not isinstance(bbox, list):
                continue
            if len(bbox) == 4:
                x1, y1, x2, y2 = [float(v) for v in bbox]
                mx = max(x1, x2)
                my = max(y1, y2)
            elif len(bbox) >= 8:
                coords = [float(v) for v in bbox[:8]]
                xs = coords[0::2]
                ys = coords[1::2]
                mx = max(xs)
                my = max(ys)
            else:
                continue
            cur = space_by_page.get(page_num, {}).get("observed_max")
            if not cur:
                space_by_page[page_num] = {"observed_max": (mx, my), "is_canvas": False}
            else:
                space_by_page[page_num]["observed_max"] = (max(cur[0], mx), max(cur[1], my))
        except Exception:
            continue
    if settings.debug:
        for pn, info in sorted(space_by_page.items())[:5]:
            mx, my = info.get("observed_max", (None, None))
            logging.debug(f"MinerU bbox space page {pn}: max=({mx}, {my}), canvas={info.get('is_canvas')}")
    return space_by_page


def _find_pdf_quadpoints(
    pdf_path: str,
    page_num: int,
    *,
    needle: str | None,
    fallback_sentence: str | None,
) -> List[float] | None:
    """
    Best-effort: use PDF text coordinates for accurate highlights.
    - If PDF has real text layer, PyMuPDF can locate text and return rectangles.
    - Returns quadpoints in PDF bottom-left coordinate space (annotpdf compatible), can include 8*n coords.
    """
    try:
        doc = fitz.open(pdf_path)
        if page_num < 1 or page_num > doc.page_count:
            doc.close()
            return None
        page = doc.load_page(page_num - 1)
        page_h = float(page.rect.height)

        candidates: list[str] = []
        if needle:
            candidates.append(needle.strip())
        if fallback_sentence:
            candidates.append(str(fallback_sentence).strip())
        # Also try removing spaces for CJK PDFs where extraction may omit spaces
        candidates.extend([c.replace(" ", "") for c in candidates if " " in c])

        rects: list[fitz.Rect] = []
        for c in candidates:
            if not c:
                continue
            rects = page.search_for(c)
            if rects:
                break

        # If still nothing, try a shorter needle (first 12 chars) to improve hit rate
        if not rects and needle:
            short = needle.strip()
            if len(short) > 12:
                rects = page.search_for(short[:12])

        doc.close()
        if not rects:
            return None

        # Convert rects (top-left origin) to PDF quadpoints (bottom-left origin).
        # Allow multi-quad highlights (8*n).
        quadpoints: list[float] = []
        for r in rects[:6]:
            x0, y0, x1, y1 = float(r.x0), float(r.y0), float(r.x1), float(r.y1)
            quadpoints.extend(
                [
                    x0,
                    page_h - y0,
                    x1,
                    page_h - y0,
                    x0,
                    page_h - y1,
                    x1,
                    page_h - y1,
                ]
            )
        return [round(v, 2) for v in quadpoints]
    except Exception:
        return None


def _init_deepseek_model():
    """
    Initialize DeepSeek chat model using LangChain v1 init_chat_model provider API.
    Falls back to OpenAI-compatible ChatOpenAI with custom base_url if provider package isn't available.
    """
    try:
        from langchain.chat_models import init_chat_model

        # langchain-deepseek reads DEEPSEEK_API_KEY from env by default.
        if settings.deepseek_api_key:
            import os

            os.environ.setdefault("DEEPSEEK_API_KEY", settings.deepseek_api_key)
        model_name = settings.deepseek_model or "deepseek-chat"
        return init_chat_model(model_name, model_provider="deepseek", temperature=0.2)
    except Exception as e:
        logging.warning(f"init_chat_model(deepseek) unavailable, falling back to ChatOpenAI: {e}")
        return ChatOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            model=settings.deepseek_model,
            temperature=0.2,
        )


def _load_mineru_layout(meta: Dict[str, Any] | None, cache_key: str) -> Dict[str, Any] | None:
    """
    Load MinerU layout.json (line/span-level bboxes) for better highlights on PDFs without text layer.
    Prefer cached `layout_path` from MinerU meta; fall back to cache dir lookup.
    """
    try:
        layout_path = None
        if isinstance(meta, dict):
            lp = meta.get("layout_path")
            if isinstance(lp, str) and lp:
                layout_path = Path(lp)
        if not layout_path:
            layout_path = Path(settings.mineru_cache_dir) / f"{cache_key}.layout.json"
        if not layout_path.exists():
            return None
        return json.loads(layout_path.read_text(encoding="utf-8"))
    except Exception as e:
        logging.warning(f"Failed to load MinerU layout: {e}")
        return None


def _normalize_for_match(text: str) -> str:
    return (
        text.replace("\u3000", " ")
        .replace("\r", "")
        .replace("\n", "")
        .replace("\t", "")
        .strip()
    )


def _char_weight(ch: str) -> float:
    """计算字符的相对宽度权重，用于估算子串在行内的位置"""
    if not ch:
        return 0.0
    if ch.isspace():
        return 0.3
    o = ord(ch)
    # CJK 字符（中文、日文、韩文）占用更多宽度
    if 0x4E00 <= o <= 0x9FFF or 0x3400 <= o <= 0x4DBF:  # CJK Unified Ideographs
        return 1.0
    if 0x3000 <= o <= 0x303F:  # CJK Symbols and Punctuation
        return 1.0
    if 0xFF00 <= o <= 0xFFEF:  # Fullwidth Forms
        return 1.0
    if o < 128:  # ASCII
        return 0.55
    return 0.8


def _substring_bbox_from_line(line_text: str, line_bbox: list[float], start: int, end: int) -> list[float] | None:
    """基于字符权重计算子串在行内的精确 bbox"""
    if not line_bbox or len(line_bbox) != 4:
        return None
    x0, y0, x1, y1 = [float(v) for v in line_bbox]
    if x1 <= x0 or y1 <= y0:
        return None
    if start < 0 or end <= start or end > len(line_text):
        return None

    weights = [_char_weight(c) for c in line_text]
    total = sum(weights) or float(len(line_text))
    prefix = [0.0]
    for w in weights:
        prefix.append(prefix[-1] + w)

    a = prefix[start] / total
    b = prefix[end] / total
    sx0 = x0 + (x1 - x0) * a
    sx1 = x0 + (x1 - x0) * b

    # 确保最小宽度
    min_width = (x1 - x0) * 0.02  # 至少占行宽的 2%
    if sx1 - sx0 < min_width:
        mid = (sx0 + sx1) / 2.0
        sx0 = max(x0, mid - min_width / 2)
        sx1 = min(x1, mid + min_width / 2)

    return [round(sx0, 2), round(y0, 2), round(sx1, 2), round(y1, 2)]


def _find_span_match(
    spans: list[dict],
    needle: str,
    line_bbox: list[float],
) -> tuple[list[float] | None, float]:
    """
    在 spans 中查找精确匹配，返回 (bbox, score)。
    优先匹配单个 span，然后尝试跨 span 匹配。
    """
    if not spans or not needle:
        return None, 0.0

    needle_norm = _normalize_for_match(needle)
    needle_ns = needle_norm.replace(" ", "")

    # 1. 尝试在单个 span 中精确匹配
    for span in spans:
        if not isinstance(span, dict):
            continue
        content_raw = span.get("content")
        content = str(content_raw) if isinstance(content_raw, str) else ""
        span_bbox = span.get("bbox")
        if not isinstance(span_bbox, list) or len(span_bbox) != 4:
            continue
        if not content:
            html_raw = span.get("html")
            if isinstance(html_raw, str) and html_raw.strip():
                bbox = _table_html_guess_bbox(html_raw, span_bbox, needle_norm)
                if bbox:
                    return bbox, 0.7
            continue

        content_norm = _normalize_for_match(content)

        # 完全匹配
        if content_norm == needle_norm:
            return span_bbox, 1.0

        # 子串匹配
        idx = content_norm.find(needle_norm)
        if idx >= 0:
            sub_bbox = _substring_bbox_from_line(content_norm, span_bbox, idx, idx + len(needle_norm))
            return sub_bbox or span_bbox, 0.95

        # 无空格匹配
        content_ns = content_norm.replace(" ", "")
        if needle_ns in content_ns:
            return span_bbox, 0.9

    # 2. 尝试跨 span 匹配 - 拼接所有 span 内容
    full_text = ""
    span_ranges = []  # [(start, end, span_bbox), ...]
    for span in spans:
        if not isinstance(span, dict):
            continue
        content = str(span.get("content", ""))
        span_bbox = span.get("bbox")
        if content and isinstance(span_bbox, list) and len(span_bbox) == 4:
            start = len(full_text)
            full_text += content
            span_ranges.append((start, len(full_text), span_bbox))

    full_norm = _normalize_for_match(full_text)
    idx = full_norm.find(needle_norm)
    if idx >= 0:
        # 找到匹配，计算覆盖的 span 范围
        match_end = idx + len(needle_norm)
        covered_bboxes = []
        for start, end, bbox in span_ranges:
            if start < match_end and end > idx:
                covered_bboxes.append(bbox)
        if covered_bboxes:
            # 合并覆盖的 bbox
            min_x = min(b[0] for b in covered_bboxes)
            min_y = min(b[1] for b in covered_bboxes)
            max_x = max(b[2] for b in covered_bboxes)
            max_y = max(b[3] for b in covered_bboxes)
            return [min_x, min_y, max_x, max_y], 0.85

    return None, 0.0


def _strip_html_text(s: str) -> str:
    t = html.unescape(s or "")
    t = re.sub(r"(?is)<\s*br\s*/?\s*>", "\n", t)
    t = re.sub(r"(?is)</\s*(tr|p|div)\s*>", "\n", t)
    t = re.sub(r"(?is)</\s*(td|th)\s*>", "\t", t)
    t = re.sub(r"(?is)<[^>]+>", " ", t)
    t = t.replace("\u00a0", " ")
    t = re.sub(r"[ \t]+", " ", t)
    return t.strip()


def _normalize_compact_text(s: str) -> str:
    t = _normalize_for_match(s)
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", t)


def _parse_html_table_cells(table_html: str) -> list[list[dict[str, Any]]]:
    s = table_html or ""
    rows: list[list[dict[str, Any]]] = []
    for tr in re.findall(r"(?is)<\s*tr[^>]*>(.*?)</\s*tr\s*>", s):
        row: list[dict[str, Any]] = []
        for m in re.finditer(r"(?is)<\s*(td|th)([^>]*)>(.*?)</\s*(td|th)\s*>", tr):
            attrs = m.group(2) or ""
            inner = m.group(3) or ""
            rs = 1
            cs = 1
            mrs = re.search(r'(?is)rowspan\s*=\s*"?(\\d+)"?', attrs)
            if mrs:
                try:
                    rs = max(1, int(mrs.group(1)))
                except Exception:
                    rs = 1
            mcs = re.search(r'(?is)colspan\s*=\s*"?(\\d+)"?', attrs)
            if mcs:
                try:
                    cs = max(1, int(mcs.group(1)))
                except Exception:
                    cs = 1
            txt = _normalize_compact_text(_strip_html_text(inner))
            row.append({"text": txt, "rowspan": rs, "colspan": cs})
        if row:
            rows.append(row)
    return rows


def _table_html_guess_bbox(table_html: str, table_bbox: list[float], needle_norm: str) -> list[float] | None:

    if not table_bbox or len(table_bbox) != 4:
        return None
    needle_ns = _normalize_compact_text(needle_norm)
    if not needle_ns:
        return None
    rows = _parse_html_table_cells(table_html)
    if not rows:
        return None

    grid: list[list[int | None]] = []
    cell_meta: list[dict[str, Any]] = []

    def ensure_cols(r: int, c: int) -> None:
        while len(grid) <= r:
            grid.append([])
        while len(grid[r]) < c:
            grid[r].append(None)

    row_i = 0
    for row in rows:
        col_i = 0
        for cell in row:
            while True:
                ensure_cols(row_i, col_i + 1)
                if grid[row_i][col_i] is None:
                    break
                col_i += 1
            idx = len(cell_meta)
            cell_meta.append({"text": cell["text"], "r": row_i, "c": col_i, "rs": cell["rowspan"], "cs": cell["colspan"]})
            for dr in range(cell["rowspan"]):
                for dc in range(cell["colspan"]):
                    ensure_cols(row_i + dr, col_i + dc + 1)
                    grid[row_i + dr][col_i + dc] = idx
            col_i += cell["colspan"]
        row_i += 1

    row_count = len(grid)
    col_count = max((len(r) for r in grid), default=0)
    if row_count <= 0 or col_count <= 0:
        return None

    def score_cell(cell_text: str) -> float:
        if not cell_text:
            return 0.0
        if needle_ns in cell_text:
            return 1.0
        ratio = SequenceMatcher(a=needle_ns, b=cell_text).ratio()
        if ratio >= 0.72:
            return ratio
        if len(needle_ns) >= 4:
            grams = {needle_ns[i : i + 2] for i in range(0, len(needle_ns) - 1)}
            if grams:
                hit = sum(1 for g in grams if g in cell_text)
                overlap = hit / len(grams)
                if overlap >= 0.34:
                    return max(ratio, 0.66, overlap)
        for n in (6, 5, 4):
            if len(needle_ns) >= n:
                for i in range(0, min(len(needle_ns) - n + 1, 24)):
                    if needle_ns[i : i + n] in cell_text:
                        return max(ratio, 0.68)
        return ratio

    best = None
    best_score = 0.0
    for meta in cell_meta:
        s = score_cell(str(meta.get("text") or ""))
        if s > best_score:
            best_score = s
            best = meta

    if not best or best_score < 0.62:
        return None

    x0, y0, x1, y1 = [float(v) for v in table_bbox]
    w = x1 - x0
    h = y1 - y0
    if w <= 0 or h <= 0:
        return None

    r0 = int(best["r"])
    c0 = int(best["c"])
    rs = int(best["rs"])
    cs = int(best["cs"])

    bx0 = x0 + w * (c0 / col_count)
    bx1 = x0 + w * ((c0 + cs) / col_count)
    by0 = y0 + h * (r0 / row_count)
    by1 = y0 + h * ((r0 + rs) / row_count)
    return [round(bx0, 2), round(by0, 2), round(bx1, 2), round(by1, 2)]


def _find_layout_quadpoints(
    layout: Dict[str, Any] | None,
    page_num: int,
    *,
    page_size_points: tuple[float, float] | None,
    needle: str | None,
    fallback_sentence: str | None,
) -> List[float] | None:
    """
    使用 MinerU layout.json 的 span 级别 bbox 生成精确的 quadpoints。
    优先在 span 级别匹配，然后回退到行级别。
    """
    if not layout or not isinstance(layout, dict) or not page_size_points:
        return None
    pdf_info = layout.get("pdf_info")
    if not isinstance(pdf_info, list) or page_num < 1:
        return None

    page_obj = next((p for p in pdf_info if isinstance(p, dict) and int(p.get("page_idx", -1)) == page_num - 1), None)
    if not page_obj:
        return None

    page_size_px = page_obj.get("page_size")
    if not isinstance(page_size_px, (list, tuple)) or len(page_size_px) != 2:
        return None
    observed_max = (float(page_size_px[0]), float(page_size_px[1]))

    blocks = page_obj.get("para_blocks") or []
    if not isinstance(blocks, list):
        return None

    candidates = []
    if needle:
        candidates.append(str(needle))
    if fallback_sentence:
        candidates.append(str(fallback_sentence))
    candidates = [c for c in candidates if c and c.strip()]
    if not candidates:
        return None

    best_bbox = None
    best_score = 0.0

    def iter_lines(block: dict) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        direct = block.get("lines") or []
        if isinstance(direct, list):
            out.extend([ln for ln in direct if isinstance(ln, dict)])
        children = block.get("blocks") or []
        if isinstance(children, list):
            for ch in children:
                if not isinstance(ch, dict):
                    continue
                cl = ch.get("lines") or []
                if isinstance(cl, list):
                    out.extend([ln for ln in cl if isinstance(ln, dict)])
        return out

    # 1. 优先在 span 级别精确匹配
    for cand in candidates:
        for b in blocks:
            if not isinstance(b, dict):
                continue
            for ln in iter_lines(b):
                if not isinstance(ln, dict):
                    continue
                spans = ln.get("spans") or []
                line_bbox = ln.get("bbox") or b.get("bbox")
                if not isinstance(spans, list) or not line_bbox:
                    continue

                bbox, score = _find_span_match(spans, cand, line_bbox)
                if score > best_score:
                    best_score = score
                    best_bbox = bbox

                if best_score >= 0.95:
                    break
            if best_score >= 0.95:
                break
        if best_score >= 0.95:
            break

    # 2. 如果 span 匹配不够好，回退到行级别匹配
    if best_score < 0.7:
        lines: list[dict[str, Any]] = []
        for b in blocks:
            if not isinstance(b, dict):
                continue
            for ln in iter_lines(b):
                if not isinstance(ln, dict):
                    continue
                spans = ln.get("spans") or []
                if not isinstance(spans, list):
                    continue
                text = "".join([str(s.get("content", "")) for s in spans if isinstance(s, dict)])
                bbox = ln.get("bbox") or b.get("bbox")
                if not text or not isinstance(bbox, list) or len(bbox) != 4:
                    continue
                lines.append({"text": text, "bbox": bbox})

        for cand in candidates:
            cand_norm = _normalize_for_match(cand)
            cand_norm_ns = cand_norm.replace(" ", "")
            for line in lines:
                line_text = str(line["text"])
                line_bbox = line["bbox"]
                line_norm = _normalize_for_match(line_text)

                # 精确子串匹配
                idx = line_norm.find(cand_norm)
                if idx >= 0:
                    bbox_px = _substring_bbox_from_line(line_norm, line_bbox, idx, idx + len(cand_norm)) or line_bbox
                    if 0.85 > best_score:
                        best_bbox = bbox_px
                        best_score = 0.85
                    break

                # 无空格匹配
                line_ns = line_norm.replace(" ", "")
                if cand_norm_ns in line_ns:
                    if 0.75 > best_score:
                        best_bbox = line_bbox
                        best_score = 0.75
                    break

            if best_score >= 0.85:
                break

    # 3. 模糊匹配回退
    if best_score < 0.55 and needle:
        lines = []
        for b in blocks:
            if not isinstance(b, dict):
                continue
            for ln in b.get("lines") or []:
                if not isinstance(ln, dict):
                    continue
                spans = ln.get("spans") or []
                text = "".join([str(s.get("content", "")) for s in spans if isinstance(s, dict)])
                bbox = ln.get("bbox") or b.get("bbox")
                if text and isinstance(bbox, list) and len(bbox) == 4:
                    lines.append({"text": text, "bbox": bbox})

        cand_norm = _normalize_for_match(str(needle))
        for line in lines:
            line_norm = _normalize_for_match(str(line["text"]))
            ratio = SequenceMatcher(a=cand_norm, b=line_norm).ratio() if cand_norm and line_norm else 0.0
            if ratio > best_score:
                best_score = ratio
                best_bbox = line["bbox"]

        if best_score < 0.55:
            best_bbox = None

    if not best_bbox:
        return None

    if settings.debug:
        logging.debug(f"Layout match: score={best_score:.2f}, bbox={best_bbox}, needle={needle[:30] if needle else None}...")

    return bbox_to_quadpoints(
        best_bbox,
        page_size_points,
        origin="top-left",
        units="px",
        observed_max=observed_max,
        content_coverage=1.0,
    )
