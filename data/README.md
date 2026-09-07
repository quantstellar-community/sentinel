# Data

Thư mục này chứa dữ liệu **local**, không được commit lên git (`/data/` trong `.gitignore`). Mỗi thành viên cần tự tải dữ liệu về máy.

## Cấu trúc

```text
data/
├── raw/          # Dữ liệu đầu vào chưa xử lý (creditcard.csv)
├── processed/    # Sau preprocessing
├── features/     # Derived behavioral features
└── predictions/  # Model outputs / artifacts
```

## Dataset hiện tại: European credit-card fraud

Nguồn: Kaggle — [`mlg-ulb/creditcardfraud`](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud)

Dữ liệu: 284,807 giao dịch, 31 cột (`Time`, `V1..V28` PCA-anonymized, `Amount`, `Class`). Phục vụ controlled benchmark cho anomaly detection (chi tiết: `SENTINEL_THESIS.md` §5).

## Tải dữ liệu

### 1. Chuẩn bị Kaggle credentials

Kaggle yêu cầu API key dạng file `kaggle.json`:

1. Đăng nhập [Kaggle](https://www.kaggle.com), vào **Settings → API**.
2. Chọn **Create New Token** → tải về file `kaggle.json`.
3. Đặt file tại `~/.kaggle/kaggle.json`:

   - **Windows:** `C:\Users\<username>\.kaggle\kaggle.json`
   - **Linux/macOS:** `~/.kaggle/kaggle.json`

**Lưu ý:** `kaggle.json` chứa API key — tuyệt đối **không commit** vào repo (RULE-57).

### 2. Chạy script tải dữ liệu

```powershell
uv sync          # cài dependency (kagglehub)
uv run python scripts/fetch_data.py
```

Kết quả: `data/raw/creditcard.csv`

- File đã tồn tại → script bỏ qua (không tải lại).
- Muốn tải lại từ đầu: `uv run python scripts/fetch_data.py --force`.