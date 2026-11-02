"""Quét tin Vbiz từ các RSS feed public — stdlib only."""
import hashlib
import html
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

FEEDS = [
    ("VnExpress", "https://vnexpress.net/rss/giai-tri.rss"),
    ("Thanh Niên", "https://thanhnien.vn/rss/giai-tri.rss"),
    ("Tuổi Trẻ", "https://tuoitre.vn/rss/giai-tri.rss"),
    ("Kenh14", "https://kenh14.vn/star.rss"),
    ("Znews", "https://znews.vn/rss/giai-tri.rss"),
    ("Google News", "https://news.google.com/rss/search?q=vbiz&hl=vi&gl=VN&ceid=VN:vi"),
]

TAG_RE = re.compile(r"<[^>]+>")
IMG_RE = re.compile(r"""<img[^>]+src=["']([^"']+)["']""", re.I)


def _clean(text):
    if not text:
        return ""
    return html.unescape(TAG_RE.sub(" ", text)).split()  # list of words


def clean_text(text, limit=300):
    words = _clean(text)
    out = " ".join(words)
    return out[:limit].rsplit(" ", 1)[0] if len(out) > limit else out


def parse_feed(xml_text, source):
    """Parse một RSS 2.0 feed thành list item dict."""
    items = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items
    for it in root.iter("item"):
        title = clean_text((it.findtext("title") or ""), 200)
        link = (it.findtext("link") or "").strip()
        if not title or not link:
            continue
        pub = it.findtext("pubDate")
        try:
            dt = parsedate_to_datetime(pub).astimezone(timezone.utc)
        except Exception:
            dt = datetime.now(timezone.utc)
        # vài báo ghi giờ VN nhưng gắn nhãn GMT -> tin "đến từ tương lai"; kẹp lại
        dt = min(dt, datetime.now(timezone.utc))
        # Google News ghép " - Tên báo" vào title
        src = source
        if source == "Google News" and " - " in title:
            title, src = title.rsplit(" - ", 1)
        desc = it.findtext("description") or ""
        m = IMG_RE.search(desc)
        image = html.unescape(m.group(1)) if m else ""
        if not image:  # enclosure / media:content cũng hay chứa ảnh
            for child in it:
                if child.tag.endswith("enclosure") or child.tag.endswith("content"):
                    u = child.get("url") or ""
                    if u.startswith("http"):
                        image = u
                        break
        items.append({
            "title": title.strip(),
            "link": link,
            "source": src.strip(),
            "published": dt.isoformat(),
            "summary": clean_text(desc),
            "image": image,
        })
    return items


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (vbiz-cafe)"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", errors="replace")


def _key(item):
    # dedupe theo title đã chuẩn hoá (cùng tin trên nhiều báo vẫn giữ, chỉ chặn trùng hệt)
    base = item["title"].lower().strip()
    return hashlib.sha1(base.encode()).hexdigest()[:16]


def load_seen():
    p = DATA / "seen.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def save_seen(seen):
    DATA.mkdir(parents=True, exist_ok=True)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    seen = {k: v for k, v in seen.items() if v >= cutoff}
    (DATA / "seen.json").write_text(json.dumps(seen, ensure_ascii=False, indent=1), encoding="utf-8")


def scout(max_age_hours=36):
    """Quét mọi feed, trả về (tin mới chưa từng thấy, toàn bộ tin còn tươi)."""
    seen = load_seen()
    now = datetime.now(timezone.utc)
    fresh, new = [], []
    for source, url in FEEDS:
        try:
            items = parse_feed(fetch(url), source)
        except Exception as e:
            print(f"  [scout] {source} lỗi: {e}")
            continue
        for it in items:
            if (now - datetime.fromisoformat(it["published"])) > timedelta(hours=max_age_hours):
                continue
            fresh.append(it)
            k = _key(it)
            if k not in seen:
                seen[k] = it["published"]
                new.append(it)
    fresh.sort(key=lambda i: i["published"], reverse=True)
    new.sort(key=lambda i: i["published"], reverse=True)
    save_seen(seen)
    return new, fresh


if __name__ == "__main__":
    new, fresh = scout()
    print(f"{len(fresh)} tin còn tươi, {len(new)} tin mới chưa thấy\n")
    for it in fresh[:20]:
        print(f"- [{it['source']}] {it['title']}  ({it['published']})")
