# ADR-012 — Kagglehub Data Fetch

## Trạng thái

Accepted

## Bối cảnh

`/data/` bị gitignore nên data không lên remote; đồng đội clone repo về cần tự chuẩn bị dataset. Dataset European credit-card nằm trên Kaggle (`mlg-ulb/creditcardfraud`), yêu cầu API credentials.

## Quyết định

Dùng **`kagglehub`** (Python package) trong `scripts/fetch_data.py` để tải `creditcard.csv` về `data/raw/`. Credentials (`kaggle.json`) đặt ở `~/.kaggle/`, **không commit** (RULE-57). Hướng dẫn chi tiết trong `data/README.md`. Script skip nếu file đã tồn tại, có flag `--force` để tải lại.

## Hệ quả

- **Tích cực:** Đồng đội tự tải data được (`uv run python scripts/fetch_data.py`); data thật vẫn không lên git.
- **Trung tính:** `kaggle.json` là yêu cầu bắt buộc cho người cần tải data; `kagglehub` được thêm vào dependencies.
- **Tiêu cực:** Kaggle account cần thiết; nếu không có credentials thì phải tự lấy data từ nguồn khác.