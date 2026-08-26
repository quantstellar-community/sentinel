# Sentinel — Data Engineering

Phần data pipeline cho project Fraud Detection kết hợp Quantum + Classical ML. Repo này thuộc nhánh **Data Engineering**, phục vụ dữ liệu cho 4 team downstream: Classical ML, Quantum 1, Quantum 2, UI/API.

Nếu bạn đến đây lần đầu, đọc [`DATA_CONTRACT.md`](DATA_CONTRACT.md) trước — file đó giải thích tại sao pipeline được thiết kế theo kiểu "một nguồn, một split, ba view" thay vì ba pipeline độc lập.

---

## Cấu trúc

```
src/
├── extraction/        extract.py        — merge CSV -> parquet
├── cleaning/          clean.py          — canonical cleaned data
├── split/             split.py          — time-based split manifest
├── feature_engineering/ build_features.py — 3 views + fit artifacts
└── eda/               eda_report.py     — EDA report tự động

dags/
└── fraud_detection_dag.py              — Airflow DAG (5 task)

dvc.yaml                                — pipeline stages
params.yaml                             — tất cả tham số tập trung ở đây
```

---

## Cài đặt

```bash
pip install -r requirements.txt
```

Dataset: [IEEE-CIS Fraud Detection](https://www.kaggle.com/c/ieee-fraud-detection) — tải về, đặt vào `data/raw/`:

```
data/raw/train_transaction.csv
data/raw/train_identity.csv
```

---

## Chạy pipeline

Cách nhanh nhất — dùng DVC (tự detect stage nào cần rebuild):

```bash
dvc repro
```

Hoặc chạy từng bước thủ công:

```bash
# 1. Extract
python src/extraction/extract.py --data-dir data/raw --output data/raw/merged.parquet

# 2. Clean
python src/cleaning/clean.py --input data/raw/merged.parquet --output data/cleaned/merged_cleaned.parquet

# 3. Split (time-based, không random)
python src/split/split.py --input data/cleaned/merged_cleaned.parquet --output data/manifests/split_manifest.parquet

# 4. Feature engineering
python src/feature_engineering/build_features.py \
    --input data/cleaned/merged_cleaned.parquet \
    --manifest data/manifests/split_manifest.parquet \
    --output-dir data/views \
    --artifacts-dir data/artifacts \
    --n-components 8 \
    --quantum-max-samples 3000 \
    --random-seed 42

# 5. EDA report
python src/eda/eda_report.py
```

Thay đổi tham số (split ratio, n_components, seed...) chỉ cần sửa `params.yaml` rồi chạy `dvc repro` — DVC tự biết rebuild stage nào.

---

## Output

| Team | Dùng file nào |
|---|---|
| Classical ML (LightGBM/XGBoost) | `data/views/classical_tree/{train,val,cal,test}.parquet` |
| OCSVM classical kernel | `data/views/classical_kernel_8f/train_normal_only.parquet` để train, `{val,cal,test}.parquet` để đánh giá |
| Quantum 1 / Quantum 2 | `data/views/quantum_8q/train_normal_only.parquet` để train, `{val,cal,test}.parquet` để đánh giá |
| Tất cả team | `data/eda/eda_summary.md` — thống kê tổng quan dataset |

`classical_kernel_8f` và `quantum_8q` dùng **chung một PCA** fit trên tập train (`data/artifacts/pca_8.joblib`). Quantum view chỉ khác ở bước scale cuối (`[0, π]` thay vì `[0, 1]`). Điều này đảm bảo benchmark classical vs quantum kernel công bằng — cùng ID, cùng split, cùng PCA.


