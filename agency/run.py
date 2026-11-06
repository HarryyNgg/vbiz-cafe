"""Vbiz Café CLI.

python -m agency.run              # scout -> Gemini digest -> build (bản tin đầy đủ)
python -m agency.run --headlines  # scout -> Jev chấm tin -> tiêu điểm nhanh -> build (mỗi 30 phút)
python -m agency.run --auto       # như --headlines, nhưng pha digest nếu đã qua 7:00 VN mà hôm nay chưa có
python -m agency.run --rebuild    # build lại từ data/ sẵn có
"""
import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import build as build_mod
from . import jev as jev_mod
from . import scout as scout_mod

DATA = Path(__file__).resolve().parent.parent / "data"


def save_headlines(fresh):
    """Mỗi nguồn tối đa 8 tin, để nguồn ít bài không bị các báo đăng dồn dập đè mất.

    Jev chấm từng tin (showbiz VN? nóng cỡ nào?); trả về các tin đã chọn.
    """
    DATA.mkdir(parents=True, exist_ok=True)
    by_source = {}
    for it in fresh:  # fresh đã sort mới nhất trước
        by_source.setdefault(it["source"], []).append(it)
    picked = [dict(it) for items in by_source.values() for it in items[:8]]
    picked.sort(key=lambda i: i["published"], reverse=True)

    p = DATA / "headlines.json"
    previous = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
    try:
        jev_mod.judge(picked, previous)
    except Exception as e:  # Jev chỉ là lớp làm giàu: lỗi gì thì danh sách vẫn phải lên
        print(f"[jev] lỗi, bỏ qua: {e}")
    p.write_text(json.dumps(picked, ensure_ascii=False, indent=1), encoding="utf-8")
    return picked


VN_TZ = timezone(timedelta(hours=7))
DIGEST_HOUR = 7


def digest_due(now=None):
    """Đã qua 7:00 VN mà bản tin đầy đủ hôm nay chưa pha? (pulse 30 phút không tính)."""
    now = (now or datetime.now(timezone.utc)).astimezone(VN_TZ)
    if now.hour < DIGEST_HOUR:
        return False
    p = DATA / "digest.json"
    brewed = json.loads(p.read_text(encoding="utf-8")).get("brewed_at") if p.exists() else None
    return not brewed or datetime.fromisoformat(brewed).astimezone(VN_TZ).date() < now.date()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headlines", action="store_true", help="chỉ cập nhật ticker + tiêu điểm nhanh")
    ap.add_argument("--auto", action="store_true", help="như --headlines, hoặc pha digest nếu sáng nay chưa có")
    ap.add_argument("--rebuild", action="store_true", help="render lại từ data/ sẵn có")
    args = ap.parse_args()
    if args.auto:
        args.headlines = not digest_due()
        print(f"[auto] {'ticker' if args.headlines else 'pha bản tin sáng'}")

    if args.rebuild:
        build_mod.build()
        return

    new, fresh = scout_mod.scout()
    print(f"[scout] {len(fresh)} tin tươi, {len(new)} tin mới")
    picked = save_headlines(fresh)

    from . import brief as brief_mod
    if not args.headlines:
        try:
            digest = brief_mod.brew(fresh)
            digest["generated_at"] = digest["brewed_at"] = datetime.now(timezone.utc).isoformat()
            (DATA / "digest.json").write_text(
                json.dumps(digest, ensure_ascii=False, indent=1), encoding="utf-8"
            )
            print(f"[brief] digest: {len(digest.get('tin_chinh', []))} tin chính")
        except (SystemExit, Exception) as e:
            if not args.auto:  # bấm tay: báo lỗi thật
                raise
            print(f"[brief] lỗi, lượt này chỉ cập nhật ticker, lượt sau thử lại: {e}")
            args.headlines = True

    if args.headlines:
        # tiêu điểm "thời gian thực": tóm tắt lại từ tin VN mới nhất, các mục khác giữ bản tin sáng
        vn_news = [i for i in picked if i.get("vn", 1) >= jev_mod.VN_MIN]
        try:
            summary = brief_mod.pulse(vn_news or fresh)
            if summary:
                p = DATA / "digest.json"
                digest = (json.loads(p.read_text(encoding="utf-8")) if p.exists()
                          else {"tin_chinh": [], "dang_hot": [], "sap_dien_ra": []})
                digest["tieu_diem"] = summary
                digest["generated_at"] = datetime.now(timezone.utc).isoformat()
                p.write_text(json.dumps(digest, ensure_ascii=False, indent=1), encoding="utf-8")
                print("[pulse] tiêu điểm đã cập nhật")
        except SystemExit as e:  # thiếu key: ticker vẫn phải chạy
            print(f"[pulse] bỏ qua: {e}")
        except Exception as e:
            print(f"[pulse] lỗi, giữ tiêu điểm cũ: {e}")

    build_mod.build()


if __name__ == "__main__":
    main()
