from common.logger import get_logger

# Workaround: 如果系统缺少 sqlite3 模块，使用 pysqlite3 代替
import sys
try:
    import sqlite3
except ModuleNotFoundError:
    import pysqlite3 as sqlite3
    sys.modules['sqlite3'] = sqlite3

import aiosqlite
from typing import Any, Dict, List, Optional
from pathlib import Path
from config.config import settings


logging = get_logger(__name__)


CREATE_ISSUES_TABLE = """
CREATE TABLE IF NOT EXISTS issues (
    id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    type TEXT NOT NULL,
    status TEXT NOT NULL,
    text TEXT NOT NULL,
    explanation TEXT,
    suggested_fix TEXT,
    risk_level TEXT,
    location TEXT,
    review_initiated_by TEXT,
    review_initiated_at_UTC TEXT,
    resolved_by TEXT,
    resolved_at_UTC TEXT,
    modified_fields TEXT,
    dismissal_feedback TEXT,
    feedback TEXT
);
"""

CREATE_RULES_TABLE = """
CREATE TABLE IF NOT EXISTS rules (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    examples TEXT,
    rule_type TEXT NOT NULL DEFAULT 'applicable',
    source TEXT NOT NULL DEFAULT 'custom',
    status TEXT NOT NULL DEFAULT 'active',
    is_universal INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT
);
"""

CREATE_DOCUMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    subtype_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (subtype_id) REFERENCES document_subtypes(id)
);
"""

CREATE_DOCUMENT_TYPES_TABLE = """
CREATE TABLE IF NOT EXISTS document_types (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
"""

CREATE_DOCUMENT_SUBTYPES_TABLE = """
CREATE TABLE IF NOT EXISTS document_subtypes (
    id TEXT PRIMARY KEY,
    type_id TEXT NOT NULL,
    name TEXT NOT NULL,
    FOREIGN KEY (type_id) REFERENCES document_types(id)
);
"""

CREATE_RULE_SUBTYPE_RELATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS rule_subtype_relations (
    rule_id TEXT NOT NULL,
    subtype_id TEXT NOT NULL,
    PRIMARY KEY (rule_id, subtype_id),
    FOREIGN KEY (rule_id) REFERENCES rules(id),
    FOREIGN KEY (subtype_id) REFERENCES document_subtypes(id)
);
"""

CREATE_RULE_TYPE_RELATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS rule_type_relations (
    rule_id TEXT NOT NULL,
    type_id TEXT NOT NULL,
    PRIMARY KEY (rule_id, type_id),
    FOREIGN KEY (rule_id) REFERENCES rules(id),
    FOREIGN KEY (type_id) REFERENCES document_types(id)
);
"""


class SQLiteClient:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or settings.sqlite_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    async def init_db(self) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(CREATE_ISSUES_TABLE)
            await db.execute(CREATE_RULES_TABLE)
            await db.execute(CREATE_DOCUMENTS_TABLE)
            await db.execute(CREATE_DOCUMENT_TYPES_TABLE)
            await db.execute(CREATE_DOCUMENT_SUBTYPES_TABLE)
            await db.execute(CREATE_RULE_SUBTYPE_RELATIONS_TABLE)
            await db.execute(CREATE_RULE_TYPE_RELATIONS_TABLE)
            await db.commit()
            
            # Migration: Add risk_level column to existing issues table if not exists
            try:
                await db.execute("ALTER TABLE issues ADD COLUMN risk_level TEXT")
                await db.commit()
                logging.info("Migration: Added risk_level column to issues table")
            except Exception:
                # Column already exists, ignore
                pass

            # Migration: Add rule_type column to existing rules table if not exists
            try:
                await db.execute("ALTER TABLE rules ADD COLUMN rule_type TEXT NOT NULL DEFAULT 'applicable'")
                await db.commit()
                logging.info("Migration: Added rule_type column to rules table")
            except Exception:
                pass

            # Migration: Add source column to existing rules table if not exists
            try:
                await db.execute("ALTER TABLE rules ADD COLUMN source TEXT NOT NULL DEFAULT 'custom'")
                await db.commit()
                logging.info("Migration: Added source column to rules table")
            except Exception:
                pass

            # Migration: Add is_universal column to existing rules table if not exists
            try:
                await db.execute("ALTER TABLE rules ADD COLUMN is_universal INTEGER NOT NULL DEFAULT 0")
                await db.commit()
                logging.info("Migration: Added is_universal column to rules table")
            except Exception:
                pass

            # Seed initial document types if empty
            cursor = await db.execute("SELECT COUNT(*) FROM document_types")
            count = (await cursor.fetchone())[0]
            if count == 0:
                initial_types = [
                    ("type_legal", "法律合同"),
                    ("type_medical", "医学文书"),
                    ("type_financial", "财务发票"),
                    ("type_media", "媒体文案"),
                    ("type_bidding", "投标文件"),
                ]
                for type_id, type_name in initial_types:
                    await db.execute(
                        "INSERT INTO document_types (id, name) VALUES (?, ?)",
                        (type_id, type_name)
                    )
                await db.commit()
                logging.info("Migration: Seeded initial document types")

            # Ensure universal type exists (for rules associated with 'universal')
            await db.execute(
                "INSERT OR IGNORE INTO document_types (id, name) VALUES (?, ?)",
                ("type_universal", "通用"),
            )
            await db.commit()

            # Seed initial document subtypes if empty
            cursor = await db.execute("SELECT COUNT(*) FROM document_subtypes")
            count = (await cursor.fetchone())[0]
            if count == 0:
                initial_subtypes = [
                    # 法律合同子类
                    ("subtype_labor_contract", "type_legal", "劳动合同"),
                    ("subtype_lease_contract", "type_legal", "租赁合同"),
                    ("subtype_sales_contract", "type_legal", "买卖合同"),
                    ("subtype_service_contract", "type_legal", "服务合同"),
                    ("subtype_loan_contract", "type_legal", "借款合同"),
                    # 医学文书子类
                    ("subtype_medical_record", "type_medical", "病历"),
                    ("subtype_diagnosis_report", "type_medical", "诊断报告"),
                    ("subtype_prescription", "type_medical", "处方"),
                    ("subtype_surgery_consent", "type_medical", "手术同意书"),
                    # 财务发票子类
                    ("subtype_vat_invoice", "type_financial", "增值税发票"),
                    ("subtype_receipt", "type_financial", "收据"),
                    ("subtype_expense_report", "type_financial", "费用报销单"),
                    # 媒体文案子类
                    ("subtype_ad_copy", "type_media", "广告文案"),
                    ("subtype_press_release", "type_media", "新闻稿"),
                    ("subtype_social_media", "type_media", "社交媒体内容"),
                    # 投标文件子类
                    ("subtype_bid_proposal", "type_bidding", "投标书"),
                    ("subtype_technical_spec", "type_bidding", "技术规格书"),
                    ("subtype_quotation", "type_bidding", "报价单"),
                ]
                for subtype_id, type_id, subtype_name in initial_subtypes:
                    await db.execute(
                        "INSERT INTO document_subtypes (id, type_id, name) VALUES (?, ?, ?)",
                        (subtype_id, type_id, subtype_name)
                    )
                await db.commit()
                logging.info("Migration: Seeded initial document subtypes")

            # Ensure universal subtype exists (used by rule_subtype_relations.subtype_id = 'universal')
            await db.execute(
                "INSERT OR IGNORE INTO document_subtypes (id, type_id, name) VALUES (?, ?, ?)",
                ("universal", "type_universal", "通用"),
            )
            await db.commit()

            try:
                cursor = await db.execute(
                    "SELECT DISTINCT rule_id FROM rule_subtype_relations WHERE subtype_id = 'universal'"
                )
                universal_rule_ids = [row[0] for row in await cursor.fetchall()]

                if universal_rule_ids:
                    placeholders = ", ".join(["?"] * len(universal_rule_ids))
                    await db.execute(
                        f"UPDATE rules SET is_universal = 1 WHERE id IN ({placeholders})",
                        universal_rule_ids,
                    )
                    await db.execute(
                        f"DELETE FROM rule_subtype_relations WHERE rule_id IN ({placeholders})",
                        universal_rule_ids,
                    )
                    await db.commit()
                    logging.info(f"Migration: Marked {len(universal_rule_ids)} rules as universal and cleared relations")

                await db.execute(
                    """
                    INSERT OR IGNORE INTO rule_type_relations (rule_id, type_id)
                    SELECT DISTINCT rsr.rule_id, rsr.subtype_id
                    FROM rule_subtype_relations rsr
                    INNER JOIN document_types dt ON dt.id = rsr.subtype_id
                    """
                )
                await db.execute(
                    """
                    DELETE FROM rule_subtype_relations
                    WHERE subtype_id IN (SELECT id FROM document_types)
                    """
                )
                await db.commit()
            except Exception as e:
                logging.warning(f"Migration: Failed to backfill rule scopes: {e}")


    async def store_item(self, table: str, item: Dict[str, Any]) -> None:
        columns = ", ".join(item.keys())
        placeholders = ", ".join(["?"] * len(item))
        values = list(item.values())
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                f"REPLACE INTO {table} ({columns}) VALUES ({placeholders})",
                values,
            )
            await db.commit()

    async def retrieve_item_by_id(self, table: str, item_id: str) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(f"SELECT * FROM {table} WHERE id = ?", (item_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def retrieve_items_by_values(self, table: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not filters:
            where = ""
            params: list[Any] = []
        else:
            clauses = [f"{col} = ?" for col in filters.keys()]
            where = "WHERE " + " AND ".join(clauses)
            params = list(filters.values())

        query = f"SELECT * FROM {table} {where}"
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def delete_item(self, table: str, item_id: str) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(f"DELETE FROM {table} WHERE id = ?", (item_id,))
            await db.commit()

    async def delete_items_by_values(self, table: str, filters: Dict[str, Any]) -> None:
        if not filters:
            return
        clauses = [f"{col} = ?" for col in filters.keys()]
        where = " AND ".join(clauses)
        params = list(filters.values())
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(f"DELETE FROM {table} WHERE {where}", params)
            await db.commit()

    async def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
