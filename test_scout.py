"""Self-check offline: parse RSS mẫu, dedupe, lịch pha bản tin sáng. Chạy: python test_scout.py"""
import json
import tempfile
from datetime import datetime
from pathlib import Path

from agency import run
from agency.scout import _key, clean_text, parse_feed

SAMPLE = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel><title>Test</title>
<item>
  <title><![CDATA[Sơn Tùng công bố concert mới]]></title>
  <link>https://example.com/a</link>
  <pubDate>Sun, 02 Nov 2026 08:00:00 +0700</pubDate>
  <description><![CDATA[<p><img src="https://example.com/thumb.jpg"/>Chi tiết <b>concert</b> tại TP.HCM.</p>]]></description>
</item>
<item>
  <title>Tin thiếu link bị bỏ qua</title>
  <pubDate>Sun, 02 Nov 2026 08:00:00 +0700</pubDate>
</item>
<item>
  <title>Hoà Minzy ra MV - VnExpress</title>
  <link>https://example.com/b</link>
  <pubDate>Sun, 02 Nov 2026 09:00:00 +0700</pubDate>
</item>
</channel></rss>"""


def main():
    items = parse_feed(SAMPLE, "Test")
    assert len(items) == 2, f"phải ra 2 item, được {len(items)}"
    assert items[0]["title"] == "Sơn Tùng công bố concert mới"
    assert "concert" in items[0]["summary"] and "<" not in items[0]["summary"]
    assert items[0]["image"] == "https://example.com/thumb.jpg"
    assert items[1]["image"] == ""
    assert items[0]["published"].startswith("2026-11-02T01:00:00"), items[0]["published"]

    gn = parse_feed(SAMPLE, "Google News")
    assert gn[1]["source"] == "VnExpress" and gn[1]["title"] == "Hoà Minzy ra MV"

    a = _key({"title": "Sơn Tùng công bố Concert mới "})
    b = _key({"title": "sơn tùng công bố concert mới"})
    assert a == b, "dedupe phải bỏ qua hoa/thường và khoảng trắng"

    assert len(clean_text("x " * 500, limit=100)) <= 100

    # bản tin sáng tự pha: chỉ sau 7:00 VN và khi hôm nay chưa pha (giờ UTC = VN - 7)
    with tempfile.TemporaryDirectory() as d:
        run.DATA = Path(d)
        utc = lambda s: datetime.fromisoformat(s + "+00:00")
        assert not run.digest_due(utc("2026-11-05T23:30")), "6:30 VN: chưa tới giờ"
        assert run.digest_due(utc("2026-11-06T00:30")), "7:30 VN, chưa có digest: phải pha"
        (Path(d) / "digest.json").write_text(json.dumps({"brewed_at": "2026-11-06T00:20:00+00:00"}))
        assert not run.digest_due(utc("2026-11-06T09:00")), "đã pha sáng nay: thôi"
        assert run.digest_due(utc("2026-11-07T01:00")), "sang ngày mới: pha lại"
    print("test_scout: OK")


if __name__ == "__main__":
    main()
