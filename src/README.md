# Fraud Detection Data Pipeline — v2 (canonical + shared views)

Đọc `DATA_CONTRACT.md` trước — đặc biệt mục "Thay đổi quan trọng so với v1" để hiểu vì sao kiến trúc đổi từ "3 output độc lập" sang "1 nguồn + 1 split + 3 view chia sẻ".

## Cài đặt

```bash
pip install -r requirements.txt
```

## Chuẩn bị dữ liệu

Tải IEEE-CIS Fraud Detection từ Kaggle, đặt vào `data/raw/`:
```
data/raw/train_transaction.csv
data/raw/train_identity.csv
```

## Chạy pipeline (thứ tự bắt buộc — có thêm bước `split` so với trước)

```bash
# 1. Extract
python src/extraction/extract.py \
    --data-dir data/raw --output data/raw/merged.parquet

# 2. Clean -> tạo canonical data DUY NHẤT
python src/cleaning/clean.py \
    --input data/raw/merged.parquet \
    --output data/cleaned/merged_cleaned.parquet

# 3. Split -> tạo split_manifest DUY NHẤT (dùng chung mọi view)
python src/split/split.py \
    --input data/cleaned/merged_cleaned.parquet \
    --output data/manifests/split_manifest.parquet

# 4. Feature engineering -> tạo 3 view, join theo split_manifest,
#    fit imputer/PCA/scaler CHỈ trên train
python src/feature_engineering/build_features.py \
    --input data/cleaned/merged_cleaned.parquet \
    --manifest data/manifests/split_manifest.parquet \
    --output-dir data/views \
    --artifacts-dir data/artifacts \
    --n-components 8 \
    --quantum-max-samples 3000
```

## Output cho từng team

| Team | File cần dùng |
|---|---|
| Classical ML (LightGBM/XGBoost) | `data/views/classical_tree/{train,val,cal,test}.parquet` |
| OCSVM classical kernel | `data/views/classical_kernel_8f/train_normal_only.parquet` (train OCSVM) + `{val,cal,test}.parquet` (đánh giá) |
| Quantum 1 / Quantum 2 | `data/views/quantum_8q/train_normal_only.parquet` (train) + `{val,cal,test}.parquet` (đánh giá) |

`classical_kernel_8f` và `quantum_8q` dùng **chung một PCA fit trên train** (`data/artifacts/pca_8.joblib`) — đảm bảo benchmark classical vs quantum kernel công bằng, chỉ khác nhau ở bước scale cuối.

Mỗi view kernel/quantum đều có `scaling_metadata.json` — nêu rõ range scale, số component, và xác nhận `"fitted_on": "train split only"` để downstream biết không có leakage.

## Việc tiếp theo (Pha 2, chưa làm trong bản này)

- Validation chi tiết (Great Expectations)
- Sửa `add_frequency_features` thành rolling/expanding count theo thời gian (hiện tại đang tính trên toàn bộ data, rò rỉ nhẹ)
- Feature engineering nâng cao (UID giả lập, aggregation theo thời gian sâu hơn)
- Đóng gói thành Airflow DAG + `dvc.yaml` (đã có sẵn 4 stage rõ ràng: extract → clean → split → build_features)
