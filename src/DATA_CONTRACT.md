# DATA CONTRACT — Fraud Detection (Quantum + Classical ML)

> **Chủ sở hữu:** Data Engineering (1 người)
> **Version:** v3 — fix frequency leakage, thêm DVC pipeline + params.yaml + seed management
> **Cập nhật lần cuối:** 2026-08-27
> **Mục đích:** Nguồn sự thật duy nhất về format, schema, và ý nghĩa của dữ liệu mà Data Engineering cung cấp cho 4 team downstream: Quantum 1, Quantum 2, Classical ML, UI/API.

---

## ⚠️ Thay đổi quan trọng so với v1

Bản v1 định nghĩa "3 output độc lập" dễ khiến hiểu nhầm thành 3 pipeline/3 cách split riêng biệt — điều này phá vỡ tính công bằng khi benchmark classical kernel vs quantum kernel. **v2 sửa lại theo kiến trúc:**

```
One source of truth (canonical data)
        ↓
One fixed split policy (split_manifest — cố định, dùng chung)
        ↓
Shared IDs + labels
        ↓
Branch-specific preprocessing (3 views, KHÔNG phải 3 dataset độc lập)
```

**Nguyên tắc bất di bất dịch:**
1. Chỉ có **một** bước cleaning tạo ra canonical data — mọi nhánh đọc từ đây.
2. Chỉ có **một** file `split_manifest.parquet` quyết định dòng nào thuộc train/val/cal/test — không nhánh nào được tự split riêng.
3. `classical_kernel` và `quantum` dùng **chung một PCA fit trên train** — quantum view là phép biến đổi *tiếp theo* từ kernel view (chỉ khác bước scale cuối), không phải pipeline tách biệt.
4. Mọi imputer/scaler/PCA **chỉ được fit trên tập `train`**, sau đó transform cho val/cal/test — tuyệt đối không fit lại trên test (leakage).
5. OCSVM train trên `train_normal_only` (chỉ label 0, chỉ trong tập train); val/cal/test giữ nguyên cả normal + fraud để đánh giá.

---

## 1. Nguồn dữ liệu gốc

| Item | Giá trị |
|---|---|
| Dataset | IEEE-CIS Fraud Detection |
| Files gốc | `train_transaction.csv`, `train_identity.csv`, `test_transaction.csv`, `test_identity.csv` |
| Key join | `TransactionID` (left join transaction ← identity) |
| Label | `isFraud` (0/1, chỉ có trong train) |
| Đặc điểm | ~590k dòng, mất cân bằng nặng (~3.5% fraud), ~24% giao dịch có identity |

---

## 2. Pipeline stages (thứ tự chạy — ĐÃ THÊM stage `split`)

```
raw (csv) → extract → validate → clean (canonical) → split (manifest) → feature engineering → 3 views
```

| Stage | Input | Output | Script |
|---|---|---|---|
| Extract | `data/raw/*.csv` | `data/raw/merged.parquet` | `src/extraction/extract.py` |
| Validate | `data/raw/merged.parquet` | `data/validated/*.parquet` + report | `src/validation/validate.py` (Pha 2) |
| **Clean (canonical)** | `data/validated/*.parquet` | `data/cleaned/merged_cleaned.parquet` | `src/cleaning/clean.py` |
| **Split (manifest)** | `data/cleaned/merged_cleaned.parquet` | `data/manifests/split_manifest.parquet` | `src/split/split.py` |
| Feature Engineering | canonical + manifest | 3 views (xem mục 3) | `src/feature_engineering/build_features.py` |

Versioning: mọi output track bằng **DVC**.

---

## 3. `split_manifest.parquet` — nguồn sự thật về split

| Cột | Ý nghĩa |
|---|---|
| `TransactionID` | khóa chính |
| `split` | một trong `train` / `val` / `cal` / `test` |
| `label` | `isFraud` gốc, đi kèm để tiện kiểm tra tỷ lệ fraud từng phần |
| `TransactionDT` | giữ lại để audit |

**Split theo thời gian** (sort theo `TransactionDT`, KHÔNG random, KHÔNG shuffle) để tránh leakage. Tỷ lệ mặc định: `train=60% / val=15% / cal=10% / test=15%` (xem `params.yaml → split.*`).

- `train` — fit imputer/scaler/PCA, train model
- `val` — tune hyperparameter
- `cal` — calibrate threshold/probability (quan trọng với fraud detection vì cần chọn ngưỡng theo precision/recall mong muốn)
- `test` — chỉ đánh giá cuối cùng, không đụng vào trong lúc phát triển

**Bất kỳ nhánh nào cần join theo ID này, không tự tạo split khác.**

---

## 4. Ba "views" — derive từ CÙNG canonical data + CÙNG split, KHÔNG phải 3 dataset độc lập

### 4.1 View `classical_tree` — dành cho **Classical ML** (LightGBM/XGBoost)

- **Path:** `data/views/classical_tree/{train,val,cal,test}.parquet`
- Giữ **full feature set**, giữ NaN nguyên bản (tree model tự xử lý được), categorical dtype `category`
- Không PCA, không scale — tree model không cần và không nên ép giảm chiều
- File đi kèm: `categorical_cols.txt`

### 4.2 View `classical_kernel_{n}f` — dành cho **OCSVM classical kernel** (benchmark baseline)

- **Path:** `data/views/classical_kernel_{n}f/{train,val,cal,test,train_normal_only}.parquet`
- `{n}` = số component sau PCA (mặc định 8, PHẢI khớp với số qubit bên quantum dùng)
- Impute (median, fit trên train) → PCA (`n_components`, fit trên train) → scale `MinMaxScaler[0,1]` (fit trên train)
- `train_normal_only.parquet` = subset `train` với `isFraud==0`, dùng để train OCSVM (one-class)
- `{train,val,cal,test}.parquet` giữ cả normal + fraud, dùng để đánh giá (AUPRC, precision, recall, F1, FPR)

### 4.3 View `quantum_{n}q` — dành cho **Quantum 1 / Quantum 2**

- **Path:** `data/views/quantum_{n}q/{train,val,cal,test,train_normal_only}.parquet`
- **Dẫn xuất trực tiếp từ `classical_kernel_{n}f`** — dùng lại đúng `n` component đã PCA (không PCA lại lần 2), chỉ thêm 1 bước scale sang range của quantum encoding (mặc định `[0, π]`)
- `{n}` = số qubit dự kiến dùng — **cần xác nhận với Quantum 1/2**
- Subsample theo từng split riêng (không trộn train/test khi subsample) để giữ nguyên ranh giới split, giữ tỷ lệ fraud gốc — mặc định tối đa `quantum_max_samples` dòng/split (mặc định 3000)
- **⚠️ Cần xác nhận từ team Quantum 1 và Quantum 2:**
  - Số qubit simulator dự kiến dùng → quyết định `n_components`
  - Loại feature map/encoding cụ thể (ZFeatureMap, ZZFeatureMap...) → quyết định encoding range
  - Quantum 1 và Quantum 2 dùng chung 1 view hay cần 2 view riêng (`quantum_{n}q_v1`, `quantum_{n}q_v2`)?

---

## 5. Artifacts — lưu lại để tránh fit lại, đảm bảo có thể transform data mới

| File | Ý nghĩa |
|---|---|
| `data/artifacts/imputer.joblib` | SimpleImputer(median), fit trên train |
| `data/artifacts/pca_{n}.joblib` | PCA n_components, fit trên train (dùng chung cho kernel + quantum) |
| `data/artifacts/kernel_scaler_{n}f.joblib` | MinMaxScaler[0,1], fit trên train PCA components |
| `data/artifacts/quantum_scaler_{n}q.joblib` | MinMaxScaler[quantum range], fit trên train PCA components |

Khi có data mới (vd batch inference), dùng lại đúng các artifact này để transform — không fit mới.

---

## 6. Cấu trúc thư mục

```
data/
├── raw/                          # csv gốc + merged.parquet
├── cleaned/                      # canonical cleaned data (1 file duy nhất)
├── manifests/
│   └── split_manifest.parquet    # nguồn sự thật về split — dùng chung mọi nhánh
├── artifacts/                    # imputer/pca/scaler đã fit trên train
│   ├── imputer.joblib
│   ├── pca_8.joblib
│   ├── kernel_scaler_8f.joblib
│   └── quantum_scaler_8q.joblib
└── views/
    ├── classical_tree/
    ├── classical_kernel_8f/
    └── quantum_8q/
```

---

## 7. Metadata đi kèm mỗi lần release

- `feature_dictionary.csv` — tên cột, ý nghĩa, kiểu dữ liệu, nguồn gốc
- `categorical_cols.txt` (trong `classical_tree/`) — danh sách cột categorical
- `scaling_metadata.json` (trong `classical_kernel_{n}f/` và `quantum_{n}q/`) — phương pháp scale, range, số component, xác nhận "fitted_on: train split only"
- `validation_report.json` — kết quả check missing/dtype/leakage của lần chạy đó (Pha 2)

---

## 8. Quy trình khi cần thay đổi feature/split

1. Team downstream báo yêu cầu qua kênh chung (không nhắn riêng).
2. Data Engineering đánh giá — **nếu thay đổi `n_components` hoặc split ratio, phải chạy lại TOÀN BỘ 3 view** (vì chúng dùng chung artifact) để tránh 3 nhánh lệch nhau.
3. Chạy lại `dvc repro`, version mới được track tự động.
4. Cập nhật **Changelog** bên dưới + báo 1 lần cho cả team.

---

## 9. Changelog

| Ngày | Thay đổi | Người thực hiện |
|---|---|---|
| 2026-08-02 | Khởi tạo contract v1, Pha 1 (extraction + cleaning tối thiểu + feature v0, 3 output độc lập) | Data Engineering |
| 2026-08-17 | **v2**: sửa kiến trúc thành canonical data + fixed split_manifest + shared views để đảm bảo benchmark classical–quantum công bằng, tránh leakage (fit imputer/PCA/scaler chỉ trên train), thêm `train_normal_only` cho OCSVM, lưu artifact `.joblib` | Data Engineering |
| 2026-08-27 | **v3**: (1) Fix `add_frequency_features` — thay `value_counts()` toàn bộ df bằng `groupby().cumcount()` sort theo `TransactionDT` → loại bỏ rò rỉ tần suất từ tương lai; (2) Thêm `dvc.yaml` (4 stage: extract→clean→split→build_features) + `params.yaml` (tập trung toàn bộ tham số); (3) Expose `--random-seed` ra CLI của `build_features.py` (trước đó hardcode 42) — seed ảnh hưởng PCA và quantum subsampling, phải nhất quán giữa mọi lần chạy | Data Engineering |

---

## 10. Việc còn TODO / cần xác nhận từ team

- [ ] Xác nhận số qubit simulator & loại feature map với Quantum 1, Quantum 2 (quyết định `n_components`)
- [ ] Xác nhận Quantum 1 và Quantum 2 có cần view riêng không
- [ ] Xác nhận UI/API cần đọc trực tiếp từ nhánh nào (thường là kết quả model, không phải feature)
- [ ] Xác nhận tỷ lệ split train/val/cal/test (60/15/10/15) và `quantum_max_samples` có phù hợp thời gian train simulator không
- [x] ~~`add_frequency_features` rò rỉ tần suất tương lai~~ — **đã fix v3** (expanding count theo thời gian)
- [ ] Validation chi tiết với Great Expectations
- [ ] Airflow DAG (4 stage tương ứng `dvc.yaml`)
