# Báo cáo Tổng quan Dự án Sentinel

## 1. Giới thiệu dự án

Sentinel là một nền tảng phân tích bất thường hành vi (Behavioral Anomaly Intelligence) được thiết kế để phát hiện gian lận trong hệ thống thanh toán trực tuyến. Nguyên tắc vận hành cốt lõi của hệ thống là tách biệt hai giai đoạn: (1) mô hình hoá hành vi bình thường của hệ thống, và (2) đo lường độ lệch so với hành vi bình thường đó để sinh tín hiệu rủi ro. Dự án hiện hoàn thành Phase 1 (Classical Behavioral Baseline) theo lộ trình đề ra, bao gồm toàn bộ đường ống dữ liệu, hệ thống mô hình, khung đánh giá, và các kết quả thực nghiệm đã được kiểm chứng.

## 2. Cấu trúc dự án

Mã nguồn được tổ chức thành ba khối chính: `src/` (5.593 dòng), `scripts/` (1.493 dòng) và `tests/` (3.756 dòng, 366 bài kiểm thử). Thư mục `src/` chứa toàn bộ logic nghiệp vụ, được chia thành bốn nhóm module: `datasets/` (khai báo bộ dữ liệu), `data/` (nạp dữ liệu và phân chia thời gian), `features/` (xây dựng đặc trưng), `models/` (đăng ký và huấn luyện mô hình), và `evaluation/` (chạy thí nghiệm, đánh giá, phân tích trôi dạt, giải thích kết quả). Thư mục `scripts/` cung cấp các điểm vào dòng lệnh cho từng tác vụ cụ thể. Thư mục `tests/` bao phủ kiểm thử tự động cho toàn bộ các lớp xử lý.

Dự án được thực nghiệm trên hai bộ dữ liệu: (1) European Credit Card — 284.807 giao dịch, 492 trường hợp gian lận (0,17%), 28 biến PCA ẩn danh, thời gian quan sát 2 ngày; và (2) IEEE-CIS Fraud Detection — 590.540 giao dịch, 20.663 trường hợp gian lận (3,50%), 434 biến sau khi nối bảng, thời gian quan sát 182 ngày.

## 3. Kiến trúc đường ống mô hình (Model Pipeline)

Đường ống xử lý được thiết kế thành 10 lớp tuần tự, mỗi lớp thực hiện đúng một nhiệm vụ và được bảo vệ bởi bốn ràng buộc bất biến (invariants):

- **Lớp 1 — Domain Adapter**: Mỗi bộ dữ liệu được khai báo dưới dạng cấu hình (`DatasetSpec`), không phải mã logic. Khi thêm bộ dữ liệu mới, chỉ cần bổ sung một file spec mà không cần thay đổi các lớp phía dưới.
- **Lớp 2 — Ingestion**: Nạp dữ liệu thô, nối bảng (với IEEE-CIS), kiểm tra schema, loại bỏ bản ghi trùng lặp và sắp xếp theo trục thời gian.
- **Lớp 3 — Temporal Partition**: Phân chia dữ liệu theo cửa sổ thời gian mở rộng (expanding) hoặc cửa sổ trượt (sliding). Kiểm tra chống rò rỉ thời gian (temporal leakage) được thực thi tự động trước khi ghi dữ liệu ra đĩa.
- **Lớp 4 — Feature Pipeline**: Xây dựng hai nhóm đặc trưng: đặc trưng cấu trúc (structural — biến đổi, mã hoá, chuẩn hoá) và đặc trưng hành vi (behavioral — tổng hợp tích luỹ theo thực thể, chỉ sử dụng dữ liệu quá khứ).
- **Lớp 5 — Label Regime**: Mỗi mô hình phải khai báo rõ mức độ tiếp cận nhãn khi huấn luyện thông qua 3 Track:
  - **Track A (Supervised — 13 mô hình)**: Thấy toàn bộ thuộc tính X và nhãn thực tế. Bao gồm: `logreg`, `logreg_full_scale`, `xgboost`, `xgboost_unweighted`, `xgboost_tuned`, `lightgbm`, `lightgbm_unweighted`, `lightgbm_tuned`, `xgboost_hybrid`, `xgboost_hybrid_iforest`, `xgboost_behavioral`, `xgboost_behavioral_only`, `xgboost_hybrid_behavioral`.
  - **Track B (One-class / Unsupervised Normal — 6 mô hình)**: Chỉ huấn luyện trên các giao dịch hợp pháp (hành vi bình thường). Bao gồm: `isolation_forest`, `isolation_forest_with_time`, `autoencoder`, `autoencoder_minimal_scale`, `isolation_forest_behavioral`, `autoencoder_behavioral`.
  - **Track C (Unlabeled / Contaminated — 3 mô hình)**: Huấn luyện trên toàn bộ X không sử dụng nhãn, giữ nguyên tỷ lệ nhiễm bẩn gian lận thực tế. Bao gồm: `if_contaminated`, `ae_contaminated`, `pu_cascade`.
- **Lớp 6 — Model**: Đăng ký 22 mô hình trên dưới dạng các factory. Mỗi mô hình khai báo chiến lược chuẩn hoá cột, khả năng xử lý giá trị thiếu, và yêu cầu thông tin thực thể (các mô hình có hậu tố `_behavioral` yêu cầu thông tin thực thể nên chỉ chạy trên IEEE-CIS).
- **Lớp 7 — Execution**: Điều phối quá trình huấn luyện theo từng fold, đo thời gian, và lưu kết quả dự đoán (`scores.npz`) xuống đĩa.
- **Lớp 8 — Evaluation**: Tính AUPRC (chỉ số chính), ROC-AUC, Precision@k, và khoảng tin cậy bằng paired bootstrap (2.000 lần lấy mẫu).
- **Lớp 9 — Drift Protocol**: Đo lường mức suy giảm hiệu năng theo thời gian qua ba kịch bản: đóng băng mô hình (frozen), cửa sổ trượt (sliding), và cửa sổ mở rộng (expanding). Phân tách đóng góp của tính mới dữ liệu (recency) và khối lượng dữ liệu (volume).
- **Lớp 10 — Explanation**: Giải thích kết quả dự đoán bằng TreeSHAP (đóng góp của từng biến) và phân tích phản thực (counterfactual — xác định thay đổi tối thiểu để đảo ngược kết quả).

Bốn ràng buộc bất biến được áp dụng xuyên suốt: (I) dòng thông tin chỉ đi từ quá khứ sang tương lai; (II) mức độ tiếp cận nhãn của mỗi mô hình phải được khai báo tường minh; (III) sự khác biệt giữa các bộ dữ liệu chỉ tồn tại trong hai lớp đầu tiên; (IV) mọi so sánh giữa hai mô hình phải được thực hiện trên cùng tập dữ liệu đánh giá.

## 4. Kết quả mô hình

### 4.1. Bảng xếp hạng IEEE-CIS (AUPRC trên các fold validation)

| Mô hình | Track | AUPRC | Ghi chú |
|---|:---:|---:|---|
| `lightgbm_tuned` | A | 0,6096 | Mô hình tốt nhất · ROC-AUC 0,9127 · Precision@100 = 0,993 |
| `lightgbm_unweighted` | A | 0,5937 | |
| `xgboost_tuned` | A | 0,5861 | |
| `xgboost` | A | 0,5393 | Baseline tham chiếu cho mọi so sánh |
| `xgboost_hybrid` | A | 0,5389 | Bổ sung anomaly score — không cải thiện |
| `if_contaminated` | C | 0,1956 | Isolation Forest không nhãn |
| `isolation_forest` | B | 0,1877 | |
| `pu_cascade` | C | 0,1607 | Thua baseline `if_contaminated` |
| `autoencoder` | B | 0,0922 | |

Trên tập European Credit Card, mô hình `xgboost` đạt AUPRC = 0,7741 (phân fold: 0,8168 / 0,6668 / 0,8213 / 0,7916). Giá trị này được sử dụng làm ràng buộc hồi quy (migration constraint) để kiểm tra tính toàn vẹn của đường ống khi có thay đổi mã nguồn.

### 4.2. Đánh giá chất lượng kết quả

Mô hình `lightgbm_tuned` đạt AUPRC = 0,6096 trên tập IEEE-CIS, tương đương gấp 17,4 lần so với giá trị nền ngẫu nhiên (0,035). Precision@100 đạt 0,993 cho thấy trong 100 cảnh báo rủi ro cao nhất mà mô hình sinh ra, 99 trường hợp là gian lận thực tế. Kết quả này đạt mức cạnh tranh với các giải pháp hàng đầu trên cùng bộ dữ liệu.

Các mô hình Track B (one-class) và Track C (không nhãn) cho kết quả thấp hơn đáng kể, với AUPRC dao động từ 0,078 đến 0,196. Khoảng cách này phản ánh đúng mức độ khó của bài toán phát hiện bất thường khi không có nhãn giám sát, đặc biệt trên bộ dữ liệu thiếu thông tin lịch sử thực thể.

## 5. Các phát hiện thực nghiệm chính

**Tinh chỉnh siêu tham số (Hyperparameter Tuning)** là biện pháp cải thiện hiệu quả nhất được ghi nhận: `lightgbm_tuned` tăng +0,0159 AUPRC so với cấu hình tốt nhất trước đó, có ý nghĩa thống kê trên 4/6 fold. Tuy nhiên, hiệu quả này chỉ áp dụng cho các mô hình cây tổ hợp (tree ensembles) có không gian siêu tham số tương tác, không áp dụng cho mô hình tuyến tính.

**Đặc trưng hành vi không cải thiện hiệu năng trên IEEE-CIS.** Bốn thí nghiệm so sánh đều cho kết quả tiêu cực. Nguyên nhân được xác định: 26 cột hành vi tự xây dựng chỉ đóng góp 4,70% tổng gain của XGBoost, trong khi bộ dữ liệu đã chứa sẵn các biến đếm tích luỹ do nhà cung cấp dữ liệu (Vesta) tính trước. Kết luận về tính dư thừa được kiểm chứng thêm bằng thí nghiệm thay đổi khoá thực thể (entity proxy), và kết quả không thay đổi.

**Tính mới của dữ liệu (recency) chiếm 82% hiệu năng mô hình**, so với 18% từ khối lượng dữ liệu tích luỹ. Mức suy giảm khi đóng băng mô hình tăng dần theo khoảng cách thời gian (từ +0,0221 ở block 2 lên +0,1071 ở block 6). Đối với mô hình đã tinh chỉnh (`lightgbm_tuned`), việc đóng băng làm mất 61% lợi ích từ tinh chỉnh siêu tham số. Cửa sổ huấn luyện tối ưu là 2 block (khoảng 60 ngày), đạt hiệu năng tương đương toàn bộ lịch sử trong khi giảm 3 lần chi phí tính toán.

**Lớp phát hiện bất thường (anomaly layer) chưa đóng góp giá trị** khi kết hợp với mô hình giám sát. AUPRC của `xgboost_hybrid` (0,5389) không khác biệt so với `xgboost` thuần (0,5393) trên cả hai bộ dữ liệu.

## 6. Nghiệm thu dự án

### 6.1. Các mục tiêu đã hoàn thành

- Đường ống dữ liệu tái lập được (reproducible data pipeline) với kiểm tra chống rò rỉ thời gian tự động.
- Hệ thống đặc trưng cấu trúc và hành vi hoàn chỉnh, tương thích đa bộ dữ liệu.
- 22 mô hình thuộc ba chế độ nhãn (supervised, one-class, unlabeled), mỗi mô hình có câu hỏi đo lường gắn liền.
- Khung đánh giá dựa trên AUPRC, paired bootstrap, và kiểm chứng hồi quy (migration constraint).
- Phân tích trôi dạt dữ liệu (data drift) với phân tách recency/volume trên ba kịch bản huấn luyện.
- Lớp giải thích kết quả bằng TreeSHAP và phân tích phản thực.
- 366 bài kiểm thử tự động bao phủ toàn bộ các lớp xử lý.
- Holdout chưa từng được chấm điểm (0/37 bản ghi), bảo toàn tính toàn vẹn cho đánh giá cuối cùng.

### 6.2. Hạn chế đã xác định

- Hai bộ dữ liệu hiện có thiếu thông tin lịch sử thực thể (entity history) — creditcard không có định danh người dùng, IEEE-CIS sử dụng khoá thực thể ghép gián tiếp. Điều này hạn chế khả năng kiểm chứng tầm nhìn mô hình hoá quỹ đạo hành vi (behavioral trajectory) của dự án.
- Các mô hình phát hiện bất thường (Track B, C) chưa đạt hiệu năng đủ cao để sử dụng độc lập trong bối cảnh bộ dữ liệu hiện tại.
- Hệ thống hiện hoạt động ở chế độ nghiên cứu ngoại tuyến (offline research), chưa có thành phần phục vụ thời gian thực (real-time serving).

### 6.3. Hướng phát triển tiếp theo

Giai đoạn tiếp theo (Phase 2) theo lộ trình là đánh giá lớp lai cổ điển-lượng tử (hybrid quantum layer), bao gồm quantum kernel, quantum autoencoder, và phương pháp đo tương đồng dựa trên fidelity. Kết quả từ Phase 1 đã cung cấp một dự báo cụ thể: vì autoencoder cổ điển mất 72% hiệu năng khi tập huấn luyện bị nhiễm 0,17% dữ liệu gian lận, quantum autoencoder cũng sẽ gặp rủi ro tương tự nếu không được huấn luyện trên dữ liệu đã lọc sạch. Ngoài ra, việc bổ sung bộ dữ liệu có lịch sử thực thể đầy đủ (như Sparkov hoặc IBM Transactions) là cần thiết để kiểm chứng giá trị của đặc trưng hành vi và mô hình phát hiện bất thường.
