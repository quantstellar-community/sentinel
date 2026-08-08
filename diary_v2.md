# Nhật ký phiên — Triển khai kiến trúc tầng (PIPELINE_V2)

> Ngày 2026-08-05 → 2026-08-06. Phiên này **thực thi** bản thiết kế trong [`PIPELINE_V2.md`](PIPELINE_V2.md): tái cấu trúc từ codebase một-dataset thành kiến trúc nhiều tầng chạy được cả `creditcard.csv` lẫn `ieeecis-fraud-detection`.
>
> Nhật ký Phase 0 / 1a / 1b nằm ở [`history.md`](history.md). File này tiếp nối từ đó.

---

## Mục lục

1. [Trạng thái đầu và cuối phiên](#1-trạng-thái-đầu-và-cuối-phiên)
2. [Plan đã duyệt](#2-plan-đã-duyệt)
3. [Bước 0–1 — Tầng 1–3 và ràng buộc di trú](#3-bước-01--tầng-13-và-ràng-buộc-di-trú)
4. [Bước 2 — Adapter IEEE-CIS](#4-bước-2--adapter-ieee-cis)
5. [Bổ sung ngoài plan — Tầng 4 cấu trúc](#5-bổ-sung-ngoài-plan--tầng-4-cấu-trúc)
6. [Bước 3 — Tầng 5 Label Regime](#6-bước-3--tầng-5-label-regime)
7. [Bước 4 — Chạy roster A/B/C](#7-bước-4--chạy-roster-abc)
8. [Lỗi phát hiện và đã sửa](#8-lỗi-phát-hiện-và-đã-sửa)
9. [Kết quả đo được](#9-kết-quả-đo-được)
10. [Dự đoán của tôi bị bác bỏ](#10-dự-đoán-của-tôi-bị-bác-bỏ)
11. [Đính chính cuối phiên về ưu tiên dự án](#11-đính-chính-cuối-phiên-về-ưu-tiên-dự-án)
12. [Tồn đọng và bước tiếp](#12-tồn-đọng-và-bước-tiếp)

---

## 1. Trạng thái đầu và cuối phiên

| | Đầu phiên | Cuối phiên |
|---|---:|---:|
| Test | 150 | **222** |
| Dòng code (`src`+`scripts`+`tests`) | 3,928 | **6,494** |
| Dataset chạy được | 1 | **2** |
| Model trong registry | 12 | **14** |
| Track nhãn | (không có khái niệm) | **A: 8 · B: 4 · C: 2** |
| Experiment record | 12 (creditcard) | 14 creditcard + **9 ieeecis** |
| `verify_migration` | (chưa tồn tại) | **12/12 tái lập chính xác** |

Test theo file cuối phiên:

```
test_models.py     83     test_metrics.py    24     test_features.py   21
test_regime.py     21     test_anomaly.py    20     test_datasets.py   20
test_splitter.py   12     test_loader.py     11     test_novel_fraud.py 10
```

---

## 2. Plan đã duyệt

Người dùng yêu cầu lên plan chi tiết trước khi làm. Plan gồm 9 bước; phiên này hoàn thành **Bước 0–4**.

Bốn quyết định thiết kế được chốt trước khi viết dòng code nào:

| # | Quyết định | Phương án |
|---|---|---|
| 1 | Truyền spec thế nào | **Tham số tường minh** qua cả ngăn xếp, không singleton |
| 2 | Vị trí split đã xử lý | `datasets/processed/<dataset>/` |
| 3 | Registry lồng theo dataset? | **Không** — phẳng, mỗi model khai `requires_entity` |
| 4 | Fixture test | Một generator duy nhất trong `conftest.py`, nhận `spec` |

**Ràng buộc di trú** (điều kiện nghiệm thu cứng): sau tái cấu trúc, kết quả creditcard phải tái lập **từng chữ số**. Đây là phép thử duy nhất phân biệt "tái cấu trúc" với "viết lại".

---

## 3. Bước 0–1 — Tầng 1–3 và ràng buộc di trú

### Bước 0 — chốt golden reference

```bash
cp -r experiments/results experiments/results_pre_refactor
```

12 record được đóng băng làm bản đối chứng trước khi động vào code.

### File thêm mới

| File | Dòng | Nội dung |
|---|---:|---|
| `src/datasets/spec.py` | 162 | `DatasetSpec` — mọi thứ khiến hai dataset khác nhau, dưới dạng dữ liệu |
| `src/datasets/creditcard.py` | 57 | Instance `CREDITCARD` |
| `src/datasets/ieeecis.py` | 79 | Instance `IEEECIS` |
| `src/datasets/__init__.py` | 54 | `SPECS`, `get_spec()` |
| `tests/conftest.py` | 105 | Fixture sinh khung dữ liệu **theo spec** |
| `tests/test_datasets.py` | 148 | 20 test hợp đồng tầng 1 |
| `scripts/verify_migration.py` | 142 | Đối chiếu với golden reference, dung sai `1e-9` |

### Phạm vi sửa (đo bằng grep trước khi bắt đầu)

| Hằng số schema | Số chỗ | | Hằng số protocol | Số chỗ |
|---|---:|---|---|---:|
| `TARGET_COLUMN` | 43 | | `SEED` | 14 |
| `TIME_COLUMN` | 25 | | `N_BOOTSTRAP` | 9 |
| `FEATURE_COLUMNS` | 21 | | `PROCESSED_DIR` | 6 |
| còn lại | ~53 | | còn lại | 6 |
| **Phải sửa** | **~142** | | **Giữ nguyên** | **35** |

`src/config.py` được rút xuống còn hằng số **protocol**: `SEED`, `N_BOOTSTRAP`, `BOOTSTRAP_ALPHA`, `PRECISION_AT_K`, `MIN_DISTINCT_SCORE_RATIO`. Mọi thứ mô tả *dataset* chuyển sang `src/datasets/`.

### Hai bổ sung thiết kế ngoài plan

Cả hai phát sinh từ chính ràng buộc tái lập:

**`ScaleSpec` với literal `"none" / "all" / "default" / "amount"`.** Cần vì `logreg` phải scale đúng `[Time, Amount]` để tái lập `0.6932`, mà không được hardcode tên cột creditcard vào model — nếu không thì model không chạy được trên IEEE-CIS.

**`bind(spec)` trên `SentinelModel`.** Cần vì hybrid phải resolve feature của component lồng bên trong lúc `fit`, mà `fit(X, y)` không nhận spec. Phương án thay thế là đổi chữ ký `fit` — tránh vì nó phá dạng sklearn quen thuộc.

Plan của tôi cũng **đếm thiếu file phải sửa**: liệt kê `models/base.py` và `models/anomaly.py` nhưng thực tế phải sửa thêm `supervised.py`, `hybrid.py`, `models/__init__.py`. Lý do máy móc — đổi API lớp cha thì mọi lớp con buộc đổi theo.

### Nghiệm thu

| Lệnh | Kết quả |
|---|---|
| `pytest` | 168 pass (150 migrate + 18 mới) |
| `build_splits --dataset creditcard` | dev 226,982/399 · holdout 56,744/74 · fold 69/47/89/52 — **khớp** |
| `run_experiment --model xgboost` | **0.7741** · `[0.8168, 0.6668, 0.8213, 0.7916]` — **khớp** |
| `verify_migration.py` | **12/12 model tái lập chính xác** |

Sau đó dọn 12 thư mục flat cũ (đã xác nhận trùng khớp với `creditcard/`), chuyển `comparisons/` và `novel_fraud/` vào namespace.

---

## 4. Bước 2 — Adapter IEEE-CIS

### `scripts/profile_dataset.py` — đo trước khi chốt spec

Nguyên tắc ghi thẳng vào docstring: **so ứng viên proxy thực thể bằng tiêu chí phi-nhãn**. Cột "fraud concentration" có in ra nhưng **cố ý không dùng để chọn** — chọn định nghĩa thực thể bằng nhãn sẽ rò rỉ nhãn vào *mọi* behavioral feature xây trên đó, và rò rỉ đó vô hình trong kết quả.

### Kết quả đo

| | creditcard | IEEE-CIS |
|---|---:|---:|
| Giao dịch | 284,807 | **590,540** |
| Fraud | 492 | **20,663** |
| Tỷ lệ | 0.17% | **3.50%** |
| Thời gian | 2 ngày | **182 ngày** |
| Cột (sau join) | 31 | **434** |
| Dòng trùng hoàn toàn | 1,081 | **0** |

**Hai phát hiện:**

`test_transaction.csv` **không có cột `isFraud`** — test set cuộc thi Kaggle, nhãn do ban tổ chức giữ. Chỉ dùng được `train_transaction.csv`.

Tỷ lệ fraud **trôi theo thời gian** — drift thật, lần đầu đo được:

| Khối 30 ngày | 0 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Tỷ lệ | 2.48% | **4.04%** | 4.03% | 3.93% | 3.47% | **3.40%** | 4.18% |

Biên độ 1.69×.

### Proxy thực thể — đo, chưa đổi

| Ứng viên | nhóm | txn/nhóm | singleton | txn trong nhóm ≥5 |
|---|---:|---:|---:|---:|
| `card1` | 13,553 | 43.6 | **25.4%** | **97.7%** |
| `card1+addr1` | 37,531 | 15.7 | 39.5% | 81.7% |
| **`card1+card2+addr1`** *(đang dùng)* | 37,280 | 15.8 | 39.5% | 80.3% |
| `card1+addr1+D1n` | 199,070 | 3.0 | **58.0%** | 44.0% |

Mẹo `D1n` phổ biến trên Kaggle **làm vỡ vụn** dữ liệu ở đây chứ không gom lại — loại. `card1` cho lịch sử dùng được nhiều hơn hẳn nhưng thô hơn (43.6 giao dịch/nhóm gợi ý nó gom nhiều thẻ). Không có tiêu chí phi-nhãn nào phân định → **giữ nguyên, để thành phép đo ở bước feature hành vi**.

### Splits IEEE-CIS

| | dòng | fraud | tỷ lệ |
|---|---:|---:|---:|
| dev | 472,432 | 16,599 | 3.514% |
| holdout 🔒 | 118,108 | **4,064** | 3.441% |

Fold val: `[1634, 2664, 2885, 2432, 2775, 2405]` — trung bình **2,465**, **gấp ~32–35×** creditcard.

---

## 5. Bổ sung ngoài plan — Tầng 4 cấu trúc

### Vì sao phải chèn vào

Plan đặt Bước 4 (*"chạy roster A/B/C trên cột thô, cả hai dataset"*) **trước** tầng 4. Bất khả thi, vì IEEE-CIS có:

- **31 cột kiểu chuỗi** mà XGBoost/sklearn không ăn trực tiếp
- **384/401 cột số có NaN**

creditcard không có cả hai nên tôi đã không lường. Đây là lỗi thứ tự trong plan của tôi.

### Giải pháp — tách tầng 4 làm hai nhóm

| Nhóm | Thành phần | Cần entity | Giao ở |
|---|---|---|---|
| **Cấu trúc** | `PassThrough`, `CategoricalEncode`, (`TimeOfDay` opt-in) | ❌ | **Trước Bước 4** |
| **Hành vi** | `RollingWindows`, `VelocityRatios`, `EntityHistory`, `Benford` | ✅ | Sau |

Phân biệt then chốt được ghi vào code:

- **Structural** — làm dữ liệu dùng được mà **không thêm thông tin**. Bật mặc định an toàn.
- **Derived** — tạo tín hiệu mới, đổi không gian feature, đổi **mọi con số downstream**. Phải opt-in và phải đo.

`TimeOfDay` thuộc nhóm hai nên **không nằm trong pipeline mặc định**, dù nó không cần entity.

### `handles_missing` — bổ sung vào hợp đồng tầng 6

```python
class SentinelModel:
    handles_missing: bool = False   # XGBoost/LightGBM khai True
```

Runner chỉ impute (median học **trên train**) khi model khai là không tự xử lý được. Lý do: trên IEEE-CIS *"trường identity này không được thu thập"* là **tín hiệu thật**, và median fill sẽ xóa nó. Giữ cho XGBoost đọc NaN nguyên bản.

### Kiểm chứng

Pipeline trên IEEE-CIS: **432 cột, 0 cột chuỗi**, 296 cột còn NaN (đúng — model nào cần thì runner impute).
Pipeline trên creditcard: **identity đúng 30 cột cũ** → kết quả tái lập.

Test tôi coi là quan trọng nhất của tầng này:

```python
def test_transform_of_a_row_does_not_depend_on_later_rows():
    """Không phải "fit() có nhận train không" — cái đó một implementation
    vẫn lén nhìn tương lai cũng thỏa mãn. Điều phải đúng là: xóa tương lai
    đi thì hiện tại không đổi."""
```

---

## 6. Bước 3 — Tầng 5 Label Regime

### Vì sao là một tầng, không phải một cờ

Thiếu tầng này thì ranh giới "supervised" / "unsupervised" là mơ hồ. Một anomaly model huấn luyện trên riêng lớp bình thường có phải unsupervised không?

**Không.** Nó **dùng nhãn để lọc tập train**, chỉ là không đưa vào loss. Đó là *one-class semi-supervised*. Model thật sự mù nhãn phải huấn luyện trên **toàn bộ**, gồm cả fraud chưa phát hiện.

### Ba chế độ

```python
FullySupervised   # track A — (X, y) nguyên vẹn
OneClass          # track B — (X[y==0], y[y==0]); nhãn dùng để LỌC
Unlabeled         # track C — (X, zeros); không thông tin nhãn nào
PartialLabel(p)   # A/C — chỉ lộ p% fraud, mô hình độ trễ nhãn
```

**Bất biến quyết định:** nhãn thật **luôn** dùng ở tầng 8, bất kể model thấy gì lúc fit. Nhờ đó câu *"model hoạt động ra sao khi mù nhãn"* thành **phép đo**, không phải phỏng đoán.

### Hai hàng rào phát sinh khi làm

**Cổng chặn supervised + track C.** Model supervised mù nhãn sẽ huấn luyện trên target hằng số và **vẫn cho ra một con số**. Runner raise. Ngoại lệ duy nhất: `generates_own_labels=True`, dành cho `pu_cascade` sau này.

**`__init_subclass__` chặn khai báo chết.** `trains_on_normal_only` giờ là property đọc từ regime; subclass nào còn gán nó sẽ **im lặng không có tác dụng**. Tôi bị đúng lỗi đó khi migrate test, nên thêm `TypeError` chỉ thẳng sang `label_regime`.

### Test cốt lõi

```python
def test_a_track_c_model_never_receives_a_positive_label():
    assert seen == [0, 0], f"a track C model was shown positives: {seen}"
    assert all(outcome.val_y.sum() > 0 for outcome in record.folds), (
        "the evaluation folds must contain fraud, or the test proves nothing"
    )
```

Vế thứ hai quan trọng ngang vế thứ nhất — không có nó, test vẫn pass khi fold đánh giá rỗng fraud và chẳng chứng minh được gì.

---

## 7. Bước 4 — Chạy roster A/B/C

9 model nhanh chạy trên IEEE-CIS (bỏ nhóm autoencoder, xem [§11](#11-đính-chính-cuối-phiên-về-ưu-tiên-dự-án)), kèm 6 paired test.

Trên creditcard: chạy lại đủ 14 model để làm mới metadata `track`/`label_regime` (10 record cũ thiếu). `verify_migration` xác nhận **không con số nào dịch chuyển**.

---

## 8. Lỗi phát hiện và đã sửa

### 8.1 Cờ `--dataset` bị bỏ qua âm thầm — nghiêm trọng nhất

Lần chạy IEEE-CIS đầu tiên **chạy nhầm creditcard**. Nguyên nhân: `run_and_report` gọi `run_cv(factory, n_bootstrap=...)` — **thiếu `spec=spec`**. Khối thay thế trong script sửa file của tôi không khớp và fail âm thầm.

Đây là loại lỗi nguy hiểm nhất trong dự án này: **chạy trót lọt, in số hợp lý, ghi record hợp lệ** — chỉ là sai dataset, và không có gì trong output nói ra. Tôi chỉ bắt được vì thuộc số fold của creditcard (69/47/89/52).

Đã thêm test chặn regression monkeypatch `run_cv` để bắt đúng lỗi này:

```python
def test_run_and_report_passes_the_spec_through(monkeypatch):
    assert captured["spec"] is IEEECIS, "the requested dataset never reached run_cv"
```

Hệ quả phụ: lần chạy sai ghi đè `creditcard/xgboost/record.json` với `n_bootstrap=200`. Đã chạy lại với mặc định 2000.

### 8.2 Cùng một lỗi lặp lại lần thứ hai

Khối thay thế `print(f"track  : ...")` trong `run_and_report` cũng fail âm thầm vì cùng lý do — escape `\n` trong heredoc không khớp. **Sau lần này tôi chuyển hẳn sang `Edit`** cho các sửa đổi nhiều dòng thay vì script `str.replace`.

Bài học: `str.replace` không báo lỗi khi không khớp. Với chuỗi nhiều dòng có escape, nó là công cụ sai.

### 8.3 Test cũ khai báo chết sau khi đổi API

`test_runner_honours_trains_on_normal_only` set `trains_on_normal_only = True` như class attribute — giờ thành no-op. Đã sửa test và thêm `__init_subclass__` guard (xem §6).

### 8.4 Record cũ thiếu metadata

10/12 record creditcard chạy trước tầng 5 nên thiếu `track`/`label_regime`. Số liệu đúng, chỉ metadata cũ. Đã chạy lại toàn bộ để cây kết quả nhất quán.

---

## 9. Kết quả đo được

### 9.1 Bảng tổng hợp

| Model | Track | creditcard | IEEE-CIS |
|---|:---:|---:|---:|
| logreg | A | 0.6932 | 0.1899 |
| logreg_full_scale | A | 0.6968 | 0.2006 |
| xgboost | A | **0.7741** | 0.5393 |
| xgboost_unweighted | A | 0.7673 | 0.5790 |
| lightgbm | A | 0.5011 | 0.5662 |
| lightgbm_unweighted | A | 0.7694 | **0.5937** |
| isolation_forest | B | 0.0871 | 0.1877 |
| isolation_forest_with_time | B | 0.0711 | 0.1893 |
| autoencoder | B | 0.2116 | *(chưa chạy)* |
| autoencoder_minimal_scale | B | 0.1106 | *(chưa chạy)* |
| if_contaminated | C | 0.1086 | 0.1956 |
| ae_contaminated | C | 0.0600 | *(chưa chạy)* |

**Không so AUPRC trần giữa hai bộ** — sàn ngẫu nhiên khác nhau (0.0015 vs 0.0242). Quy về lift: creditcard **537×**, IEEE-CIS **19×**. IEEE khó hơn nhiều so với sàn của chính nó.

### 9.2 Khoảng tin cậy sụp 5.2× — thay đổi quan trọng nhất

| | creditcard | IEEE-CIS |
|---|---:|---:|
| Độ rộng CI (xgboost) | **0.2090** | **0.0402** |
| Fraud mỗi fold | 47–89 | 1,634–2,885 |

Trước đây CI rộng 0.21 — **lớn hơn hầu hết khoảng cách giữa các model**, nên bảng xếp hạng vô nghĩa và chỉ paired test mới phân giải được. Giờ 0.04.

### 9.3 Sáu paired test trên IEEE-CIS — tất cả 6/6 fold

| So sánh | Mean delta | Fold có ý nghĩa | Kết luận |
|---|---:|---|---|
| logreg → xgboost | **+0.3494** | **6/6** | XGBoost thắng dứt khoát |
| xgboost → xgboost_unweighted | +0.0397 | **6/6** | Bỏ trọng số thắng |
| lightgbm → lightgbm_unweighted | +0.0275 | **6/6** | Bỏ trọng số thắng |
| isolation_forest → if_contaminated | +0.0079 | **5/6** | **Track C thắng track B** |
| iforest_with_time → iforest | −0.0016 | 1 thắng 2 thua | Nhiễu |
| isolation_forest → xgboost | +0.3516 | **6/6** | A − B rất lớn |

### 9.4 Ba kết quả đáng chú ý

**`scale_pos_weight` có hại cho *cả hai* boosting model trên IEEE-CIS.**

| | creditcard | IEEE-CIS |
|---|---|---|
| xgboost → unweighted | −0.0069, **0/4** | **+0.0397, 6/6** |
| lightgbm → unweighted | +0.2683, 4/4 | **+0.0275, 6/6** |

Khuyến nghị `scale_pos_weight ≈ 578` trong `research_synthesis.md` §2.2 giờ **bị bác bỏ trên 3/4 tổ hợp model × dataset**.

**Isolation Forest ngang bằng logistic regression trên IEEE-CIS.** creditcard: 0.0871 vs 0.6932 (kém **8×**). IEEE: 0.1877 vs 0.1899 (**hòa**). Thay đổi về chất.

**Bỏ cột `Time` khỏi anomaly model là quyết định phụ thuộc dataset.** creditcard thắng 3/4 fold; IEEE **1 thắng 2 thua — nhiễu**. Lập luận vẫn đúng nhưng **không phổ quát** như docstring đã viết. Giữ nguyên vì không hại.

### 9.5 Bảng A − B / B − C

| | creditcard (nhiễm 0.17%) | IEEE-CIS (nhiễm 3.50%) |
|---|---:|---:|
| **A − B** giá trị của nhãn trong loss | +0.6871 | +0.3516 |
| **B − C** Isolation Forest | −0.0215 | −0.0079 |
| **B − C** Autoencoder | **+0.1515** | **chưa đo** |

---

## 10. Dự đoán của tôi bị bác bỏ

Tôi dự đoán trong `PIPELINE_V2.md` §7: *"B − C ≈ 0 trên creditcard vì nhiễm bẩn ở 0.17% là không đáng kể; đáng kể trên IEEE-CIS ở 3.5%"*.

**Sai.** Hai anomaly model phản ứng **ngược chiều nhau** ở cùng mức nhiễm bẩn 0.17%:

| Model | Track B | Track C | B − C |
|---|---:|---:|---:|
| Isolation Forest | 0.0871 | **0.1086** | −0.0215 (C tốt hơn) |
| Autoencoder | **0.2116** | 0.0600 | **+0.1515** (B tốt hơn **3.53×**) |

Autoencoder thắng **4/4 fold**, khoảng tin cậy cách xa 0.

### Cơ chế — suy ra từ hàm mục tiêu, không phải suy đoán

- **Autoencoder** tối thiểu hóa sai số tái tạo trên **mọi điểm** tập train. Cho fraud vào → học tái tạo cả fraud → fraud có sai số thấp → điểm bất thường mất khả năng phân biệt. **399 điểm cũng đủ.**
- **Isolation Forest** không tối ưu hàm mục tiêu nào trên tập train; nó dựng phân hoạch ngẫu nhiên với `max_samples=256`, nên **phần lớn cây không hề thấy một điểm fraud nào**.

**Kết luận sửa lại:** độ nhạy nhiễm bẩn là thuộc tính của **hàm mục tiêu**, không phải của tỷ lệ nhiễm bẩn.

### Suýt báo cáo sai về Isolation Forest

Lần chạy một seed cho "C thắng 2/4 fold". Kiểm tra **5 seed × 4 fold** mới thấy:

| Fold | B − C qua 5 seed | Đọc |
|---|---|---|
| 0, 1, 3 | \|δ\| < 0.011, **đảo dấu theo seed** | Nhiễu |
| **2** | −0.047 … −0.102 | **Nhất quán — hiệu ứng thật** |

Nếu không kiểm tra seed, tôi đã báo "track C thắng 2/4 fold" mà không biết 3/4 trong đó là nhiễu subsample. Cơ chế đằng sau fold 2 **chưa xác lập được**.

*(Ghi chú về mức độ chắc chắn: với autoencoder tôi **không** kiểm tra seed — hiệu ứng 0.15, thắng 4/4, CI cách xa 0, chiều khớp cơ chế. Đó là suy luận, không phải phép đo.)*

---

## 11. Đính chính cuối phiên về ưu tiên dự án

Cuối phiên tôi đề xuất **bỏ autoencoder toàn-chiều trên IEEE-CIS** (ước lượng ~3 giờ) và thay bằng phiên bản *budgeted* 8 feature, với lý lẽ rằng nó gần với so sánh Quantum Autoencoder ở Phase 2 hơn.

**Người dùng đính chính rằng tôi hiểu sai ưu tiên của dự án:**

> Classical ML là phần **quan trọng, phải phát triển tới mức tối ưu và tốt nhất**. Quantum là một **thử nghiệm** để trả lời "khi có quantum thì kết quả fraud thay đổi thế nào". Hiện tại chỉ tập trung xây kiến trúc classical ML tốt nhất; quantum để sau.

### Đề xuất của tôi bị lật ngược

| | Đề xuất sai của tôi | Đúng theo ưu tiên dự án |
|---|---|---|
| AE toàn-chiều trên IEEE | Bỏ | **Phải chạy — nó LÀ baseline classical** |
| AE budgeted (8 feature) | Ưu tiên | **Để sau, cùng Phase 2** |

Lý do tôi sai: tôi lấy ràng buộc phần cứng quantum (4–8 feature) làm ràng buộc thiết kế cho **toàn bộ** tầng anomaly, trong khi nó chỉ là ràng buộc của **một thí nghiệm sẽ chạy sau**.

### Phần phân tích vẫn còn giá trị

Hai điều đã tính ra trong lúc đó vẫn đúng và nên giữ để dùng khi tới Phase 2:

**Nút cổ chai không phải ràng buộc của so sánh QAE — số feature đầu vào mới là.** QAE sẽ không bao giờ nhận 431 feature. Phép so sánh Phase 2 là *cả hai bên ở cùng k feature*, không phải cùng nút cổ chai.

**IEEE-CIS làm quantum kernel khả thi theo cách creditcard không bao giờ có được.** Quantum kernel cần `n(n+1)/2` lần chạy mạch; giữ nguyên tỷ lệ fraud tự nhiên:

| n | thời gian (1ms/mạch) | fraud @0.17% | fraud @3.5% |
|---:|---:|---:|---:|
| 2,000 | 33 phút | **3** | **70** |
| 10,000 | 14 giờ | **17** | **350** |

Trên creditcard, quy mô chạy được cho **3 ca fraud** — buộc phải cân bằng lại mẫu, và AUPRC ở tỷ lệ 50/50 **không chuyển đổi được** về tỷ lệ thật. Trên IEEE-CIS, 2,000 dòng cho **70 ca** (ngang toàn bộ holdout creditcard) và 10,000 dòng qua một đêm cho **350 ca**.

### Một dự báo cho Phase 2 rút ra từ kết quả classical

QAE tối đa hóa **fidelity** giữa trạng thái vào và trạng thái tái tạo, trên toàn tập train — cùng cấu trúc với AE cổ điển tối thiểu hóa MSE: **mọi điểm huấn luyện đều đóng góp vào hàm mục tiêu**.

Nên kết quả đã đo (AE mất **72% hiệu năng** vì nhiễm bẩn ở mức 0.17%) **dự báo một chế độ hỏng của QAE**: triển khai QAE mà không có dữ liệu huấn luyện sạch sẽ suy giảm y hệt. Suy luận từ cấu trúc, chưa phải phép đo — nhưng đủ cụ thể để kiểm chứng.

---

## 12. Tồn đọng và bước tiếp

### Chưa làm trong phiên này

| # | Việc | Ghi chú |
|---|---|---|
| 1 | **Nhóm autoencoder trên IEEE-CIS** | 3 model, ~3 giờ. **Ưu tiên cao** theo §11 — là baseline classical |
| 2 | Tầng 4 nhóm **hành vi** | `RollingWindows`, `VelocityRatios`, `EntityHistory`, `Benford` — cần sửa 4 chỗ rò rỉ (`groupby().transform()` → `expanding()`) |
| 3 | `pu_cascade` (track C sinh nhãn) | Hạ tầng đã sẵn qua `generates_own_labels` |
| 4 | Tầng 9 — drift protocol | IEEE-CIS có drift thật 1.69× |
| 5 | Tầng 10 — SHAP + counterfactual | Đóng hạng mục Phase 1 còn thiếu |

### Quyết định còn mở

**Kiến trúc autoencoder cho dữ liệu rộng.** Hiện tại `431 → 20 → 14 → 7` nén **62:1** (creditcard chỉ 4:1). Đáng chú ý: nén xuống 20 xảy ra **ngay ở lớp đầu** — 21:1 — nên nút cổ chai 7 không phải chỗ thắt thật. Một AE hợp lý cho 431 chiều cần nới cả lớp ẩn (ví dụ `431 → 128 → 64 → 32`), tức nhiều tham số hơn ~17× và chậm hơn nữa.

Đề xuất: **chạy 1 fold trước** với cấu hình hiện tại để xem có suy biến không. `score_resolution_warning` trong runner sẽ báo động nếu điểm số sụp — đó là tín hiệu sẵn có để đọc.

**Proxy thực thể.** `card1` cho lịch sử dùng được 97.7% vs 80.3% của `card1+card2+addr1`, nhưng thô hơn. Giữ nguyên khai báo hiện tại, để thành phép đo khi có feature hành vi.

**`V1–V339` của Vesta.** 339 cột, NaN median 47.3%. Giữ hết hay lọc chưa quyết. Nếu lọc **phải lọc bên trong training fold**.

### Ràng buộc phải giữ

> Mọi thay đổi tầng 1–3 phải giữ `verify_migration.py` **12/12**. `xgboost` trên creditcard phải vẫn cho `0.7741` với per-fold `[0.8168, 0.6668, 0.8213, 0.7916]`.

---

## Phụ lục — Lệnh

```bash
# Splits
uv run python scripts/build_splits.py --dataset creditcard
uv run python scripts/build_splits.py --dataset ieeecis

# Đo dataset trước khi chốt spec
uv run python scripts/profile_dataset.py --dataset ieeecis

# Chạy model
uv run python scripts/run_experiment.py --dataset ieeecis --model xgboost
uv run python scripts/run_experiment.py --dataset ieeecis --all

# Paired test — thứ quyết định, không phải bảng xếp hạng
uv run python scripts/compare_models.py --dataset ieeecis logreg xgboost

# Ràng buộc di trú
uv run python scripts/verify_migration.py

uv run pytest          # 222 test
```

### Cây thư mục mới trong phiên

```text
src/datasets/          spec.py · creditcard.py · ieeecis.py · __init__.py
src/features/          base.py · structural.py · __init__.py
src/models/regime.py   FullySupervised · OneClass · Unlabeled · PartialLabel
scripts/               profile_dataset.py · verify_migration.py
tests/                 conftest.py · test_datasets.py · test_features.py · test_regime.py

datasets/processed/creditcard/   dev.parquet · holdout.parquet · split_manifest.json
datasets/processed/ieeecis/      dev.parquet · holdout.parquet · split_manifest.json
experiments/results/creditcard/  14 record + comparisons/ + novel_fraud/
experiments/results/ieeecis/     9 record + comparisons/
experiments/results_pre_refactor/  golden reference (12 record)
```
