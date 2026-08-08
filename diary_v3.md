# Nhật ký phiên — Hoàn tất kiến trúc tầng (Bước 5 → 9 + ngoài plan)

> Ngày 2026-08-06 → 2026-08-07. Phiên này thực thi **toàn bộ phần còn lại** của plan trong [`PIPELINE_V2.md`](PIPELINE_V2.md) §15 — Bước 5 đến Bước 9 — cộng ba hạng mục ngoài plan (tìm kiếm siêu tham số, cửa sổ trượt, năm phép đo củng cố). Sau phiên này, cả **10 tầng kiến trúc và cả 10 thí nghiệm** trong chương trình nghiên cứu đều đã có kết quả.
>
> Nhật ký Bước 0–4 nằm ở [`diary_v2.md`](diary_v2.md); Phase 0/1 ở [`history.md`](history.md). File này tiếp nối từ đó và là bản tổng hợp đầy đủ của phiên — thay thế các bản nháp trước.

---

## Mục lục

**Tổng quan**
1. [Trạng thái đầu và cuối phiên](#1-trạng-thái-đầu-và-cuối-phiên)
2. [Bản đồ: bước nào trả lời thí nghiệm nào](#2-bản-đồ-bước-nào-trả-lời-thí-nghiệm-nào)

**Từng bước, theo thứ tự đã làm**
3. [Bước 5 — Tầng 4: nhóm feature hành vi](#3-bước-5--tầng-4-nhóm-feature-hành-vi)
4. [Bước 6 — Roster hành vi trên IEEE-CIS](#4-bước-6--roster-hành-vi-trên-ieee-cis)
5. [Ngoài plan — Tầng tìm kiếm siêu tham số](#5-ngoài-plan--tầng-tìm-kiếm-siêu-tham-số)
6. [Bước 7 — `pu_cascade`](#6-bước-7--pu_cascade)
7. [Bước 8 — Tầng 9: drift protocol](#7-bước-8--tầng-9-drift-protocol)
8. [Ngoài plan — Cửa sổ trượt và bất biến IV](#8-ngoài-plan--cửa-sổ-trượt-và-bất-biến-iv)
9. [Bước 9 — Tầng 10: explanation](#9-bước-9--tầng-10-explanation)
10. [Ngoài plan — Năm phép đo củng cố](#10-ngoài-plan--năm-phép-đo-củng-cố)

**Tổng hợp**
11. [Bảng kết quả đầy đủ — IEEE-CIS](#11-bảng-kết-quả-đầy-đủ--ieee-cis)
12. [Năm kỳ vọng trong tài liệu — bốn sai, một đúng](#12-năm-kỳ-vọng-trong-tài-liệu--bốn-sai-một-đúng)
13. [Lỗi của tôi trong phiên](#13-lỗi-của-tôi-trong-phiên)
14. [Việc chưa làm / cần làm / nên làm](#14-việc-chưa-làm--cần-làm--nên-làm)

---

## 1. Trạng thái đầu và cuối phiên

| | Đầu phiên | Cuối phiên |
|---|---:|---:|
| Test | 222 | **380** |
| Dòng code (`src`+`scripts`+`tests`) | 6,494 | **11,204** |
| Model trong registry | 14 | **23** |
| Dataset spec | 2 | **3** (+`ieeecis_card1`) |
| Áp dụng được trên creditcard | 14 | 15 |
| Áp dụng được trên IEEE-CIS | 14 | 23 |
| Feature group | 3 (chỉ structural) | **7** (+4 hành vi) |
| Tầng kiến trúc đã xây | 1–8 | **1–10 (đủ)** |
| Experiment record — creditcard | 14 | **15** |
| Experiment record — ieeecis | 9 | **23** |
| Experiment record — ieeecis_card1 | — | **2** |
| Paired comparison — creditcard | 10 | **12** |
| Paired comparison — ieeecis | 10 | **18** |
| Paired comparison — ieeecis_card1 | — | **1** |
| Thí nghiệm #1–#10 (PIPELINE_V2 §14) | 6/10 có kết quả | **10/10** |
| `verify_migration` | 12/12 | **12/12** (không đổi suốt phiên) |

File nguồn thêm mới:

| File | Dòng | Nội dung |
|---|---:|---|
| `src/features/behavioral.py` | 530 | 4 nhóm hành vi + `_EntityView` + carry-over lịch sử |
| `src/models/behavioral.py` | 151 | 5 model hành vi + 2 mixin |
| `src/models/tuning.py` | 270 | `TunedModel` + 2 không gian tìm kiếm |
| `src/models/pu.py` | 215 | `PUCascade` — track C sinh nhãn của chính nó |
| `src/evaluation/drift.py` | ~330 | Tầng 9 — 3 arm (đóng băng, trượt, mở rộng) + phân tách paired |
| `src/evaluation/explain.py` | ~380 | Tầng 10 — TreeSHAP + counterfactual + tối ưu hiệu năng theo thực thể |
| `src/data/splitter.py` | +130 | `sliding_window_folds()` |
| `scripts/` | ~300 | `pu_diagnostic` · `drift_experiment` · `explain_alerts` |
| `tests/` | ~1,500 | 144 test mới |

Ràng buộc di trú (creditcard `xgboost` = `0.7741`, per-fold `[0.8168, 0.6668, 0.8213, 0.7916]`) **giữ nguyên suốt phiên**, xác nhận lại ở mọi mốc kiểm tra.

---

## 2. Bản đồ: bước nào trả lời thí nghiệm nào

| Bước | Tầng | Thí nghiệm (§14) | Trạng thái |
|---|---|---|:---:|
| 5 | Tầng 4 hành vi | — (hạ tầng cho #2–#5) | ✅ |
| 6 | Roster hành vi | #2, #3, #4, #5 | ✅ |
| *(ngoài plan)* | Tìm kiếm siêu tham số | — | ✅ |
| 7 | `pu_cascade` | #8 | ✅ |
| 8 | Tầng 9 drift | #9, #10 | ✅ |
| *(ngoài plan)* | Cửa sổ trượt | tách bạch #9/#10 | ✅ |
| 9 | Tầng 10 explanation | — (yêu cầu thiết kế #5) | ✅ |
| *(từ phiên trước)* | — | #1, #6, #7 | ✅ |

Cả 10 thí nghiệm trong chương trình nghiên cứu giờ đều có kết quả đo được, không còn ô trống nào trong bảng §14 của PIPELINE_V2.

---

## 3. Bước 5 — Tầng 4: nhóm feature hành vi

### Bốn nhóm, 26 cột

`RollingWindows` (12 cột — tổng/đếm trong 6 cửa sổ trượt), `VelocityRatios` (7 cột — cửa sổ ngắn so với dài), `EntityHistory` (6 cột — thống kê mở rộng nghiêm ngặt trước dòng hiện tại), `BenfordDeviation` (1 cột — độ lệch định luật Benford).

### Quyết định thiết kế bản gốc bỏ sót: lịch sử phải đi qua ranh giới fold

PIPELINE_V2 §6 mô tả bốn nhóm nhưng **không nói gì** về việc lịch sử đi qua ranh giới fold thế nào. Một `FeatureGroup` chỉ nhận một khung dữ liệu mỗi lần gọi; để nguyên thì `transform(val)` sẽ **khởi động lại lịch sử mọi thực thể từ dòng đánh giá đầu tiên** — một khách hàng đã có 50 giao dịch trong train hiện ra như khách mới. Train và val khi đó mang **hai đại lượng khác nhau dưới cùng một tên cột**.

**Cách xử lý:** `fit()` lưu `(entity, time, amount)` của mọi dòng train; `transform()` ghép vào phần lịch sử **xảy ra nghiêm ngặt trước** khung nó nhận được. Không rò rỉ vì hai lý do độc lập — `fit()` chỉ nhận train nên lịch sử lưu không thể chứa dòng đánh giá; và chỉ dùng phần sớm hơn nghiêm ngặt nên thông tin vẫn chảy một chiều. Quy tắc "sớm hơn nghiêm ngặt" còn khiến `transform(train)` ngay sau `fit(train)` không đếm trùng lịch sử của chính nó.

Test cốt lõi khẳng định tính qua ranh giới fold **bằng** tính một lượt trên khung đã nối:

```python
def test_features_across_a_split_match_a_single_pass_over_the_joined_frame(group_class):
    across_the_split = group_class().fit(train, IEEECIS).transform(validation)
    in_one_pass      = group_class().fit(df, IEEECIS).transform(df).iloc[300:]
    pd.testing.assert_frame_equal(across_the_split, in_one_pass)
```

### Lỗi có sẵn ở tầng 1 — bị bắt nhờ tầng hành vi mới

`DatasetSpec.entity_id` nối các thành phần khóa ghép bằng `astype(str)`. Trong pandas 2.x, **`astype(str)` giữ nguyên `NaN`**, nên một thành phần thiếu làm null cả định danh. Và `pd.factorize` đánh dấu null bằng `-1`, mà `-1` sắp **trước mọi mã thật** — nên không gây lỗi, chúng gộp thành **một thực thể duy nhất mang 60,416 giao dịch "lịch sử"** (60,417 dòng IEEE-CIS thiếu `addr1` hoặc `card2`).

**Phát hiện:** `HIST_TXN_COUNT` mean 7,187, max 60,416 — trong khi nhóm lớn nhất theo `value_counts()` chỉ có 4,708 dòng. Đối chiếu với `df.groupby(entity).cumcount()` độc lập xác nhận lệch.

**Sửa:** điền `ENTITY_MISSING = "?"` cho thành phần thiếu (khớp với `MISSING_CODE` của bộ mã hóa phân loại — vắng mặt là trạng thái phân biệt được, không phải null). Hàng rào kèm theo: `_EntityView` **raise** nếu gặp mã âm.

**Hệ quả:** bảng proxy thực thể trong diary_v2 sai vì cùng lỗi (`profile_dataset.py` dùng `value_counts()`, âm thầm bỏ NA khỏi mẫu số):

| Ứng viên | diary_v2 (có lỗi) | **đúng** |
|---|---|---|
| `card1+addr1` | 37,531 · 39.5% · **81.7%** | 39,974 · 39.4% · **92.3%** |
| **`card1+card2+addr1`** *(đang dùng)* | 37,280 · 39.5% · **80.3%** | **41,672 · 40.3% · 91.9%** |

*(cột: số nhóm · singleton · % giao dịch trong nhóm ≥5)* — khoảng cách với `card1` (97.7%) thực ra là 97.7% vs 91.9%, không phải 80.3%.

### Câu hỏi kiến trúc treo từ diary_v2 — đóng bằng phép đo

diary_v2 §12 nghi ngờ kiến trúc autoencoder `431→20→14→7` (nén 62:1) quá chặt, đề xuất nới lên `431→128→64→32`. Chạy fold 0 cạnh nhau:

| Kiến trúc | AUPRC | CI | Điểm phân biệt |
|---|---:|---|---:|
| `20→14→7` *(hiện tại)* | **0.0389** | [0.0364, 0.0419] | 99.92% |
| `128→64→32` *(đề xuất)* | 0.0343 | [0.0321, 0.0368] | 99.92% |

**Bác bỏ.** Không suy biến, và bản nới còn kém hơn. Chi phí thật ~36s/fold, không phải ~3 giờ như ước lượng.

### Chi tiết cài đặt

- Cửa sổ **nửa mở** `(t − w, t]`, không phải đóng như bản thiết kế viết.
- `searchsorted` trên structured array `(entity, time)` — khóa thực thể là khóa chính nên tự kẹp trong nhóm, không cần clamp thủ công.
- Mọi cột `HIST_` loại trừ chính dòng đang tính (expanding nghiêm ngặt trước).
- Vắng mặt mã hóa hai cách có chủ ý: `DAYS_SINCE_LAST` dùng sentinel 999 (có chiều đúng — "đã rất lâu"), các cột lịch sử khác dùng `NaN` (không có câu trả lời đúng).
- Cửa sổ khai báo bằng **giây thật**, quy đổi qua trường mới `spec.seconds_per_time_unit` — thiếu nó thì dataset tính bằng mili-giây sẽ cho cửa sổ sai 1000 lần mà không báo lỗi.

### Tầng 6 học cách khai báo feature group

Thêm `SentinelModel.feature_groups()` — lý do như `scale_columns`: một tên registry phải định danh một thí nghiệm hoàn chỉnh. `requires_entity=True` giữ các model hành vi ra khỏi `models_for(creditcard)`; thiếu nó chúng sẽ âm thầm rơi về pipeline structural và ghi một record tên `xgboost_behavioral` chứa kết quả `xgboost` thuần.

---

## 4. Bước 6 — Roster hành vi trên IEEE-CIS

### Phán quyết paired test — thí nghiệm #2 đến #5

| # | So sánh | Mean delta | Fold có ý nghĩa | Phán quyết |
|---|---|---:|---|---|
| **2** | `xgboost` → `xgboost_behavioral` | −0.0014 | thắng 0/6, thua 1/6 | **Feature hành vi không giúp** |
| **3** | `xgboost_behavioral` → `_behavioral_only` | −0.4290 | thua **6/6** | Cột thô vẫn thiết yếu |
| **4** | `autoencoder` → `autoencoder_behavioral` | −0.0034 | thắng 2/6, thua 3/6 | Không nhất quán |
| — | `isolation_forest` → `_behavioral` | −0.0140 | thua **6/6** | **Feature hành vi gây hại** |
| **5** | `xgboost_behavioral` → `xgboost_hybrid_behavioral` | −0.0008 | thắng 2/6, thua 1/6 | Tầng bất thường vẫn im lặng |

Bốn phép so đều âm, và không phép nào ngẫu nhiên về hướng — dấu hiệu cho thấy đây là hiệu ứng thật, không phải nhiễu.

### Cơ chế: feature hành vi trùng lặp với feature Vesta có sẵn

Đo tỷ trọng gain XGBoost gán cho 26 cột hành vi: **4.70%** (26/458 cột = 5.68% — dùng ít hơn một cột trung bình). Cột tốt nhất, `HIST_TXN_COUNT`, xếp hạng 79/458. Top-15 cột theo gain chứa `C8`, `C4`, `C12`, `C14` — **nhóm đếm của chính Vesta**, xây cho đúng mục đích mà 26 cột của tôi phục vụ.

Không phải "feature hành vi vô dụng": `xgboost_behavioral_only` đạt 0.1089 với chỉ 26 cột (lift 4.5×) — chúng mang tín hiệu thật, chỉ là tín hiệu đó đã có sẵn trong dataset dưới tên khác.

### Phản biện hiển nhiên đã được kiểm chứng và bác bỏ

Lập luận phản bác tự nhiên: proxy ghép `card1+card2+addr1` **xé lẻ khách hàng thật** (thẻ cấp lại đổi `card2`, chuyển nhà đổi `addr1`), nên feature hành vi đang tính trên lịch sử cụt — kết quả null là lỗi của proxy, không phải bản chất feature.

Kiểm chứng bằng cách thêm spec `ieeecis_card1` (chỉ khác đúng `entity_keys`):

| Proxy | Lịch sử dùng được | `xgboost_behavioral` | so với `xgboost` |
|---|---:|---:|---:|
| `card1+card2+addr1` | 91.9% | 0.5379 | −0.0014 |
| **`card1`** | **97.7%** | **0.5356** | **−0.0037** |

Proxy tốt hơn **không thu hẹp khoảng cách** — thậm chí còn rộng ra chút. Kiểm chứng phụ đắt giá: `xgboost` trên spec card1 cho **0.5393, trùng khít** với ieeecis, đúng như phải thế vì nó không dùng feature thực thể. Điều đó xác nhận hai spec chỉ khác đúng một thứ.

Đây là điều biến "trùng lặp" từ **giả thuyết** thành **lời giải thích còn sống sót**: nó vượt qua được một phép thử trực tiếp có khả năng bác bỏ nó.

Ghi chú kiến trúc: proxy khác được khai báo thành **spec riêng** chứ không phải cờ, vì `entity_keys` thuộc tầng 1. Hệ quả đúng như mong muốn — `processed_dir` và `results_dir` tự tách namespace, hai proxy không thể ghi đè kết quả của nhau.

### Dự đoán B−C bị bác bỏ lần thứ hai

PIPELINE_V2 §7 dự đoán: hiệu số B−C phụ thuộc độ nhiễm, gần 0 trên creditcard (0.17%), rộng trên IEEE-CIS (3.5%). diary_v2 đã bác bỏ nửa đầu (creditcard B−C = +0.1515, không phải ~0). Phiên này bác bỏ nốt nửa sau:

| | creditcard (0.17%) | IEEE-CIS (3.5%) |
|---|---:|---:|
| **B−C** Autoencoder | +0.1515 (B thắng 4/4) | **+0.0015** (không nhất quán) |

Độ nhiễm cao gấp 20 lần lại cho hiệu số gần 0 — ngược dự đoán. Lý do: trên IEEE-CIS autoencoder gần như không hoạt động (lift 3.8× so với 124× trên creditcard). **Một model đã ở gần sàn thì không còn gì để mất.** Rút ra điều kiện chưa từng nêu trong giao thức: báo cáo B−C mà không kèm lift của chính model là báo cáo một tỷ số không diễn giải được.

### Thí nghiệm #6 và #7 — lấp một lỗ hổng giao thức

Rà soát phát hiện creditcard chưa có paired test cho A−B (thí nghiệm #6) — con số `+0.6871` trong diary_v2 chỉ là hiệu hai trung bình, trái nguyên tắc *"bảng xếp hạng không phải kết luận"*. Đã chạy paired test thật: **xgboost thắng isolation_forest 4/4 fold**, +0.6871 (trùng phần trung bình, giờ có CI).

| # | Dataset | So sánh | Mean delta | Fold |
|---|---|---|---:|---|
| 6 | creditcard | isolation_forest → xgboost | +0.6871 | 4/4 |
| 6 | ieeecis | isolation_forest → xgboost | +0.3516 | 6/6 |
| 7 | creditcard | autoencoder → ae_contaminated | −0.1515 | 0/4 |
| 7 | ieeecis | autoencoder → ae_contaminated | +0.0015 | không nhất quán |

---

## 5. Ngoài plan — Tầng tìm kiếm siêu tham số

### Vì sao xây thêm

Kết quả Bước 6 đặt câu hỏi tự nhiên: nếu feature không giúp, hiệu năng còn nằm ở đâu? Câu trả lời: **chưa từng có bước tune siêu tham số nào trong toàn dự án** — mọi cấu hình đặt tay. Bằng chứng có sẵn: `lightgbm_unweighted` 0.5937 so với `xgboost` 0.5393, chênh 10% tương đối chỉ từ một cờ nhị phân.

### Thiết kế: wrapper lồng trong `fit`, không phải script

Một script tune ngoài sẽ chọn tham số trên dữ liệu bao gồm mọi fold đánh giá — lạc quan hóa không kiểm soát được. `TunedModel` đặt phép tìm kiếm **bên trong `fit`**, cắt lát validation nội bộ ở cuối tập train, chấm ứng viên trên đó, rồi refit người thắng trên toàn bộ fold. Cùng lập luận lồng nhau mà `AnomalyAugmentedModel` đã dùng.

Hai hàng rào: model tự từ chối dataset quá mỏng (creditcard ~20 ca dương/lát → từ chối; IEEE-CIS ~590 → chạy), và không bọc được model anomaly (không có mục tiêu AUPRC để tune).

### Kết quả

| Model | AUPRC | so với bản tốt nhất đã biết |
|---|---:|---:|
| **`lightgbm_tuned`** | **0.6096** | +0.0159 (4/6 fold, thua 0) |
| `xgboost_tuned` | 0.5861 | +0.0071 (4/6 fold, thua 0) |

### Bài học phương pháp: baseline sai thổi phồng kết quả

So `xgboost_tuned` với `xgboost` (mặc định lịch sử) cho **+0.0468, 6/6 fold** — nhưng phần lớn khoản đó là tìm lại `balanced=False`, điều **đã biết từ trước**. So với `xgboost_unweighted` (tốt nhất đã biết) chỉ **+0.0071**. Cả hai đúng, nhưng trả lời hai câu hỏi khác nhau; báo cáo một mà giấu cái kia là chọn kết luận trước rồi chọn phép so sau.

### Mặt phản hồi phẳng — phát hiện quan trọng nhất

Kiểm tra 4 seed trên fold lớn nhất: cả bốn dương (+0.0176 đến +0.0249, không phải nhiễu), nhưng chọn **bốn cấu hình rất khác nhau** (`max_depth` 4–8, `learning_rate` 0.02–0.2, `reg_lambda` 0.1–10) cho AUPRC gần như y hệt. Nghĩa là rất nhiều cấu hình tốt ngang nhau — cái quyết định là thoát vùng xấu, không phải tìm điểm tối ưu. Hệ quả: tăng `n_candidates` gần như chắc chắn không đáng (mặt phẳng thì lấy thêm mẫu không tìm được gì hơn); `balanced` là tham số chịu tải duy nhất.

---

## 6. Bước 7 — `pu_cascade`

Model **supervised duy nhất không hề thấy nhãn**: anomaly detector xếp hạng tập train, hai đầu thứ hạng thành nhãn giả, model supervised học từ đó. Baseline đúng là `if_contaminated` (chính detector chấm trực tiếp) — so với model supervised sẽ đo lại ngân sách nhãn, việc tầng 5 đã làm.

### Ba kỹ thuật cố ý không cài đặt

history.md §32 đã xem xét và bác bỏ từng cái:

| Kỹ thuật | Vì sao không |
|---|---|
| Elkan-Noto | Chia hằng số toàn cục → biến đổi đơn điệu → không đổi metric xếp hạng. `min(·,1.0)` thì gây hại: tạo khối điểm trùng ở đỉnh |
| nnPU | Risk estimator cụ thể với class prior. Không cài thì không gọi tên |
| CVuO | Loại mẫu log-loss cao nhất = loại ca khó và giàu thông tin nhất |

### Vòng lặp logic nêu thẳng thành tham số

Thiết kế cũ: `contamination=0.03` → gắn cờ 3% → học 3% → cắt phân vị 97 → lại 3%. Tỷ lệ cảnh báo đi ra vì nó đã đi vào. Ở đây `assumed_positive_rate` là tham số tường minh, mặc định 5% (số vận hành tròn, không lấy từ tỷ lệ quan sát được — tránh nhãn lọt qua cửa sau).

### Thí nghiệm #8: chất lượng nhãn giả đo riêng bằng script

`scripts/pu_diagnostic.py` chấm nhãn giả với nhãn thật — chỉ để đo, không đưa vào bất cứ thứ gì được fit (một model chạm được vào con số đó thì không còn là track C).

| Tỷ lệ giả định | Precision | Recall | Lift |
|---:|---:|---:|---:|
| **5%** *(mặc định)* | **0.217** | **0.310** | 6.2× |

Ở IEEE-CIS: tìm được 31% gian lận thật, nhưng 78% số dòng gắn cờ là sai.

### Kết quả: âm trên cả hai dataset

| Dataset | `if_contaminated` | `pu_cascade` | Mean delta | Fold |
|---|---:|---:|---:|---|
| ieeecis | 0.1956 | 0.1607 | −0.0349 | thắng 1/6, thua 5/6 |
| creditcard | 0.1086 | 0.0343 | **−0.0743** | thắng 0/4, thua 3/4 |

Trên creditcard, tỷ lệ giả định 5% cao gấp ~28 lần tỷ lệ thật (0.19%) → 96.7% nhãn giả sai → precision 0.033 thay vì 0.217. Đáng lưu ý: creditcard có **lift cao hơn** (17.1× so với 6.2×) nhưng model supervised học từ precision tuyệt đối, không phải lift.

**Giới hạn cấu trúc:** cắt ngưỡng để tạo nhãn nhị phân xóa sạch thông tin thứ tự liên tục của điểm anomaly — cascade bắt đầu bằng việc vứt đi phần lớn những gì người thầy biết. Và `assumed_positive_rate` — thứ quyết định phần lớn kết quả — chính là điều **không đo được khi mù nhãn**.

---

## 7. Bước 8 — Tầng 9: drift protocol

### Một nửa phép đo có sẵn miễn phí

PIPELINE_V2 §11 yêu cầu đường cong suy giảm **và** so sánh đóng băng/huấn luyện lại. `run_cv` đã luôn sinh ra arm huấn luyện lại — đó là định nghĩa của cửa sổ mở rộng — nên chỉ cần thêm arm đóng băng. `frozen[0]` và `retrained[0]` huấn luyện trên đúng cùng dòng nên bắt buộc trùng khít — kiểm tra tính đúng đắn miễn phí, `assert_baseline_agrees` cưỡng chế.

### Kết quả ban đầu (2 arm)

| Khối | Đóng băng | Huấn luyện lại | Lời |
|---:|---:|---:|---:|
| 1 | 0.4696 | 0.4696 | +0.0000 |
| 6 | 0.4258 | 0.5457 | **+0.1199** |

Đường cong suy giảm yếu và nhiễu (khối 2 cao hơn khối 1); khoản lời huấn luyện lại đơn điệu tăng.

### Kết luận sai đầu tiên trong phiên

Lập luận: đóng băng chỉ mất 0.0438 trong khi huấn luyện lại mang về 0.1199 → suy giảm giải thích tối đa 37% → phần còn lại là khối lượng dữ liệu (67k → 405k). Kết luận: *"huấn luyện lại có lợi chủ yếu vì thêm dữ liệu, không phải vì chống drift."*

**Sai — xem mục 8.** Lỗi nằm ở so model đóng băng với chính nó ở khối trước, trong khi các khối khác nhau về độ khó nội tại.

---

## 8. Ngoài plan — Cửa sổ trượt và bất biến IV

### Vì sao cần: kết luận ở mục 7 tự nó không tách bạch được

Cửa sổ mở rộng thay đổi **hai thứ cùng lúc** — dữ liệu vừa mới hơn vừa nhiều hơn — nên +0.1199 là hai hiệu ứng trộn lẫn. Thêm arm thứ ba giữ chiều rộng cửa sổ **cố định**:

```
đóng băng   train khối 0       chấm khối i+1    cùng rộng, cũ nhất
trượt       train khối i       chấm khối i+1    cùng rộng, mới nhất
mở rộng     train khối 0..i    chấm khối i+1    rộng nhất
```

`trượt − đóng băng` = độ mới (khối lượng cố định). `mở rộng − trượt` = khối lượng cộng thêm. Hai chi tiết kiểm chứng trên dữ liệu thật: khối validation trùng khít cả 6 fold (cổng tầng 8 vẫn qua), fold 0 trùng khít cả phần train (kiểm tra miễn phí hai cách chia là cùng phân hoạch).

### Kết quả điểm ước lượng: đảo ngược hoàn toàn kết luận ở mục 7

| | Trung bình khối 2–6 |
|---|---:|
| Độ mới | **+0.0765 (82%)** |
| Khối lượng | +0.0168 (18%) |

Ngược hẳn — độ mới mới là yếu tố chính.

### Lỗi tôi tự tạo: vi phạm bất biến IV

Bản đầu của tầng 9 lưu AUPRC nhưng **không lưu điểm số thô** — vi phạm bất biến IV của chính dự án ("điểm số phải sống lâu hơn lần chạy sinh ra nó"). Hệ quả: tỷ lệ 82/18 không thể kiểm định paired mà không tính lại, và tính lại thì chính bất biến đó nói là không tương đương.

**Sửa:** `drift.save_scores()` ghi `decay_scores.npz` cho cả hai arm mới; `drift.paired_decomposition()` bootstrap paired trên cả hai hiệu số, từ chối chạy nếu ba arm không cùng nhãn cho một khối.

### Kết quả paired — và một phát hiện sắc hơn cả tỷ lệ 82/18

| Khối | Độ mới | Khối lượng |
|---:|---|---|
| 2 | +0.0221 [+0.0114,+0.0331] ✓ | +0.0261 [+0.0194,+0.0327] ✓ |
| 6 | +0.1071 [+0.0945,+0.1197] ✓ | +0.0128 [+0.0026,+0.0229] ✓ |
| | **5/5 có ý nghĩa** | 4/5 có ý nghĩa |

Cả hai hiệu ứng đều thật, nhưng CI **chồng lấn ở khối 2** và **tách rời hoàn toàn ở khối 6**. Nhìn theo thời gian: độ mới tăng dần (+0.0221 → +0.1071), khối lượng gần như phẳng (~+0.017).

**Phát biểu đúng không phải "độ mới chiếm 82%"** mà: **cái giá của dữ liệu cũ tăng theo khoảng cách thời gian, lợi ích của tích lũy lịch sử thì không đổi.** Khuyến nghị vận hành: *"nhịp huấn luyện lại càng thưa thì độ mới càng chiếm ưu thế"* — chính sự trì hoãn làm tăng cái giá của trì hoãn.

### Lặp lại trên nhà vô địch — kết luận tổng quát hóa, kèm một cảnh báo mới

Phép đo trên chỉ chạy với `xgboost`, model không còn là vô địch. Chạy lại toàn bộ ba arm với `lightgbm_tuned`:

| | `xgboost` | `lightgbm_tuned` |
|---|---:|---:|
| Suy giảm khi đóng băng | −9.3% | **−15.9%** |
| Giá trị huấn luyện lại | +0.0777 | **+0.1050** |
| Độ mới / khối lượng | 82% / 18% | **75% / 25%** |
| Có ý nghĩa | 5/5 · 4/5 | 5/5 · 4/5 |

Kết luận **tổng quát hóa** — cùng hình dạng, cùng mức ý nghĩa, trên hai họ model độc lập. Đó chính là điều cần kiểm tra.

Nhưng kèm một phát hiện ngoài dự kiến: **model được tune tốt hơn mất giá nhanh gần gấp đôi khi để yên.** Cơ chế hợp lý và đáng lo: tune *chính là* việc khớp chặt hơn vào phân bố huấn luyện — khớp càng chặt thì phân bố trôi đi càng đau.

Hệ quả định lượng được:

```
Khối 6, mở rộng  : lightgbm_tuned 0.6359  vs  xgboost 0.5457   cách biệt +0.0902
Khối 6, đóng băng: lightgbm_tuned 0.4607  vs  xgboost 0.4258   cách biệt +0.0349
```

**Đóng băng bào mòn 61% lợi thế của tune.** Khoản lời +0.0159 từ tune vì thế là **có điều kiện** — nó chỉ giữ được nếu model được huấn luyện lại đều. Tune rồi để yên có thể trả lại nhiều hơn phần đã được.

Đây là một liên kết giữa hai kết quả tưởng như độc lập (tune và drift) mà không phép đo đơn lẻ nào phát hiện được — chỉ lộ ra khi chạy phép đo drift trên đúng model đang thắng.

### Quét chiều rộng cửa sổ — câu hỏi vận hành mà phép phân tách bỏ ngỏ

`train_blocks=1` là giá trị **buộc phải dùng** cho phép phân tách (phải khớp chiều rộng arm đóng băng để khối lượng cố định). Nó trả lời *"độ mới đóng góp bao nhiêu"* nhưng không trả lời *"nên giữ bao nhiêu lịch sử"* — hai điểm đã đo là hai cực, hình dạng ở giữa chưa biết.

`scripts/window_sweep.py` quét khoảng đó:

| Chiều rộng | AUPRC | so với mở rộng | Dòng train | % dữ liệu | Paired (khối cuối) |
|---:|---:|---:|---:|---:|---|
| 1 | 0.5253 | −0.0140 | 67,490 | 17% | −0.0128 **có ý nghĩa (tệ hơn)** |
| **2** | 0.5409 | +0.0016 | 134,980 | **33%** | +0.0026 (CI chứa 0) |
| 3 | 0.5414 | +0.0021 | 202,471 | 50% | +0.0107 * |
| 4 | 0.5397 | +0.0003 | 269,961 | 67% | +0.0016 (CI chứa 0) |
| 5 | 0.5414 | +0.0021 | 337,451 | 83% | +0.0127 * |

**Đường cong bão hòa ngay ở width=2.** Từ 2 đến 5, AUPRC nằm gọn trong 0.5397–0.5414 — chênh không đáng kể và **không đơn điệu**. Chỉ width=1 là tệ hơn có ý nghĩa.

Hai dấu `*` ở width 3 và 5 nói "tốt hơn mở rộng có ý nghĩa", nhưng width 4 nằm giữa lại không. Hoa văn không đơn điệu đó là dấu hiệu **nhiễu**, không phải hiệu ứng — ghi nhận theo hình dạng chung, không theo từng dấu sao lẻ.

**Sửa lại một phát biểu trước đó.** Kết quả cửa sổ trượt ban đầu được tóm tắt là *"bỏ 5/6 lịch sử, mất 2.3% tương đối"* — đúng về số nhưng chọn nhầm điểm vận hành, vì width=1 chính là điểm **duy nhất** tệ hơn có ý nghĩa. Phát biểu đúng: **giữ ~2 khối (60 ngày, 33% dữ liệu) là đủ; 67% lịch sử còn lại không mua được gì đo được** — chi phí huấn luyện giảm 3× mà không mất gì.

### Bài học phương pháp kép

So một model với **chính nó ở thời điểm khác** không tách được model đổi khỏi bài toán đổi — phải so **hai model trên cùng một khối**. Đây chính là nguyên tắc paired-comparison của tầng 8, áp theo trục thời gian, và tôi đã bỏ qua nó ở lần đo đầu.

Hệ quả: phán quyết bác bỏ EWC ở PIPELINE_V2 §11 **không còn được củng cố** bởi lập luận "vấn đề là khối lượng" (đã bác bỏ) — nhưng 4 lý do gốc khác vẫn đứng, đặc biệt lý do #5 ("trong gian lận, quên đôi khi là đúng") giờ được kết quả này **ủng hộ trực tiếp**.

---

## 9. Bước 9 — Tầng 10: explanation

Đóng nốt nguyên tắc thiết kế #5 của dự án. Hai điểm cài đặt khác bản thiết kế, cả hai có chủ ý.

### 1. Counterfactual tính lại qua pipeline, không dựng lại bằng công thức

PIPELINE_V2 §12 liệt kê từng công thức lan truyền. Lập luận đúng, nhưng thay vì viết lại công thức, cài đặt **nhiễu loạn cột thô rồi chạy lại chính feature pipeline**: chính xác tuyệt đối, không thể lệch pha khi thêm nhóm feature mới, và lan truyền xa hơn công thức (đổi số tiền một giao dịch cũng đổi lịch sử các giao dịch *sau đó* của cùng thực thể).

Kiểm chứng trên dữ liệu thật: đổi một ô `TransactionAmt` làm 9 cột dịch chuyển; `VELOCITY_COUNT_*` đứng yên đúng như toán học đòi hỏi (đếm giao dịch, không phụ thuộc số tiền).

### 2. TreeSHAP lấy thẳng từ booster

XGBoost và LightGBM đều đã cài TreeSHAP nội bộ — bọc thêm gói `shap` là thêm dependency mà không thêm độ chính xác. Đóng góp ở không gian margin, cộng tính được, `check_additivity()` cưỡng chế `bias + Σ đóng góp == margin`.

`spec.mutable_columns` chặn đề xuất trên cột bất biến (mặc định: riêng số tiền) — trên hai dataset này không phải hạn chế mà đọc đúng thực tế: IEEE-CIS ẩn danh, `V1`-`V28` của creditcard là PCA.

### Bài học hiệu năng: phải cắt cả hai nửa

Lần chạy đầu không xong sau 10 phút — cắt frame về riêng thực thể chưa đủ, vì **lịch sử lưu trong pipeline vẫn là toàn bộ dữ liệu train**. Thêm `FeaturePipeline.narrowed_to(entities)` cắt cả state lưu trong nhóm hành vi, đưa thời gian từ hàng chục phút xuống vài giây. Có test riêng khẳng định frame hẹp cho feature giống hệt frame đầy đủ.

### Kết quả trên dữ liệu thật — kỳ vọng thứ tư bị bác bỏ

4 cảnh báo cao nhất của `xgboost_behavioral`, tất cả đúng là gian lận. Nhưng **không cột hành vi nào lọt top-3** của bất kỳ cảnh báo nào (luôn là `C1`, `C8`, `V258` — khớp phép đo feature importance ở mục 4), và cả 4 đều **unreachable** — không giá trị `TransactionAmt` nào đưa điểm xuống dưới ngưỡng.

PIPELINE_V2 §12 kỳ vọng ngược lại (*"`AMOUNT_Z_SCORE = 40` dịch trực tiếp thành..."*). Không xảy ra — giải thích vẫn nằm trong ngôn ngữ feature ẩn danh. Nhưng "unreachable" tự nó là đầu ra có giá trị: *"không có gì bạn làm được để tránh cảnh báo này"* là câu trả lời trung thực hơn một con số bịa ra.

---

## 10. Ngoài plan — Năm phép đo củng cố

Sau khi hoàn tất Bước 9, phần rà soát tồn đọng liệt kê năm việc "rẻ, nên làm". Tiêu chí chọn không phải "cho đủ" mà: **mỗi việc phải thách thức hoặc làm rõ một kết luận đã báo cáo**. Cả năm đều đạt tiêu chí đó — hai việc **sửa** phát biểu sai, một **củng cố** kết luận cũ trước phản biện, một **xác nhận**, một cho **kết quả âm** phá vỡ một khái quát hóa vội vàng.

### 10.1 Đường cong suy giảm cho nhà vô địch — liên kết hai kết quả tưởng như rời rạc

Kết quả drift ở mục 8 chỉ đo trên `xgboost`, model không còn là vô địch. Chạy lại toàn bộ ba arm với `lightgbm_tuned`:

| | `xgboost` | `lightgbm_tuned` |
|---|---:|---:|
| Suy giảm khi đóng băng | −9.3% | **−15.9%** |
| Giá trị huấn luyện lại | +0.0777 | **+0.1050** |
| Độ mới / khối lượng | 82% / 18% | **75% / 25%** |
| Có ý nghĩa | 5/5 · 4/5 | 5/5 · 4/5 |

Hình dạng **tổng quát hóa** — cùng kết luận, cùng mức ý nghĩa, trên hai họ model độc lập. Đó là điều cần kiểm tra.

Nhưng kèm một phát hiện ngoài kỳ vọng: **model tune tốt hơn mất giá nhanh gần gấp đôi khi để yên.** Cơ chế hợp lý — tune *chính là* việc khớp chặt hơn vào phân bố huấn luyện, nên phân bố trôi đi thì mất mát càng lớn.

```
Khối 6, mở rộng  : lightgbm_tuned 0.6359  vs  xgboost 0.5457   cách biệt +0.0902
Khối 6, đóng băng: lightgbm_tuned 0.4607  vs  xgboost 0.4258   cách biệt +0.0349
```

**Đóng băng bào mòn 61% lợi thế của tune.** Khoản lời +0.0159 vì thế là **có điều kiện** — nó chỉ giữ được nếu model được huấn luyện lại đều.

Đây là liên kết giữa hai kết quả trước đó tưởng như độc lập (tune và drift). Không phép đo đơn lẻ nào phát hiện được — chỉ lộ ra khi chạy drift trên đúng model đang thắng.

### 10.2 Proxy thực thể `card1` — phản biện được kiểm chứng và bác bỏ

Kết luận "feature hành vi trùng lặp với `C1`–`C14` của Vesta" (mục 4) có một phản biện hiển nhiên: proxy ghép `card1+card2+addr1` **xé lẻ khách hàng thật** — thẻ cấp lại đổi `card2`, chuyển nhà đổi `addr1` — nên feature hành vi đang tính trên lịch sử cụt. Kết quả null có thể là lỗi của proxy, không phải bản chất feature.

Kiểm chứng bằng spec thứ ba `ieeecis_card1`, chỉ khác đúng `entity_keys`:

| Proxy | Lịch sử dùng được | `xgboost_behavioral` | so với `xgboost` | Fold |
|---|---:|---:|---:|---|
| `card1+card2+addr1` | 91.9% | 0.5379 | −0.0014 | thua 1/6 |
| **`card1`** | **97.7%** | **0.5356** | **−0.0037** | **thua 2/6** |

Proxy tốt hơn **không thu hẹp khoảng cách** — còn rộng ra. Kiểm chứng phụ đắt giá: `xgboost` trên spec mới cho **0.5393 trùng khít** với ieeecis, đúng như phải thế vì nó không dùng feature thực thể — xác nhận hai spec chỉ khác đúng một thứ.

Đây là điều biến "trùng lặp" từ **giả thuyết** thành **lời giải thích còn sống sót**: nó vượt qua một phép thử được thiết kế để bác bỏ nó.

**Ghi chú kiến trúc:** proxy khác được khai báo thành **spec riêng** chứ không phải cờ, vì `entity_keys` thuộc tầng 1. Hệ quả đúng như mong muốn — `processed_dir` và `results_dir` tự tách namespace, hai proxy không thể ghi đè kết quả của nhau. Split của spec mới **trùng khít từng con số** với ieeecis (cắt theo thời gian, không liên quan thực thể) — một kiểm chứng miễn phí nữa.

### 10.3 Tune `logreg` — kết quả âm phá vỡ một khái quát hóa

Kỳ vọng: logistic regression cũng hưởng lợi từ tune như hai họ boosting (+0.0071 và +0.0159).

**Không đạt.** Sau khi sửa hai lỗi (xem 10.3.1), kết quả cuối:

| Model | AUPRC | so với bản tốt nhất đã biết | Fold |
|---|---:|---:|---|
| `xgboost_tuned` | 0.5861 | +0.0071 | 4/6 thắng, 0 thua |
| `lightgbm_tuned` | 0.6096 | +0.0159 | 4/6 thắng, 0 thua |
| **`logreg_tuned`** | **0.2009** | **+0.0003** | **2 thắng, 2 thua — nhiễu** |

Trace fold cuối giải thích vì sao:

```
0.1977  {C: 0.1,   class_weight: balanced}   ← thắng
0.1959  {C: 10.0,  class_weight: balanced}
0.1956  {C: 1.0,   class_weight: balanced}   ← chính là logreg_full_scale
0.1945  {C: 0.01,  class_weight: balanced}
0.1942  {C: 100.0, class_weight: balanced}
```

`C` dao động **0.0035 qua bốn bậc độ lớn** — gần như phẳng tuyệt đối. Tham số duy nhất mang tín hiệu là `class_weight`, mà giá trị thắng của nó (`balanced`) **đã** là mặc định của `logreg_full_scale`.

**Bài học:** không gian tìm kiếm của model tuyến tính không có bậc tự do tương tác — không `max_depth`, `subsample`, `colsample_bytree` để phối hợp. Kết quả này ngăn khái quát hóa *"tune luôn có lợi"* từ 2/2 mẫu boosting. Sự thật hẹp hơn: **tune có lợi khi model có đủ không gian siêu tham số tương tác được.**

#### 10.3.1 Hai lỗi trong chính không gian tìm kiếm tôi vừa viết

Phải chạy ba lần mới ra kết quả hợp lệ. Hai lỗi độc lập, **cả hai đều chặn search khỏi cấu hình tốt nhất đã biết**.

**Lỗi 1 — một chiều tìm kiếm vô hiệu.** Tôi đưa `scale_columns` vào `LOGREG_SPACE`. Nhưng runner áp preprocessing ở dòng 168, **trước** khi gọi `model.fit` ở dòng 185, và dùng `scale_columns` của TunedModel **bên ngoài**. Giá trị ứng viên khai báo được set rồi **không bao giờ được đọc**.

Bằng chứng nằm ngay trong trace, chỉ lộ ra khi nhìn kỹ:

```
0.2087  {C: 10,     class_weight: None, scale_columns: 'all'}
0.2087  {C: 10,     class_weight: None, scale_columns: 'default'}   ← giống hệt
0.2052  {C: 0.0001, class_weight: None, scale_columns: 'all'}
0.2052  {C: 0.0001, class_weight: None, scale_columns: 'default'}   ← giống hệt
```

8 lượt bốc chỉ khám phá **5 cấu hình khác nhau**. Đây đúng loại no-op âm thầm mà codebase đã có tiền lệ chống (`__init_subclass__` từ chối khai báo `trains_on_normal_only` chết) — tôi tạo ra đúng loại lỗi đó ở chỗ khác.

**Lỗi 2 — bản sửa chưa đủ.** Bỏ `scale_columns` khỏi không gian chỉ làm giới hạn *tường minh*, không gỡ nó: `TunedModel` **kế thừa** `scale_columns` từ prototype, mà prototype là `LogisticRegressionBaseline()` mặc định → `"default"`. Nên search bị **khóa cứng ở cách scale kém hơn** (đã biết thua 0.0107), và vẫn không thể diễn đạt `logreg_full_scale`.

Phát hiện lỗi 2 **chỉ vì người dùng hỏi** *"tune logreg không có tác dụng?"* — tôi đi kiểm tra để trả lời thì thấy `scale_columns = default`. Nếu không, job 4 tiếng đã chạy xong và tôi đã báo cáo kết quả sai lần thứ hai.

**Hàng rào đã dựng:**
- `INERT_IN_SEARCH` — `TuningError` raise ngay lúc dựng nếu không gian chứa tham số tầng-7, kèm thông báo chỉ đúng cách thay thế
- Factory của `logreg_tuned` **pin cứng** `scale_columns="all"`
- Test khẳng định không gian **chứa được bản đương nhiệm** — thứ đáng lẽ phải có ngay từ đầu
- Chuyển sang **quét vét cạn 14 điểm** thay vì lấy mẫu: không gian nhỏ thế này thì lấy mẫu chỉ tạo thêm nghi ngờ

### 10.4 `explain_alerts` trên creditcard — kỳ vọng đầu tiên được xác nhận

PIPELINE_V2 §12 khẳng định: *"với `V1`–`V28` là PCA ẩn danh, SHAP chỉ nói được feature nào quan trọng, không dịch được sang ngôn ngữ nghiệp vụ"*. Đây là khẳng định **chưa kiểm chứng bằng dữ liệu thật** — giống hệt tình huống trước khi chạy trên IEEE-CIS, khi tài liệu cũng khẳng định một điều và đo ra sai.

**Đạt kỳ vọng — lần đầu tiên trong dự án một khẳng định trong tài liệu được đo ra đúng.**

```
alert 1  score 1.0000  FRAUD   V14=-7.463 (+3.952)  V10=-6.541 (+1.521)  V12=-4.938 (+1.510)
alert 2  score 1.0000  FRAUD   V14=-8.894 (+4.035)  V10=-4.401 (+1.528)  V12=-5.738 (+1.524)
```

5/5 cảnh báo đúng là gian lận. `V14` đóng góp +3.95, gấp 2.6 lần cột thứ hai, nhất quán ở cả 5 — tín hiệu rất mạnh nhưng hoàn toàn vô nghĩa về nghiệp vụ.

**Phát hiện ngoài kỳ vọng:** cả 5 đều **unreachable** — không giá trị `Amount` nào đưa điểm xuống dưới ngưỡng. Cộng với 4/4 unreachable trên IEEE-CIS, đây **không phải giới hạn riêng của creditcard** như tài liệu ngụ ý mà là **giới hạn chung của cả hai dataset**: không dataset nào cho phép counterfactual hành động được.

### 10.5 Quét chiều rộng cửa sổ — sửa lại một điểm vận hành

*(Chi tiết ở mục 8; tóm tắt ở đây cho đủ năm việc.)* `train_blocks=1` là giá trị **buộc phải dùng** cho phép phân tách, nhưng không phải điểm vận hành nên chọn. Quét cho thấy đường cong **bão hòa ngay ở width=2** (33% dữ liệu, tương đương mở rộng), trong khi **width=1 là điểm duy nhất tệ hơn có ý nghĩa**. Phát biểu *"bỏ 5/6 lịch sử, mất 2.3%"* đúng về số nhưng chọn nhầm điểm; đúng hơn là **"giữ ~2 khối là đủ"**.

---

## 11. Bảng kết quả đầy đủ — IEEE-CIS

| Model | Track | AUPRC | Ghi chú |
|---|:---:|---:|---|
| **`lightgbm_tuned`** | A | **0.6096** | Vô địch. Nhưng suy giảm −15.9% nếu đóng băng (mục 10.1) |
| `lightgbm_unweighted` | A | 0.5937 | |
| `xgboost_tuned` | A | 0.5861 | |
| `xgboost_unweighted` | A | 0.5790 | |
| `lightgbm` | A | 0.5662 | |
| `xgboost_hybrid_iforest` | A | 0.5408 | |
| `xgboost` | A | 0.5393 | Baseline gốc, mốc neo mọi so sánh cũ |
| `xgboost_hybrid` | A | 0.5389 | Tầng bất thường: null |
| `xgboost_behavioral` | A | 0.5379 | Feature hành vi: null |
| `xgboost_hybrid_behavioral` | A | 0.5371 | |
| `logreg_tuned` | A | 0.2009 | Tune: **null** (2 thắng 2 thua) |
| `logreg_full_scale` | A | 0.2006 | |
| `if_contaminated` | C | 0.1956 | |
| `logreg` | A | 0.1899 | |
| `isolation_forest` | B | 0.1877 | |
| `isolation_forest_behavioral` | B | 0.1737 | Feature hành vi: **hại** (thua 6/6) |
| `pu_cascade` | C | 0.1607 | Thua chính detector nó học từ đó |
| `xgboost_behavioral_only` | A | 0.1089 | 26 cột, lift 4.5× |
| `ae_contaminated` | C | 0.0937 | |
| `autoencoder` | B | 0.0922 | Đảo chiều so với creditcard |
| `autoencoder_behavioral` | B | 0.0888 | |
| `autoencoder_minimal_scale` | B | 0.0778 | |

Trên `ieeecis_card1` (proxy thay thế): `xgboost` 0.5393 (trùng khít), `xgboost_behavioral` 0.5356.

### Ba đảo chiều so với creditcard

Autoencoder và Isolation Forest **đổi chỗ**: trên creditcard AE thắng IF 2.4×; trên IEEE-CIS IF thắng AE 2.0×. Tầng bất thường vẫn không đóng góp gì trên cả hai dataset, dù IEEE-CIS có 42× nhiều gian lận hơn.

---

## 12. Năm kỳ vọng trong tài liệu — bốn sai, một đúng

Xuyên suốt phiên, năm điều PIPELINE_V2 hoặc diary_v2 khẳng định đã được đem ra đo:

| # | Kỳ vọng | Kết quả |
|---|---|---|
| 1 | **§7** — B−C phụ thuộc độ nhiễm (rộng ra khi nhiễm cao) | ❌ Ngược hoàn toàn: gần 0 ở nhiễm 3.5%, rộng ở nhiễm 0.17% |
| 2 | **Bảng proxy thực thể** trong diary_v2 | ❌ Sai vì lỗi `entity_id` (mục 3) |
| 3 | **"Khối lượng chiếm ưu thế"** trong drift | ❌ Kết luận tự đưa ra trong phiên, bị chính cửa sổ trượt bác bỏ |
| 4 | **§12** — `AMOUNT_Z_SCORE=40` dịch trực tiếp thành lời giải thích | ❌ 0/4 cảnh báo hàng đầu dùng feature hành vi |
| 5 | **§12** — PCA ẩn danh của creditcard không dịch được sang nghiệp vụ | ✅ **Đúng** — nhưng hóa ra là giới hạn của *cả hai* dataset |

Bốn cái sai đều bị bác bỏ bằng **phép đo có kiểm định** (paired bootstrap hoặc đối chiếu độc lập), không phải bằng trực giác. Cái đúng duy nhất cũng được xác nhận theo cách đó, và còn phát hiện thêm rằng phạm vi của nó rộng hơn tài liệu ghi.

Điểm đáng rút ra: tỷ lệ 4/5 sai không nói rằng tài liệu thiết kế tệ — nó nói rằng **một khẳng định nghe hợp lý vẫn cần được đo**, và dự án này có đủ hạ tầng để đo chúng rẻ.

---

## 13. Lỗi của tôi trong phiên

Năm lỗi, chia ba loại. Tất cả đều được sửa trong chính phiên và có test hoặc hàng rào ngăn tái diễn.

### Vận hành

Kết luận một job nền đã chết vì **file output rỗng** — thực ra chỉ bị buffer. Khởi động lại thành 3 job nặng song song, gây `MemoryError` khi `IsolationForest` ép DataFrame 431 cột thành mảng đặc >1GB. Job gốc vẫn chạy trọn; `autoencoder_behavioral` phải chạy lại một mình.

**Bài học:** kiểm tra **tiến trình** (CPU/memory), không kiểm tra kích thước file output. Áp dụng lại đúng bài học này về sau khi kiểm tra RAM trước mỗi lần xếp job (mục 10) — và nó đã ngăn được lỗi thứ hai cùng loại.

### Suy luận

**So model với chính nó ở thời điểm khác** (mục 7–8), trộn lẫn "model đổi" với "bài toán đổi" vì các khối thời gian khác nhau về độ khó nội tại. Phát biểu kết luận dù **đã tự ghi giới hạn vào docstring** — ghi nhận một giới hạn không làm nó biến mất. Sửa bằng cách so hai arm **trên cùng một khối**, đúng nguyên tắc paired-comparison mà tầng 8 của chính dự án đã dựng lên.

### Kiến trúc

**Vi phạm bất biến IV** (mục 8): tầng 9 lưu kết quả tổng hợp mà không lưu điểm số thô, khiến một kết luận vừa báo cáo không thể kiểm định lại mà không tính lại — chính điều bất biến đó cấm. Phát hiện khi tự hỏi *"con số 82/18 này có kiểm định được không"*.

**Hai lỗi trong không gian tìm kiếm `logreg`** (mục 10.3.1): một chiều tìm kiếm vô hiệu, rồi bản sửa vẫn khóa search khỏi cấu hình tốt nhất. Cả hai đều **không raise, không để lại dấu vết trong output** — chỉ lộ ra khi đọc kỹ search trace và khi đi kiểm tra để trả lời một câu hỏi.

### Hoa văn chung

Bốn trong năm lỗi thuộc cùng một loại: **thứ gì đó im lặng không hoạt động**, và output trông vẫn hợp lý. Đó chính xác là loại lỗi mà kiến trúc của dự án đã dựng nhiều hàng rào để chống (`__init_subclass__` từ chối khai báo chết, `score_resolution_warning`, cổng "cùng những dòng" của tầng 8). Tôi tạo ra đúng loại lỗi đó ở những chỗ chưa có hàng rào — và đã bổ sung hàng rào cho từng chỗ.

---

## 14. Việc chưa làm / cần làm / nên làm

### Cần làm — có tác động thật, chi phí thấp

| # | Việc | Vì sao cần |
|---|---|---|
| 1 | **README sai 5 chỗ** | Roadmap trình bày Phase 0–1 như việc tương lai dù đã xong; trạng thái dự án, phần dataset và cấu trúc repo đều lỗi thời; còn một dòng `# sentinel` thừa. Là thứ đầu tiên ai cũng đọc |
| 2 | **Toàn bộ phiên chưa commit** | `src/` `tests/` `scripts/` `experiments/` và cả `diary_v3.md` đang untracked. 11,204 dòng và 380 test không được version control — rủi ro mất việc nếu có sự cố |

Về #2, có một chi tiết đã rà: `.gitignore` chặn `/experiments/results` nhưng **không chặn** `experiments/results_pre_refactor/` (13MB snapshot golden reference). Cần thêm dòng đó trước khi commit, nếu không nó sẽ vô tình lên remote.

### Nên làm — rẻ, có giá trị đo được

| # | Việc | Chi phí |
|---|---|---|
| 3 | Đường cong suy giảm cho `ieeecis_card1` — proxy mới chưa có phép đo drift nào | 1 lệnh |
| 4 | `explain_alerts` cho `lightgbm_tuned` (mới có `xgboost` và `xgboost_behavioral`) | 1 lệnh |
| 5 | Quét `train_blocks` cho `lightgbm_tuned` — vô địch suy giảm nhanh hơn, điểm bão hòa có thể khác | 1 lệnh |

### Cân nhắc — mở rộng phạm vi, cần quyết định trước khi làm

| # | Việc | Vì sao chưa làm |
|---|---|---|
| 6 | **`PartialLabel`** — trả lời "cần gán nhãn bao nhiêu % thì đủ" | Đã cài + test cơ chế nhưng **không đăng ký ở đâu** (code chết). Không nằm trong plan 10 bước; cần trục quét `reveal_fraction` — hạ tầng cho một chuỗi thí nghiệm, không phải một entry registry. Có giá trị vận hành thật nhưng là thí nghiệm mới |
| 7 | Early stopping trong tầng tune | Lát validation nội bộ đã tường minh nên lý do cũ để tránh không còn. Cần phép đo riêng cho việc chọn số cây lúc refit. Sẽ cắt mạnh chi phí — đặc biệt cho `logreg_tuned`, entry đắt nhất registry (~4 giờ) |

### Không cần làm — đã trả lời bằng phép đo trong phiên

- **Tăng `n_candidates`** — mặt phản hồi phẳng, đo qua 4 seed: bốn cấu hình rất khác nhau cho AUPRC gần y hệt.
- **Nới kiến trúc autoencoder** — bản `128→64→32` **kém hơn** bản `20→14→7`.
- **Đổi proxy sang `card1`** — đã làm (mục 10.2), không cứu được feature hành vi.
- **Tune `logreg`** — đã làm (mục 10.3), kết quả null.
- **Quét `train_blocks`** — đã làm, bão hòa ở width=2.

### Ba việc nên làm cho Phase tiếp theo

Từ kết quả phiên này, ba hướng có cơ sở thực nghiệm:

1. **Nhịp huấn luyện lại là đòn bẩy lớn nhất chưa khai thác.** Đo được: độ mới chiếm 75–82% giá trị của việc huấn luyện lại, và đóng băng bào mòn 61% lợi thế của tune. Chưa có thí nghiệm nào đo *tần suất* tối ưu.
2. **Feature hành vi trên dataset không có sẵn nhóm đếm.** Kết luận "trùng lặp" gắn chặt với việc IEEE-CIS đã có `C1`–`C14`. Nó **không** nói gì về giá trị của feature hành vi nói chung — mà đó chính là điều Sentinel cần biết cho các lĩnh vực khác.
3. **Tầng bất thường vẫn chưa đóng góp gì** sau ba lần đo trên hai dataset. Trước khi đầu tư thêm vào Phase 2 (quantum), nên trả lời: tầng này cần điều kiện gì để có ích, hay tiền đề "học cái bình thường trước" sai với bài toán gian lận có nhãn?

### Ràng buộc phải giữ ở mọi thay đổi tiếp theo

> `verify_migration.py` phải giữ **12/12**. `xgboost` trên creditcard phải vẫn cho `0.7741` với per-fold `[0.8168, 0.6668, 0.8213, 0.7916]`.

---

## Phụ lục — Lệnh

```bash
# Roster hành vi (IEEE-CIS)
uv run python scripts/run_experiment.py --dataset ieeecis --model xgboost_behavioral

# Tune
uv run python scripts/run_experiment.py --dataset ieeecis --model xgboost_tuned

# PU cascade — chẩn đoán chất lượng nhãn giả trước khi chạy model
uv run python scripts/pu_diagnostic.py --dataset ieeecis
uv run python scripts/run_experiment.py --dataset ieeecis --model pu_cascade

# Drift — 3 arm + phân tách paired
uv run python scripts/drift_experiment.py --dataset ieeecis --model xgboost

# Explanation — top cảnh báo, attribution + counterfactual
uv run python scripts/explain_alerts.py --dataset ieeecis --model xgboost_behavioral --top 5

# Quét chiều rộng cửa sổ trượt — câu hỏi vận hành
uv run python scripts/window_sweep.py --dataset ieeecis --model xgboost

# Proxy thực thể thay thế (spec thứ ba)
uv run python scripts/build_splits.py --dataset ieeecis_card1
uv run python scripts/run_experiment.py --dataset ieeecis_card1 --model xgboost_behavioral

# Paired test — thứ quyết định, không phải bảng xếp hạng
uv run python scripts/compare_models.py --dataset ieeecis xgboost xgboost_tuned

# Ràng buộc di trú — chạy sau MỌI thay đổi tầng 1-3
uv run python scripts/verify_migration.py

uv run pytest          # 380 test
```

### Cây thư mục mới trong phiên

```text
src/datasets/ieeecis.py        + IEEECIS_CARD1 (spec thứ ba, proxy thay thế)
src/data/splitter.py           + sliding_window_folds
src/features/behavioral.py     RollingWindows · VelocityRatios · EntityHistory · BenfordDeviation
src/models/behavioral.py       5 model hành vi
src/models/tuning.py           TunedModel · 3 không gian tìm kiếm · INERT_IN_SEARCH
src/models/pu.py               PUCascade
src/evaluation/drift.py        decay_curve · sliding_curve · decompose · paired_decomposition
src/evaluation/explain.py      explain · counterfactual · narrowed_to
scripts/pu_diagnostic.py
scripts/drift_experiment.py
scripts/explain_alerts.py
scripts/window_sweep.py

experiments/results/*/*/decay.json           đường cong suy giảm + phân tách paired
experiments/results/*/*/decay_scores.npz     điểm thô 2 arm mới (bất biến IV)
experiments/results/*/*/explanations.json    attribution + counterfactual
experiments/results/*/*/window_sweep.json    quét chiều rộng cửa sổ
datasets/processed/ieeecis_card1/            split cho spec thứ ba
```

---

## Tổng kết một dòng

Phiên này hoàn tất **Bước 5 → 9** của plan, thêm **ba hạng mục ngoài plan**, và đo được **10/10 thí nghiệm** trong chương trình nghiên cứu. Kết quả nổi bật: `lightgbm_tuned` 0.6096 là vô địch mới, nhưng **lợi ích của tune có điều kiện vào nhịp huấn luyện lại** (đóng băng bào mòn 61%). Ba hướng cải thiện được thử — feature hành vi, tầng bất thường, PU cascade — **đều cho kết quả âm có kiểm định**, và mỗi cái đều kèm cơ chế giải thích. Năm lỗi của tôi được tìm ra và sửa, bốn trong số đó thuộc cùng một loại: **thứ gì đó im lặng không hoạt động trong khi output trông vẫn hợp lý.**
```
