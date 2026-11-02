"""Gọi Gemini (REST, stdlib) viết bản tin Vbiz từ tin đã quét."""
import json
import os
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent

PROMPT = """Bạn là biên tập viên của "Vbiz Café", bản tin showbiz Việt Nam mỗi sáng.
Dưới đây là các tin quét từ báo trong ~36 giờ qua (JSON). Hãy viết bản tin tiếng Việt, giọng tự nhiên,
gọn, hơi dí dỏm kiểu quán cà phê nhưng không chế thêm thông tin.

LUẬT SẮT:
- Chỉ dùng thông tin có trong tin đã cho. Không bịa, không suy đoán đời tư.
- Ưu tiên showbiz VIỆT NAM (nghệ sĩ Việt, phim/nhạc/show Việt); tin sao quốc tế chỉ lấy khi thật lớn.
- Mỗi tin chính phải kèm đúng "link" của bài gốc trong dữ liệu.
- Mục nào không đủ dữ liệu thì để mảng rỗng, đừng cố lấp.

Trả về DUY NHẤT một JSON object:
{
  "tieu_diem": "3-5 câu: hôm nay Vbiz có gì đáng chú ý nhất, trả lời thẳng",
  "tin_chinh": [{"tieu_de": "...", "vi_sao": "1-2 câu vì sao đáng đọc", "link": "...", "nguon": "tên báo"}],  // 5-8 tin
  "dang_hot": [{"ten": "tên người/từ khóa", "vi_sao": "ngắn gọn vì sao được nhắc"}],  // 3-6 mục
  "sap_dien_ra": [{"khi_nao": "vd: 15/11 hoặc 'cuối tháng 11'", "su_kien": "...", "link": "..."}]  // 0-6 mục
}

DỮ LIỆU:
"""

REQUIRED = {"tieu_diem": str, "tin_chinh": list, "dang_hot": list, "sap_dien_ra": list}


def _env():
    """Đọc agency/.env (KEY=VALUE từng dòng) vào os.environ nếu chưa có."""
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def _call(prompt):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise SystemExit("Thiếu GEMINI_API_KEY (agency/.env hoặc Actions secret).")
    model = os.environ.get("AGENCY_MODEL", "gemini-flash-latest")
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"response_mime_type": "application/json", "temperature": 0.4},
    }).encode()
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=body,
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        out = json.load(r)
    return out["candidates"][0]["content"]["parts"][0]["text"]


def _valid(d):
    return isinstance(d, dict) and all(isinstance(d.get(k), t) for k, t in REQUIRED.items())


def brew(items, max_items=80):
    """items -> digest dict. Model free hay trả JSON lệch, nên thử lại 1 lần."""
    _env()
    slim = [
        {k: it[k] for k in ("title", "link", "source", "published", "summary")}
        for it in items[:max_items]
    ]
    prompt = PROMPT + json.dumps(slim, ensure_ascii=False)
    for attempt in (1, 2):
        try:
            digest = json.loads(_call(prompt))
            if _valid(digest):
                # giữ lại chỉ link có thật trong dữ liệu (chống bịa link)
                links = {it["link"] for it in slim}
                digest["tin_chinh"] = [t for t in digest["tin_chinh"] if t.get("link") in links][:8]
                return digest
            print(f"[brief] lần {attempt}: JSON sai cấu trúc, thử lại")
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[brief] lần {attempt}: {e}")
        except urllib.error.HTTPError as e:
            print(f"[brief] lần {attempt}: HTTP {e.code}: {e.read()[:300]!r}")
    raise SystemExit("Gemini không trả được JSON hợp lệ sau 2 lần.")
