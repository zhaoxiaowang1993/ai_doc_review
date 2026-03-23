"""
脚本目标：
- 在测试环境快速重置业务数据，保留规则体系相关基础表。

执行行为：
- 读取 SQLite 中全部用户表，按白名单保留 document_types、document_subtypes、rules 及规则关系表。
- 清空其余表数据（DELETE），并打印每张表删除行数统计。
- 同步清理本地数据目录中的 documents 与 mineru 缓存目录。

使用方式：
- 预览影响范围：python3 app/api/scripts/clear_tables_except_rules.py --dry-run
- 确认执行清理：python3 app/api/scripts/clear_tables_except_rules.py --yes
- 指定数据库文件：python3 app/api/scripts/clear_tables_except_rules.py --yes --db-path /path/to/app.db

注意事项：
- 该脚本面向测试环境，不建议直接用于生产环境。
- --dry-run 只做展示，不会删除表数据和本地目录。
"""

import argparse
import os
import shutil
import sqlite3
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
APP_DIR = API_DIR.parent
ROOT_DIR = APP_DIR.parent
for p in (API_DIR, ROOT_DIR, APP_DIR):
    p_str = str(p)
    if p_str in sys.path:
        sys.path.remove(p_str)
    sys.path.insert(0, p_str)

KEEP_TABLES = {
    "document_subtypes",
    "document_types",
    "rule_subtype_relations",
    "rule_type_relations",
    "rules",
    "schema_migrations",
}


def _resolve_from_api_dir(path_like: str) -> Path:
    p = Path(path_like)
    if p.is_absolute():
        return p
    return (API_DIR / p).resolve()


def _get_user_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


def _clear_tables(conn: sqlite3.Connection, target_tables: list[str]) -> dict[str, int]:
    deleted: dict[str, int] = {}
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("BEGIN")
    try:
        for table in target_tables:
            count = conn.execute(f"SELECT COUNT(1) FROM {table}").fetchone()[0]
            conn.execute(f"DELETE FROM {table}")
            deleted[table] = count
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
    return deleted


def _clear_local_artifacts(db_path: Path) -> dict[str, str]:
    data_dir = db_path.parent
    targets = [
        (data_dir / "documents").resolve(),
        (data_dir / "mineru").resolve(),
    ]
    result: dict[str, str] = {}
    for target in targets:
        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
            result[str(target)] = "deleted"
        else:
            result[str(target)] = "not_found"
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="清空除规则相关表以外的数据")
    parser.add_argument("--yes", action="store_true", help="跳过确认，直接执行")
    parser.add_argument("--dry-run", action="store_true", help="仅展示将要清空的表，不执行删除")
    parser.add_argument(
        "--db-path",
        default=os.getenv("SQLITE_PATH", "./app/data/app.db"),
        help="SQLite 文件路径",
    )
    args = parser.parse_args()

    db_path = _resolve_from_api_dir(args.db_path)
    if not db_path.exists():
        print(f"数据库文件不存在：{db_path}")
        sys.exit(1)

    with sqlite3.connect(db_path) as conn:
        all_tables = _get_user_tables(conn)
        target_tables = [t for t in all_tables if t not in KEEP_TABLES]

        print(f"数据库文件：{db_path}")
        print("保留表：")
        for t in sorted(KEEP_TABLES):
            print(f"- {t}")
        print("将清空数据的表：")
        if target_tables:
            for t in target_tables:
                print(f"- {t}")
        else:
            print("- 无")

        if args.dry_run:
            print("dry-run 完成，未执行删除。")
            return

        if not args.yes:
            value = input("输入 yes 继续：").strip().lower()
            if value != "yes":
                print("已取消。")
                return

        deleted = _clear_tables(conn, target_tables)
        artifact_status = _clear_local_artifacts(db_path)

    total_rows = sum(deleted.values())
    print("清空完成。")
    for table, rows in deleted.items():
        print(f"- {table}: 删除 {rows} 行")
    print(f"总计删除：{total_rows} 行")
    print("本地目录清理：")
    for target, status in artifact_status.items():
        print(f"- {target}: {status}")


if __name__ == "__main__":
    main()
