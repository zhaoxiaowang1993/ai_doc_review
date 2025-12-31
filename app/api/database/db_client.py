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
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT
);
"""

CREATE_DOCUMENT_RULES_TABLE = """
CREATE TABLE IF NOT EXISTS document_rules (
    doc_id TEXT NOT NULL,
    rule_id TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (doc_id, rule_id)
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
            await db.execute(CREATE_DOCUMENT_RULES_TABLE)
            await db.commit()
            
            # Migration: Add risk_level column to existing issues table if not exists
            try:
                await db.execute("ALTER TABLE issues ADD COLUMN risk_level TEXT")
                await db.commit()
                logging.info("Migration: Added risk_level column to issues table")
            except Exception:
                # Column already exists, ignore
                pass

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
