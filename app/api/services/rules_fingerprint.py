import hashlib
import json
from typing import Any, Dict, Iterable, List

from common.models import ReviewRule


def build_review_rules_snapshot_items(rules: Iterable[ReviewRule]) -> List[Dict[str, Any]]:
    items = []
    for r in rules:
        items.append(
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "risk_level": r.risk_level,
            }
        )
    items.sort(key=lambda x: x["id"])
    return items


def compute_review_rules_fingerprint(rules: Iterable[ReviewRule]) -> str:
    canonical_items: List[Dict[str, Any]] = []
    for r in rules:
        canonical_items.append(
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "risk_level": r.risk_level,
                "examples": r.examples or [],
                "rule_type": r.rule_type,
                "source": r.source,
                "status": r.status,
                "is_universal": r.is_universal,
                "type_ids": sorted(list(r.type_ids or [])),
                "subtype_ids": sorted(list(r.subtype_ids or [])),
            }
        )

    canonical_items.sort(key=lambda x: x["id"])
    payload = json.dumps(canonical_items, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

