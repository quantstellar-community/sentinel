# Evaluation Protocol — Phase 0

> Hợp đồng nghiên cứu (research contract) của Sentinel. Mọi kết quả được báo cáo trong dự án phải tuân theo tài liệu này. Code thực thi nằm ở [src/](../src/); tài liệu này giải thích **tại sao**.

Phase 0 không tạo ra model. Nó tạo ra **thước đo** — và khóa thước đo lại trước khi bất kỳ model nào được huấn luyện. Lý do nằm ở một con số: sau khi cắt theo thời gian, tập holdout chỉ còn **74 ca gian lận**. Ở cỡ mẫu đó, chênh lệch AUPRC vài phần trăm là nhiễu lấy mẫu. Nếu thước đo được dựng sau khi đã nhìn thấy kết quả model, không cách nào phân biệt được "cải thiện thật" với "chọn được split may mắn".

---

## 1. Data contract

| Quyết định | Giá trị | Lý do |
|---|---|---|
| Nguồn | `datasets/creditcard.csv` | SHA-256 được ghi vào split manifest mỗi lần build |
| Duplicates | **Xóa toàn bộ 1,081 dòng** (19 fraud) | Xem bên dưới |
| Schema | 31 cột, đúng thứ tự, 0 null | [loader.py](../src/data/loader.py) raise `DataContractError` nếu lệch |
| Sau xử lý | 283,726 dòng, 473 fraud (0.16671%) | |

**Vì sao xóa duplicates.** Một dòng trùng lặp nằm trong test set được chấm điểm hai lần, thổi phồng mọi metric. Nghiêm trọng hơn: một cặp trùng lặp nằm hai bên ranh giới split là rò rỉ trực tiếp — model đã thấy đúng dòng đó khi train. 19/492 ca fraud (3.9%) bị ảnh hưởng, đủ lớn để không bỏ qua.

Có thể giữ lại bằng `--keep-duplicates` để so sánh, nhưng kết quả báo cáo mặc định luôn là bản đã xóa.

> [!IMPORTANT]
> Các số liệu thống kê trong [dataset_field_documentation.md](dataset_field_documentation.md) được tính trên file **gốc còn duplicates**. [notebooks/01_eda.ipynb](../notebooks/01_eda.ipynb) kiểm tra lại toàn bộ 23 con số đó — hiện tại **23/23 khớp tuyệt đối**.

---

## 2. Split protocol

### 2.1 Cắt theo *giá trị* `Time`, không theo vị trí dòng

284,807 dòng chỉ có 124,592 mốc thời gian phân biệt. Cắt theo vị trí dòng (`df.iloc[:227000]`) sẽ đẩy các giao dịch **ghi cùng một giây** sang hai phía của ranh giới — model được train trên một nửa của một khoảnh khắc và test trên nửa còn lại.

`find_cut_time()` chọn một mốc thời gian có thật, rồi `train = Time <= cut`, `test = Time > cut`. Cách này đảm bảo mọi dòng cùng timestamp luôn nằm cùng một phía. Cái giá phải trả: tỷ lệ thực tế lệch nhẹ so với tỷ lệ yêu cầu.

### 2.2 Holdout bị khóa

20% thời gian cuối cùng được tách ra và **chỉ chấm một lần mỗi phase**. Mọi quyết định — chọn feature, hyperparameter, threshold — đều diễn ra trên dev set.

Script [baseline_sanity_check.py](../scripts/baseline_sanity_check.py) bắt buộc phải truyền `--touch-holdout` mới chạm vào nó. Đây là rào cản cố ý, không phải bất tiện.

### 2.3 Expanding window trên dev set

Dev set chia thành 5 khối đều nhau theo số dòng. Fold `i` train trên khối `0..i`, validate trên khối `i+1`:

```
khối:     [0][1][2][3][4]        (thời gian →)
fold 0:   train│val
fold 1:   train────│val
fold 2:   train───────│val
fold 3:   train──────────│val
```

Mỗi fold chỉ train trên quá khứ và validate trên tương lai kề. Đây là lý do dùng expanding window thay vì k-fold thường: k-fold ngẫu nhiên sẽ train trên tương lai.

### 2.4 Số liệu thực tế

Ranh giới dev/holdout: `Time = 145,234s`.

| Split | Dòng | Fraud | Tỷ lệ |
|---|---:|---:|---:|
| dev | 226,982 | 399 | 0.1758% |
| holdout (khóa) | 56,744 | **74** | 0.1304% |

| Fold | Train dòng | Train fraud | Val dòng | Val fraud |
|---|---:|---:|---:|---:|
| 0 | 45,397 | 142 | 45,397 | 69 |
| 1 | 90,794 | 211 | 45,396 | 47 |
| 2 | 136,190 | 258 | 45,396 | 89 |
| 3 | 181,586 | 347 | 45,396 | 52 |

Model selection nhìn thấy **257 ca fraud** trên 4 fold — nhiều hơn hẳn 74 ca của một holdout đơn. Đó là toàn bộ lý do tồn tại của multi-fold ở đây.

---

## 3. Metrics

### 3.1 Thứ tự ưu tiên

| Metric | Vai trò | Ghi chú |
|---|---|---|
| **AUPRC** | Primary | Sàn của model ngẫu nhiên = prevalence ≈ 0.0017, **không phải 0.5** |
| AUPRC 95% CI | **Bắt buộc đi kèm** | Bootstrap 2,000 lần; báo cáo AUPRC trần là vi phạm protocol |
| ROC-AUC | Secondary | Lạc quan một cách gây hiểu lầm ở mức mất cân bằng này |
| Precision@k | Vận hành | k ∈ {50, 100, 200, 500} — hàng đợi review của analyst |
| Recall@k | Vận hành | Bắt được bao nhiêu % fraud trong k alert đầu |
| Precision/Recall/F1 @ threshold | Vận hành | Threshold **phải** lấy từ validation, không từ holdout |

`lift_over_random = AUPRC / prevalence` là cách trung thực để phát biểu model hơn ngẫu nhiên bao nhiêu lần.

> [!NOTE]
> **CP@k (Card Precision @ k) của ULB không cài đặt được** trên dataset này. Metric đó đếm số *thẻ* riêng biệt trong top-k alert, nhưng `creditcard.csv` không có card ID. Đã thay bằng precision@k thuần trên giao dịch. Khi chuyển sang dataset có entity ID (Phase 3), cần bổ sung CP@k thật.

### 3.2 So sánh hai model: dùng paired bootstrap

Đây là điểm quan trọng nhất của protocol.

Cách sai phổ biến: chấm model A và model B, in ra CI của từng cái, thấy chúng chồng lấn → kết luận "không khác biệt". Cách này quá bảo thủ và bỏ sót hiệu ứng thật.

Cách đúng: [`metrics.compare_auprc()`](../src/evaluation/metrics.py) bootstrap trên **hiệu số** AUPRC. Mỗi vòng lặp, cả hai model được chấm trên *cùng* một mẫu resample, nên phần phương sai dùng chung — mẫu nào được rút, mẫu đó khó đến đâu — bị triệt tiêu trong hiệu số.

```python
result = metrics.compare_auprc(y_val, baseline_scores, quantum_scores,
                               label_a="classical", label_b="quantum")
print(result.summary())
# significant == True  <=>  khoảng tin cậy của hiệu số không chứa 0
```

> [!WARNING]
> **Giới hạn của phương pháp:** pairing chỉ chặt hơn khi hai model *tương quan dương* — trường hợp điển hình khi so hai phương pháp trên cùng feature set. Nếu hai model mắc lỗi hoàn toàn không liên quan, phương sai của hiệu số là **tổng** hai phương sai và khoảng tin cậy sẽ *rộng hơn*. Đã có test cho cả hai chiều: `test_pairing_resolves_a_difference_that_overlapping_intervals_hide` và `test_pairing_does_not_help_for_uncorrelated_models`.

---

## 4. Bốn quy tắc chống rò rỉ

| # | Quy tắc | Thực thi bởi |
|---|---|---|
| 1 | Không bao giờ random split — chỉ cắt theo thời gian | `assert_no_temporal_leakage()` chạy trước khi ghi bất kỳ split nào ra đĩa |
| 2 | Scaler `fit` **chỉ** trên train | `Preprocessor.transform()` raise nếu chưa `fit`; test khẳng định thống kê đến từ train |
| 3 | Resampling (SMOTE...) **chỉ** trên train | Chưa cài đặt ở Phase 0 — quy tắc áp dụng từ Phase 1 |
| 4 | Feature selection không dựa trên toàn bộ dataset | Quy tắc áp dụng từ Phase 1 |

Thêm một quy tắc riêng của dự án này:

| 5 | **Threshold leakage** — chọn threshold trên holdout rồi báo cáo metric tại threshold đó thì con số không còn là ước lượng out-of-sample | `best_f1_threshold()` có cảnh báo trong docstring; script lấy threshold từ fold validation cuối |

---

## 5. Mỗi thí nghiệm phải ghi lại những gì

Yêu cầu từ [README](../README.md#evaluation-principles), cụ thể hóa:

- [ ] `split_manifest.json` tại thời điểm chạy (gồm SHA-256 của file nguồn)
- [ ] Random seed (mặc định `config.SEED = 42`)
- [ ] Số feature dùng — **phải bằng nhau** giữa nhánh classical và quantum
- [ ] AUPRC per-fold **kèm CI**, không chỉ giá trị trung bình
- [ ] Kết quả `compare_auprc` với baseline
- [ ] Thời gian inference và tài nguyên
- [ ] Riêng quantum: số qubit, độ sâu mạch, số tham số, noise model, simulator hay hardware thật

---

## 6. Kết quả Phase 1 — supervised baselines

Sáu cấu hình chạy qua 4 fold, tất cả cùng split, cùng seed, cùng 30 feature.

| Model | mean AUPRC | CI width | per-fold |
|---|---:|---:|---|
| **xgboost** | **0.7741** | 0.2090 | 0.817 / 0.667 / 0.821 / 0.792 |
| lightgbm_unweighted | 0.7694 | 0.2096 | 0.818 / 0.694 / 0.804 / 0.762 |
| xgboost_unweighted | 0.7673 | 0.2138 | 0.814 / 0.668 / 0.800 / 0.787 |
| logreg_full_scale | 0.6968 | 0.2350 | 0.615 / 0.570 / 0.830 / 0.773 |
| logreg *(tham chiếu Phase 0)* | 0.6932 | 0.2329 | 0.601 / 0.569 / 0.829 / 0.773 |
| lightgbm | 0.5011 | 0.2326 | 0.760 / 0.525 / 0.436 / 0.283 |

Bảng này **không phải kết luận**. Độ rộng CI (~0.21–0.24) lớn hơn hầu hết khoảng cách trong bảng. Kết luận đến từ bốn paired test dưới đây.

### 6.1 XGBoost có thắng logistic regression không?

```
uv run python scripts/compare_models.py logreg xgboost
```

| Fold | Positives | delta | 95% CI | Kết luận |
|---|---:|---:|---|---|
| 0 | 69 | +0.2153 | [+0.1171, +0.3095] | **có ý nghĩa** |
| 1 | 47 | +0.0981 | [+0.0306, +0.1782] | **có ý nghĩa** |
| 2 | 89 | −0.0081 | [−0.0510, +0.0307] | không |
| 3 | 52 | +0.0184 | [−0.0032, +0.0452] | không |

**Có, nhưng yếu: thắng có ý nghĩa ở 2/4 fold, không thua fold nào.** Mean delta +0.0809.

Đáng chú ý: hai fold XGBoost thắng là fold 0 và 1 — hai fold **ít dữ liệu train nhất**. Khi cửa sổ mở rộng, lợi thế biến mất. Nếu chỉ nhìn hai CI riêng lẻ (0.7741 ± 0.10 vs 0.6932 ± 0.12) thì sẽ kết luận "không khác biệt"; paired test phân giải được 2 fold. Đây là minh chứng trực tiếp cho lý do §3.2 tồn tại.

### 6.2 Scaling V1–V28 có quan trọng với model tuyến tính không?

**Không.** Mean delta +0.0036, chỉ có ý nghĩa ở 1/4 fold (fold 0, +0.0131). Vấn đề tồn đọng từ Phase 0 được giải quyết bằng đo đạc: với logistic regression, để V1–V28 nguyên hay scale đều không thay đổi kết quả một cách đáng kể.

> [!WARNING]
> Kết luận này **chỉ áp dụng cho model tuyến tính**. OC-SVM, autoencoder và quantum feature map dựa trên hình học khoảng cách, nơi chênh lệch std 0.33–1.96 giữa các V có thể quan trọng hơn nhiều. Phải đo lại riêng cho từng loại.

### 6.3 `scale_pos_weight` có giúp ích không?

Đây là kết quả bất ngờ nhất của Phase 1, và nó **mâu thuẫn với khuyến nghị trong [research_synthesis.md](research_synthesis.md) §2.2**.

| So sánh | Mean delta | Fold có ý nghĩa |
|---|---:|---|
| lightgbm → lightgbm_unweighted | **+0.2683** | **4/4** |
| xgboost → xgboost_unweighted | −0.0069 | 0/4 |

Với **LightGBM, bỏ trọng số thắng ở cả 4 fold**, và mức thắng *tăng dần* theo lượng dữ liệu train: +0.058 (fold 0) → +0.169 → +0.368 → **+0.479** (fold 3). Với **XGBoost thì không có khác biệt nào**.

Nghĩa là khuyến nghị "đặt `scale_pos_weight ≈ 578`" không phải một quy tắc chung — nó vô hại với XGBoost và có hại nghiêm trọng với LightGBM trên dataset này.

### 6.4 Lỗi đã gặp: LightGBM bão hòa điểm số

Cấu hình LightGBM đầu tiên cho AUPRC **0.0148** ở fold 0 — gần sàn ngẫu nhiên 0.0017 — trong khi **ROC-AUC vẫn đọc 0.80**.

Nguyên nhân: LightGBM mặc định `reg_lambda=0`, XGBoost mặc định `reg_lambda=1`. Không có phạt L2, trọng số 578x đẩy leaf value tăng không giới hạn cho tới khi đầu ra logistic bão hòa. Kết quả: **65 giá trị điểm phân biệt trên 45,397 dòng**, với 2,062 dòng trùng đúng ở 1.0 mà chỉ 45 là fraud. Xếp hạng bên trong khối trùng là ngẫu nhiên → P@100 sụp còn 0.04.

ROC-AUC không phát hiện được vì các *khối* vẫn được sắp đúng thứ tự. Đây là ví dụ cụ thể cho lý do §3.1 xếp ROC-AUC là secondary.

> [!IMPORTANT]
> Runner giờ tự động cảnh báo khi tỷ lệ điểm phân biệt trên số dòng thấp hơn `MIN_DISTINCT_SCORE_RATIO = 0.01`, và ghi `n_distinct_scores` vào mọi record. Một model bão hòa vẫn cho ROC-AUC trông hợp lý, nên không thể trông chờ bảng metric tự phơi bày lỗi này.

### 6.5 Anomaly layer — và giới hạn của chính benchmark này

Bốn cấu hình unsupervised, fit **chỉ trên lớp non-fraud**, không bao giờ thấy nhãn.

| Model | mean AUPRC | per-fold |
|---|---:|---|
| autoencoder | 0.2116 | 0.059 / 0.069 / 0.623 / 0.096 |
| autoencoder_minimal_scale | 0.1106 | 0.042 / 0.045 / 0.239 / 0.118 |
| isolation_forest | 0.0871 | 0.051 / 0.031 / 0.241 / 0.025 |
| isolation_forest_with_time | 0.0711 | 0.037 / 0.027 / 0.193 / 0.028 |

So với XGBoost 0.7741, đây là khoảng cách rất lớn — và **đó là kết quả dự kiến, không phải thất bại**. Anomaly model giải bài toán khó hơn với ít thông tin hơn, trên một benchmark mà fraud được lấy từ đúng phân phối mà model supervised đã được huấn luyện.

Hai quyết định thiết kế được kiểm chứng bằng đo đạc:

- **Bỏ `Time` khỏi input**: thắng 3/4 fold, thua 1/4, mean delta +0.0160. Verdict "inconsistent" — ủng hộ nhẹ, chưa dứt khoát. Lý do bỏ: dưới expanding window, mọi timestamp validation nằm ngoài dải train, nên model nào tái tạo/cô lập theo `Time` sẽ phạt các dòng càng về sau càng nặng — nhiễu thuần túy với fraud. `Time` là tọa độ chia tách, không phải feature hành vi.
- **Scale toàn bộ input cho autoencoder**: mean delta +0.1010, có ý nghĩa ở 1/4 fold. Reconstruction error là tổng trên các feature, nên feature có biên độ rộng đóng góp nhiều lỗi hơn bất kể nó có thông tin hay không.

### 6.6 Hybrid: anomaly score làm feature cho supervised

Theo Carcillo et al. 2019 — anomaly là **tín hiệu đầu vào** cho tầng quyết định, không phải một classifier khác.

| Model | mean AUPRC | vs xgboost |
|---|---:|---|
| xgboost_hybrid_iforest | 0.7677 | mean delta −0.0064, **0/4 fold** |
| xgboost_hybrid | 0.7549 | mean delta −0.0192, **thua 1/4 fold** |

**Không giúp gì, và bản đầy đủ còn hơi có hại.**

Kết quả này đúng như dự đoán trước khi chạy, vì một lý do cấu trúc: các component anomaly nhìn **đúng những feature mà XGBoost đã có**. Không có thông tin mới nào để đóng góp.

> [!CAUTION]
> Đây là kết luận **hẹp**. Nó nói rằng anomaly layer không thêm gì trên benchmark mà fraud validation cùng phân phối với fraud train. Nó **không** nói gì về fraud kiểu mới — thứ mà tầng này sinh ra để xử lý. Benchmark AUPRC tiêu chuẩn **về nguyên tắc không thể** đo được điều đó. Xem §6.7.

### 6.7 Novel-fraud holdout — thí nghiệm mà benchmark tiêu chuẩn không làm được

`scripts/novel_fraud_experiment.py`. Thiết kế:

1. Phân cụm fraud trong dev thành 4 nhóm hành vi (KMeans trên PCA components) — đại diện cho "loại fraud".
2. Với mỗi cụm `c`: **gán lại nhãn toàn bộ fraud thuộc `c` thành hợp lệ trong tập train**. Model supervised giờ mù với loại đó — và như thực tế, dữ liệu "bình thường" của anomaly model bị nhiễm fraud chưa phát hiện.
3. Đánh giá trên validation fold, giới hạn ở các dòng hợp lệ + fraud thuộc riêng cụm `c`.
4. So với một lần chạy *oracle* có thấy nhãn cụm `c`. Khoảng cách là **chi phí của tính mới**.

Phân bố cụm: 164 / 91 / 137 / 7 ca. Cụm 1 và 3 chỉ xuất hiện trong validation của fold 2, nên phần lớn cell bị bỏ qua — hạn chế thật của thiết kế trên dataset 48 giờ này.

**Kết quả:**

| Model | oracle | blind | giữ lại |
|---|---:|---:|---:|
| isolation_forest | 0.0929 | 0.1084 | **116.7%** |
| xgboost | 0.7145 | 0.4575 | 64.0% |
| xgboost_hybrid_iforest | 0.7009 | 0.4521 | 64.5% |

Chi phí tính mới của XGBoost theo từng cụm:

| Cụm | oracle | blind | sụt |
|---|---:|---:|---:|
| 0 (164 ca) | 0.5288 | 0.3434 | −0.1854 |
| 1 (91 ca) | 0.9220 | 0.3030 | **−0.6190** |
| 2 (137 ca) | 0.9493 | 0.6470 | −0.3023 |
| 3 (7 ca) | 0.3103 | 0.3103 | 0.0000 |

**Ba điều đọc ra, theo thứ tự quan trọng:**

**1. Chi phí của tính mới là có thật và lớn.** XGBoost mất 36% hiệu năng khi loại fraud chưa từng được gán nhãn. Với cụm 1, nó sụp từ 0.9220 xuống 0.3030. Đây là bằng chứng định lượng cho luận điểm của README rằng nhãn quá khứ không đủ.

**2. Anomaly layer bền hơn — nhưng bền không có nghĩa là tốt hơn.** Isolation Forest giữ 116.7% (thực chất là không bị ảnh hưởng, vì nó không dùng nhãn). Nhưng mức tuyệt đối của nó là **0.1084 so với 0.4575 của XGBoost bị làm mù**. Nó ổn định vì nó vốn đã kém ở đây, không phải vì nó nhận ra fraud mới.

**3. Hybrid không cứu được gì.** 0.4521 so với 0.4575 — kém hơn −0.0054. Anomaly signal không giúp model supervised xử lý fraud kiểu mới.

> [!IMPORTANT]
> Đây là **kết quả âm mạnh hơn** những gì benchmark cùng phân phối có thể kết luận. Trên `creditcard.csv`, tầng anomaly như hiện tại không đóng góp — cả ở điều kiện bình thường lẫn ở điều kiện fraud mới.
>
> Điều này **không bác bỏ** kiến trúc của Sentinel. Nó chỉ ra rằng anomaly detection trên **cùng một không gian feature tĩnh** mà supervised model đã có thì không thêm được gì. Giá trị của "learn normal first" nằm ở chỗ mô hình hóa **hành vi theo entity qua thời gian** — customer, merchant, device — thứ mà `creditcard.csv` không có. Đây là bằng chứng thực nghiệm ủng hộ việc đưa dataset có entity ID vào sớm hơn kế hoạch.

**Cảnh báo về thiết kế:** phân cụm được fit trên toàn bộ fraud của dev, tức dùng nhãn mà model bị làm mù không được thấy. Điều này hợp lệ vì clustering định nghĩa *thí nghiệm*, không phải input của model nào — nó quyết định nhãn nào bị giấu và dòng nào được chấm. Nhưng nó có nghĩa là các "loại fraud" được định nghĩa với lợi thế nhìn lại, nên chúng tách bạch hơn một loại fraud mới thật sự.

### 6.8 Sàn hiện tại

**XGBoost, mean AUPRC 0.7741.** Mọi model Phase 1 trở đi phải vượt qua nó bằng paired test, không phải bằng con số trần.

Vẫn giữ nguyên nhận xét từ Phase 0: các fold chênh nhau tới 0.26 AUPRC (logreg: 0.569 → 0.829). Đó không phải lỗi mà là thực tế fraud phân bố không đều theo thời gian.

---

## 7. Giới hạn đã biết của protocol này

1. **74 ca fraud trong holdout** là ít. Không có cách nào khắc phục trong phạm vi dataset này; chỉ có thể báo cáo trung thực độ bất định.
2. **Chỉ 48 giờ dữ liệu** → không đánh giá được temporal drift dài hạn hay tính mùa vụ, dù drift là một trong những rủi ro chính của fraud detection.
3. **Không có entity ID** → không xây được behavioral profile theo customer/merchant/device. Phase 3 của README **không khả thi** trên dataset này; cần bổ sung IEEE-CIS, ULB simulator, hoặc dữ liệu tương đương.
4. **V1–V28 là PCA** → SHAP sẽ chỉ ra được feature nào quan trọng, nhưng không diễn giải được sang ngôn ngữ nghiệp vụ. Yêu cầu "explainability by design" của README chỉ đạt được một phần.

4b. **Hyperparameter chưa được search.** Kết quả §6 dùng cấu hình cố định, hợp lý nhưng chưa tối ưu. Điều này khiến so sánh giữa các model là so sánh *cấu hình mặc định*, không phải so sánh tiềm năng tối đa. Muốn search thì phải search **bên trong** từng fold train, không phải trên fold validation — nếu không sẽ thành selection leakage.
5. **Amount bimodal trong lớp fraud** (đỉnh ~$1 chiếm 26% và đỉnh ~$100 chiếm 12%). Cost-sensitive weighting theo `Amount` như Kaggle gợi ý sẽ kéo model về phía nhóm cash-out lớn và bỏ rơi nhóm card-testing. Nếu cả hai đều quan trọng, phải đánh giá tách riêng.

---

## 8. Cách chạy lại

Mọi lệnh nhận cờ `--dataset`. Bỏ trống thì mặc định là `creditcard` — chọn cố ý, vì mọi kết quả đã ghi nhận đến giờ đều trên bộ đó và đổi mặc định một cách âm thầm sẽ khiến số cũ và số mới trông như so sánh được với nhau trong khi không phải.

```bash
uv sync
uv run python scripts/build_splits.py --dataset creditcard    # tạo splits + manifest
uv run python scripts/run_experiment.py --dataset creditcard --all
uv run python scripts/compare_models.py --dataset creditcard logreg xgboost
uv run pytest                                                  # 168 tests
```

Dataset thứ hai dùng đúng những lệnh đó với `--dataset ieeecis`.

Kiểm tra tính tái lập sau khi tái cấu trúc:

```bash
cp -r experiments/results experiments/results_pre_refactor   # trước khi sửa
uv run python scripts/verify_migration.py                    # sau khi chạy lại
```

Chạy một model cụ thể:

```bash
uv run python scripts/run_experiment.py --model xgboost
uv run python scripts/baseline_sanity_check.py           # alias cho --model logreg
```

Chạm vào holdout (một lần mỗi phase):

```bash
uv run python scripts/run_experiment.py --model xgboost --touch-holdout
```

Kết quả ghi vào `experiments/results/<model>/` gồm `record.json` (metric + khai báo model + tham số) và `scores.npz` (điểm per-fold). **`scores.npz` là thứ `compare_models.py` cần** — không có nó thì không paired test được, và tính lại từ model đã lưu không tương đương vì sẽ kéo theo mọi khác biệt về version và seed.
