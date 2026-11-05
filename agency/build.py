"""Render docs/index.html + docs/headlines.json từ data/."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DOCS = ROOT / "docs"
TEMPLATE = Path(__file__).resolve().parent / "template.html"


def _load(name):
    p = DATA / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def build():
    DOCS.mkdir(parents=True, exist_ok=True)
    headlines = _load("headlines.json") or []
    from .jev import VN_MIN
    state = {"digest": _load("digest.json"), "headlines": headlines, "vn_min": VN_MIN}
    html = TEMPLATE.read_text(encoding="utf-8").replace(
        "/*__STATE__*/null", json.dumps(state, ensure_ascii=False)
    )
    (DOCS / "index.html").write_text(html, encoding="utf-8")
    (DOCS / "headlines.json").write_text(
        json.dumps(headlines, ensure_ascii=False), encoding="utf-8"
    )
    print(f"[build] docs/index.html ({len(headlines)} headlines, digest: {'có' if state['digest'] else 'chưa'})")


if __name__ == "__main__":
    build()
