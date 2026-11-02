"""Vbiz Café CLI.

python -m agency.run              # scout -> Gemini digest -> build (bản tin đầy đủ)
python -m agency.run --headlines  # scout -> build (chỉ ticker, không gọi AI)
python -m agency.run --rebuild    # build lại từ data/ sẵn có
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from . import build as build_mod
from . import scout as scout_mod

DATA = Path(__file__).resolve().parent.parent / "data"


def save_headlines(fresh):
    """Mỗi nguồn tối đa 8 tin, để nguồn ít bài không bị các báo đăng dồn dập đè mất."""
    DATA.mkdir(parents=True, exist_ok=True)
    by_source = {}
    for it in fresh:  # fresh đã sort mới nhất trước
        by_source.setdefault(it["source"], []).append(it)
    picked = [it for items in by_source.values() for it in items[:8]]
    picked.sort(key=lambda i: i["published"], reverse=True)
    (DATA / "headlines.json").write_text(
        json.dumps(picked, ensure_ascii=False, indent=1), encoding="utf-8"
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headlines", action="store_true", help="chỉ cập nhật ticker, không gọi AI")
    ap.add_argument("--rebuild", action="store_true", help="render lại từ data/ sẵn có")
    args = ap.parse_args()

    if args.rebuild:
        build_mod.build()
        return

    new, fresh = scout_mod.scout()
    print(f"[scout] {len(fresh)} tin tươi, {len(new)} tin mới")
    save_headlines(fresh)

    if not args.headlines:
        from . import brief as brief_mod
        digest = brief_mod.brew(fresh)
        digest["generated_at"] = datetime.now(timezone.utc).isoformat()
        (DATA / "digest.json").write_text(
            json.dumps(digest, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        print(f"[brief] digest: {len(digest.get('tin_chinh', []))} tin chính")

    build_mod.build()


if __name__ == "__main__":
    main()
