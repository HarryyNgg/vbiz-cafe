"""Self-check offline cho scout: parse RSS mẫu + dedupe. Chạy: python test_scout.py"""
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
    print("test_scout: OK")


if __name__ == "__main__":
    main()
