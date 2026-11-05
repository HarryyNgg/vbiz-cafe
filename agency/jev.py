"""Jev (TypeSafe) chấm từng tin: có phải showbiz VN không (Noul) và nóng cỡ nào (Score 0-4).

Chỉ lưu xác suất/điểm thô vào headline; ngưỡng "VN hay quốc tế" là chính sách ở trang web.
Chạy thử: python -m agency.jev  (chấm headlines hiện có, in bảng)
"""
import json
import os
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT.parent / "data"
# Mỗi tin một request: gộp 20 tin vào một state làm Jev lẫn tin này với tin kia
# (thử 05/11: 'Chị chị em em 3' gộp ra 0.21, hỏi riêng ra 0.97).
WORKERS = 8
VN_MIN = 0.75  # dưới ngưỡng này về tab Quốc tế; tin lưng chừng (phim Trung, người Việt thi quốc tế) rơi vào đây

HOT_LEVELS = [
    "Tin vụn hoặc không liên quan showbiz: quảng cáo, mẹo vặt, tin địa phương lặt vặt.",
    "Tin nhỏ về nghệ sĩ ít tên tuổi hoặc hoạt động thường ngày, ít người quan tâm.",
    "Tin đáng chú ý: nghệ sĩ có tên tuổi ra sản phẩm, sự kiện, phát ngôn được nhắc tới.",
    "Tin nóng: nghệ sĩ nổi tiếng, phim/show đang hot, tranh cãi hoặc chuyện đời tư được bàn tán rộng.",
    "Tin cực nóng: sự kiện lớn của cả làng giải trí (scandal lớn, cưới/ly hôn/qua đời của sao hạng A, kỷ lục phòng vé).",
]


def _key():
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
    return (os.environ.get("TYPESAFE_API_KEY") or "").strip().lstrip("﻿")


QUESTIONS = {
    "hot": {
        "type": "score",
        "instructions": "Với độc giả Việt Nam theo dõi showbiz, tin này (tiêu đề `title`, tóm tắt `summary`) nóng đến mức nào?",
        "criteria": HOT_LEVELS,
    },
    "vn": {
        "type": "noul",
        "instructions": (
            "Tin này (tiêu đề `title`, tóm tắt `summary`) có phải về showbiz Việt Nam "
            "(nghệ sĩ, phim, nhạc, show, sự kiện giải trí của Việt Nam) không?"
        ),
        "criteria": {
            "true": "Nhân vật hoặc sự kiện chính là của làng giải trí Việt Nam.",
            "false": (
                "Chủ yếu về sao/phim/sự kiện nước ngoài, hoặc không phải tin giải trí. "
                "Lưu ý tiếng lóng: 'Cbiz' là showbiz Trung Quốc, 'Kbiz' là Hàn Quốc, 'Hollywood' là Mỹ."
            ),
        },
    },
}


def _ask(key, it):
    body = json.dumps({
        "model": os.environ.get("TYPESAFE_MODEL", "jev-latest"),
        "state": {"title": it["title"], "summary": it.get("summary", "")},
        "questions": QUESTIONS,
    }).encode()
    req = urllib.request.Request(
        "https://api.typesafe.ai/v1/systemone",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            a = json.load(r)["answers"]
        return round(a["vn"]["noul"], 3), round(a["hot"]["score"], 2)
    except (urllib.error.URLError, KeyError, ValueError) as e:
        print(f"[jev] bỏ qua 1 tin: {e}")
        return None


def judge(items, previous=()):
    """Gắn `vn` (0-1) và `hot` (0-4) vào từng tin, tại chỗ.

    Tin đã chấm ở lượt trước (cùng link) dùng lại kết quả cũ: rẻ hơn, và tin không nhảy tab giữa các lượt.
    Không có key thì bỏ qua; lỗi giữa chừng thì tin chưa chấm cứ để trống (trang coi là tin VN).
    """
    key = _key()
    if not key:
        print("[jev] thiếu TYPESAFE_API_KEY, bỏ qua")
        return
    old = {p["link"]: p for p in previous if "vn" in p}
    todo = []
    for it in items:
        if it["link"] in old:
            it["vn"], it["hot"] = old[it["link"]]["vn"], old[it["link"]]["hot"]
        else:
            todo.append(it)
    with ThreadPoolExecutor(WORKERS) as pool:
        results = list(pool.map(lambda it: _ask(key, it), todo))
    for it, res in zip(todo, results):
        if res:
            it["vn"], it["hot"] = res
    ok = sum(1 for r in results if r)
    print(f"[jev] chấm mới {ok}/{len(todo)} tin, dùng lại {len(items) - len(todo)} tin")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    items = json.loads((DATA / "headlines.json").read_text(encoding="utf-8"))
    for it in items:  # chấm lại toàn bộ cho bảng thử
        it.pop("vn", None)
        it.pop("hot", None)
    judge(items)
    for it in sorted(items, key=lambda i: i.get("hot", -1), reverse=True):
        print(f"{it.get('hot', -1):4.1f} {it.get('vn', -1):5.2f}  {it['source'][:11]:<11}  {it['title'][:80]}")
