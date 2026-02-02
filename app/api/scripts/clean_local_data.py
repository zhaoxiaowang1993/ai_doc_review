import argparse
import shutil
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

from config.config import settings


def _resolve_from_api_dir(path_like: str) -> Path:
    p = Path(path_like)
    if p.is_absolute():
        return p
    return (API_DIR / p).resolve()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args()

    targets = [
        _resolve_from_api_dir(settings.sqlite_path),
        _resolve_from_api_dir(settings.local_docs_dir),
        _resolve_from_api_dir(settings.mineru_cache_dir),
    ]

    print("将清理以下本地数据路径：")
    for t in targets:
        print(f"- {t}")

    if not args.yes:
        value = input("输入 yes 继续：").strip().lower()
        if value != "yes":
            print("已取消。")
            return

    for t in targets:
        if t.is_file():
            t.unlink(missing_ok=True)
        elif t.is_dir():
            shutil.rmtree(t, ignore_errors=True)

    print("清理完成。")


if __name__ == "__main__":
    main()
