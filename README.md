# ☕ Vbiz Café

Quán cà phê nhỏ tự pha tin Vbiz (showbiz Việt Nam): ticker tin mới mỗi giờ,
bản tin AI phân tích mỗi sáng 7:00 (giờ VN), chạy 24/7 miễn phí trên GitHub Actions.
Lấy cảm hứng từ [The Insight Café](https://github.com/melinenguyen/insight-cafe).

## Chạy trên máy

```
# chỉ ticker, không tốn gì
python -m agency.run --headlines

# bản tin đầy đủ (cần GEMINI_API_KEY trong agency/.env, free tại aistudio.google.com/apikey)
python -m agency.run

# render lại từ dữ liệu sẵn có
python -m agency.run --rebuild
```

Mở `docs/index.html` để xem. Không có dependency nào ngoài Python 3.10+ (stdlib).

## Chạy 24/7 trên GitHub

1. Tạo repo **public** (Actions free không giới hạn), push toàn bộ thư mục này.
2. Settings → Secrets and variables → Actions → thêm secret `GEMINI_API_KEY`.
3. Settings → Pages → Deploy from a branch → `main` / `docs`.
4. Actions → vbiz-cafe → Run workflow (lượt pha đầu tiên).

Sau đó: mỗi giờ ticker tự cập nhật, 7:00 sáng VN có bản tin mới.
Trang web tự fetch lại ticker mỗi 5 phút khi đang mở.

## Cấu trúc

- `agency/scout.py` — quét 9 nguồn RSS public (VnExpress, Thanh Niên, Tuổi Trẻ, Kenh14, Znews, Dân Trí, Vietnamnet, Tiền Phong, Google News), dedupe bằng `data/seen.json`
- `agency/brief.py` — Gemini viết digest JSON (chỉ dùng tin đã quét, link phải có thật)
- `agency/build.py` — render `docs/` (trang tĩnh + `headlines.json`)
- `.github/workflows/vbiz.yml` — lịch chạy

Luật: chỉ đọc tin public, không đăng/bình luận/nhắn tin ở đâu cả, không bịa thông tin.

## Self-check

```
python test_scout.py
```
