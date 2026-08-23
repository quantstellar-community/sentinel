# Sentinel — Product Requirements Document

> **Phiên bản:** V1.0  
> **Trạng thái:** Draft chính thức cho giai đoạn phát triển V1  
> **Dự án:** Quantstellar Sentinel  
> **Loại sản phẩm:** Financial Behavioral Intelligence / Fraud Intelligence  
> **Nguyên tắc nền tảng:** Classical First → Quantum Where Justified → Fair Benchmark → Measure Real Value → Decision Intelligence

---

## 1. Tổng quan sản phẩm

### 1.1. Sentinel là gì?

**Sentinel** là hệ thống **Behavioral Fraud Intelligence** tập trung vào phát hiện giao dịch và hành vi tài chính bất thường, đánh giá mức độ rủi ro và hỗ trợ điều tra, ra quyết định.

Sentinel không xem phát hiện gian lận đơn thuần là một bài toán phân loại nhị phân `fraud / non-fraud`. Thay vào đó, hệ thống xây dựng cách nhìn dựa trên hành vi:

```text
Transaction History
        ↓
Behavioral Representation
        ↓
Normal Behavior Space
        ↓
Deviation / Novelty
        ↓
Anomaly
        ↓
Risk
        ↓
Decision Support
```

Sentinel kết hợp Classical AI/ML với Quantum Machine Learning theo mô hình hybrid. Classical methods là baseline và nền tảng chính; Quantum được sử dụng như một computational enhancement layer khi có cơ sở khoa học và thực nghiệm cho thấy giá trị.

### 1.2. Product thesis

> **Sentinel không xây Quantum để chứng minh Quantum. Sentinel xây Behavioral Intelligence và sử dụng Quantum ở những nơi Quantum thực sự tạo ra giá trị có thể đo lường.**

Sản phẩm hướng tới một intelligence layer có thể hỗ trợ các hệ thống tài chính hiện hữu thay vì thay thế toàn bộ core infrastructure.

### 1.3. Phạm vi sản phẩm

Phiên bản V1 tập trung vào:

- Transaction anomaly detection.
- Behavioral representation và behavioral profiling ở mức phù hợp với dữ liệu.
- Fraud/anomaly scoring.
- Classical baseline.
- Quantum-enhanced anomaly detection.
- Investigation và decision-support interface.
- Đánh giá công bằng Classical vs Quantum.
- API-first architecture để có thể tích hợp với hệ thống khác.

---

## 2. Bối cảnh và vấn đề cần giải quyết

### 2.1. Bối cảnh

Giao dịch tài chính ngày càng được thực hiện qua môi trường số với số lượng lớn, tốc độ cao và hành vi thay đổi liên tục. Trong bối cảnh đó, gian lận không nhất thiết biểu hiện bằng một đặc trưng đơn lẻ mà có thể xuất hiện dưới dạng sự lệch khỏi hành vi thông thường của khách hàng, tài khoản, thiết bị hoặc nhóm hành vi.

Dữ liệu fraud detection thường có một số đặc điểm khó:

- Dữ liệu mất cân bằng mạnh.
- Fraud có thể rất hiếm so với giao dịch hợp lệ.
- Fraud patterns thay đổi theo thời gian.
- Một giao dịch riêng lẻ có thể không đủ thông tin để kết luận.
- False positive có thể tạo ra chi phí điều tra và ảnh hưởng trải nghiệm khách hàng.
- Các mô hình chỉ dựa trên supervised classification có thể khó phát hiện những pattern mới chưa xuất hiện trong dữ liệu huấn luyện.

### 2.2. Vấn đề cốt lõi

Sentinel tập trung vào câu hỏi:

> **Làm thế nào để phát hiện một giao dịch hoặc hành vi lệch đáng kể khỏi behavioral pattern bình thường, đánh giá mức độ bất thường/rủi ro và hỗ trợ con người đưa ra quyết định phù hợp?**

Thay vì chỉ hỏi:

> “Transaction này có phải fraud không?”

Sentinel hướng tới:

> “Transaction này khác hành vi bình thường đến mức nào, tại sao nó bất thường, mức độ rủi ro ra sao và có cần điều tra thêm hay không?”

### 2.3. Các vấn đề Sentinel cần cải thiện

1. Khả năng phát hiện behavioral anomalies.
2. Khả năng xử lý những trường hợp chưa có pattern fraud rõ ràng.
3. Giảm phụ thuộc vào một classification boundary duy nhất.
4. Hỗ trợ investigation thay vì chỉ trả về một nhãn.
5. Cho phép đánh giá vai trò thực tế của Quantum trong anomaly detection.
6. Tạo một kiến trúc có thể mở rộng từ prototype nghiên cứu thành intelligence API.

---

## 3. Người dùng mục tiêu

### 3.1. Nhóm người dùng chính

**Fraud / Financial Crime Investigator**

- Điều tra các giao dịch đáng ngờ.
- Xem evidence và anomaly signals.
- Ưu tiên các case cần review.
- Hỗ trợ quyết định điều tra tiếp.

**Risk / Compliance Analyst**

- Theo dõi các dấu hiệu bất thường.
- Đánh giá mức độ rủi ro.
- Phân tích behavioral patterns.
- Sử dụng kết quả để hỗ trợ quy trình risk/compliance.

### 3.2. Nhóm người dùng mở rộng

**Financial Institution / Fintech**

- Tích hợp Sentinel vào hệ thống fraud/risk hiện hữu.
- Sử dụng Sentinel như một intelligence layer.
- Kết hợp kết quả Sentinel với hệ thống quyết định nội bộ.

**Data Scientist / ML Engineer / Researcher**

- Xây dựng và đánh giá behavioral models.
- So sánh Classical và Quantum approaches.
- Thực hiện benchmark, ablation và resource analysis.

---

## 4. Mục tiêu sản phẩm

### 4.1. Mục tiêu chính

Sentinel phải:

1. Phát hiện được các transaction/behavioral anomalies có ý nghĩa.
2. Xây dựng behavioral representation phù hợp với bài toán.
3. Cung cấp anomaly/risk signals có thể giải thích ở mức phù hợp.
4. Hỗ trợ investigator ưu tiên các trường hợp cần review.
5. Có Classical baseline rõ ràng trước khi đánh giá Quantum.
6. Đánh giá Quantum bằng benchmark công bằng và end-to-end.
7. Tạo nền tảng API-first có thể mở rộng thành Behavioral Intelligence API.

### 4.2. Mục tiêu nghiên cứu

Sentinel cũng là một research platform có khả năng kiểm chứng:

- Quantum Kernel cho behavioral anomaly detection.
- Quantum Kernel + OCSVM.
- Hybrid Classical–Quantum anomaly detection.
- Selective Quantum enhancement.
- Temporal/behavioral representation kết hợp Quantum methods.
- Các hướng Quantum Autoencoder/QAE hoặc phương pháp khác khi có hypothesis rõ ràng.

Các hướng nghiên cứu tương lai không được xem là tính năng bắt buộc của V1.

---

## 5. Non-goals

Sentinel **không** có các mục tiêu sau trong phạm vi V1:

### 5.1. Không phải trading system

Sentinel không phải:

- Trading bot.
- Stock-price predictor.
- Portfolio optimizer.
- Automated trading engine.

### 5.2. Không thay thế core banking

Sentinel không nhằm thay thế:

- Core banking system.
- Payment processing infrastructure.
- Existing transaction processing systems.
- Existing enterprise compliance platforms.

Sentinel đóng vai trò **intelligence layer** có thể tích hợp với các hệ thống hiện hữu.

### 5.3. Không sử dụng Quantum một cách mặc định

Sentinel không chạy Quantum trên mọi transaction chỉ vì dự án có Quantum.

Quantum chỉ được sử dụng khi:

- Có scientific motivation.
- Có classical baseline.
- Có hypothesis rõ ràng.
- Có benchmark công bằng.
- Chi phí encoding/state preparation/circuit/shots và các resource liên quan được xem xét.
- Có practical utility hoặc research value có thể chứng minh.

### 5.4. Không tuyên bố Quantum Advantage khi chưa chứng minh

Theoretical speedup hoặc một metric tốt hơn trên một experiment nhỏ không đủ để kết luận quantum advantage.

Đánh giá phải xem xét cả:

- Encoding/state preparation.
- Oracle/circuit cost nếu có.
- Qubit count.
- Circuit depth.
- Shots.
- Noise.
- Simulation/hardware runtime.
- Scalability.
- End-to-end computational cost.
- Practical utility.

### 5.5. Không xây enterprise infrastructure quá sớm

V1 không mặc định yêu cầu:

- Microservices.
- Kubernetes.
- Distributed feature store.
- Complex orchestration.
- Large-scale model registry.
- Cloud infrastructure phức tạp.

Chỉ đưa infrastructure vào khi có yêu cầu thực tế và có justification.

---

## 6. Giá trị cốt lõi

### 6.1. Behavioral Intelligence

Sentinel chuyển từ cách nhìn transaction-level sang behavioral-level:

```text
Individual Transaction
        ↓
Historical Context
        ↓
Behavior Representation
        ↓
Behavioral Deviation
```

### 6.2. Novelty và anomaly detection

Sentinel không chỉ tìm các fraud pattern đã biết mà hướng tới phát hiện những hành vi lệch khỏi normal behavior space.

### 6.3. Hybrid intelligence

Classical và Quantum không cạnh tranh một cách hình thức. Chúng được sử dụng ở nơi phù hợp với vai trò của từng phương pháp.

### 6.4. Investigation-oriented intelligence

Output không chỉ là:

```text
fraud = 1
```

mà hướng tới:

```text
Anomaly
+
Risk
+
Evidence
+
Decision Support
```

### 6.5. Scientific rigor

Mọi Quantum approach phải có:

```text
Problem
→ Hypothesis
→ Mathematical Formulation
→ Classical Baseline
→ Quantum Method
→ Fair Benchmark
→ Resource / Ablation Analysis
→ Scientific Conclusion
→ Product Evaluation
```

---

## 7. Tính năng sản phẩm

### 7.1. Transaction Analysis

Hệ thống nhận transaction data và tạo ra analysis result.

Các nhóm thông tin có thể bao gồm:

- Transaction attributes.
- Temporal information.
- Behavioral context.
- Derived behavioral features.
- Model scores.
- Anomaly signals.

### 7.2. Behavioral Profiling

Sentinel xây dựng representation về hành vi dựa trên lịch sử giao dịch và các behavioral features có sẵn.

Mục tiêu là xác định:

- Normal behavioral pattern.
- Behavioral deviation.
- Temporal change.
- Novelty/anomaly signals.

### 7.3. Anomaly Detection

Sentinel hỗ trợ anomaly detection bằng Classical và Quantum methods.

Các baseline/approaches có thể bao gồm:

- Isolation Forest.
- One-Class SVM.
- Classical kernel methods.
- Quantum Kernel.
- Quantum Kernel + OCSVM.

Việc lựa chọn model cuối cùng phải dựa trên benchmark thay vì giả định trước model nào tốt nhất.

### 7.4. Risk / Anomaly Scoring

Hệ thống tạo ra các score có semantic rõ ràng.

Ví dụ:

- Classical fraud/anomaly score.
- Quantum anomaly score.
- Unified risk score khi có đủ cơ sở để kết hợp.
- Evidence/signals hỗ trợ score.

Không tạo thêm score chỉ để làm giao diện có nhiều chỉ số hơn.

### 7.5. Selective Quantum Enhancement

Quantum có thể được sử dụng cho các trường hợp:

- Khó phân loại.
- Có mức độ bất thường không rõ ràng.
- Nằm trong vùng gray zone.
- Cần thêm một lớp behavioral similarity/anomaly analysis.

Routing strategy phải được kiểm chứng thực nghiệm.

### 7.6. Investigation Interface

Sentinel cung cấp giao diện điều tra để người dùng:

- Xem transaction.
- Xem anomaly/risk signals.
- Xem behavioral evidence.
- Xem model assessment.
- Xem kết quả Quantum khi được sử dụng.
- Ưu tiên case cần review.
- Hỗ trợ đưa ra quyết định.

Taipy là presentation layer của V1 và không chứa core model/business logic.

### 7.7. API

Sentinel được thiết kế API-first để cung cấp các capability của hệ thống cho UI hoặc hệ thống bên ngoài.

API có trách nhiệm:

- Nhận request.
- Validate input.
- Gọi application services.
- Trả về structured result.

Business logic không nằm trực tiếp trong API route.

---

## 8. Phạm vi MVP — Sentinel V1

### 8.1. MVP phải có

V1 tập trung vào một vertical slice hoàn chỉnh:

```text
Transaction Data
      ↓
Validation / Preprocessing
      ↓
Behavioral Features
      ↓
Classical Baseline
      ↓
Quantum Enhancement
      ↓
Anomaly / Risk Assessment
      ↓
Decision Support
      ↓
FastAPI
      ↓
Taipy Investigation UI
```

MVP cần chứng minh được:

1. Một transaction có thể được phân tích end-to-end.
2. Classical baseline hoạt động.
3. Quantum pipeline có thể chạy trong môi trường phù hợp.
4. Classical và Quantum có thể được benchmark công bằng.
5. Kết quả có thể được đưa lên API.
6. Investigator có thể xem và hiểu kết quả trên UI.

### 8.2. Không bắt buộc trong MVP

Các thành phần sau có thể để research/future:

- Temporal Transformer phức tạp.
- Quantum Autoencoder.
- FiD-QAE.
- Graph/Temporal Graph Intelligence.
- Real-time streaming ở quy mô production.
- Distributed deployment.
- Automated retraining.
- Enterprise IAM.
- Multi-tenant architecture.

---

## 9. Functional Requirements

### FR-01 — Transaction Input

Hệ thống phải có khả năng tiếp nhận transaction data theo một contract rõ ràng.

### FR-02 — Data Validation

Input phải được kiểm tra về:

- Required fields.
- Data types.
- Missing/invalid values.
- Basic consistency constraints.

### FR-03 — Feature Processing

Hệ thống phải có khả năng tạo behavioral/transaction features từ dữ liệu đầu vào.

### FR-04 — Classical Baseline

Mỗi Quantum experiment phải có Classical baseline phù hợp để so sánh.

### FR-05 — Quantum Analysis

Hệ thống phải có khả năng chạy Quantum anomaly detection pipeline trong phạm vi tài nguyên cho phép.

### FR-06 — Scoring

Hệ thống phải trả về score có định nghĩa rõ ràng và không gây nhầm lẫn về semantic.

### FR-07 — Decision Support

Hệ thống phải chuyển model outputs thành thông tin hỗ trợ investigation/decision.

### FR-08 — API Access

Các capability chính phải có thể được truy cập thông qua API.

### FR-09 — Investigation UI

UI phải hiển thị kết quả theo cách ưu tiên:

```text
Decision
→ Risk / Anomaly
→ Evidence
→ Model Information
→ Quantum Information khi có
```

### FR-10 — Evaluation

Hệ thống phải hỗ trợ đánh giá:

- Detection performance.
- False-positive behavior.
- Classical vs Quantum comparison.
- Resource/cost characteristics.
- Robustness trong phạm vi experiment.

---

## 10. Non-functional Requirements

### NFR-01 — Reproducibility

Experiment và model evaluation phải có khả năng tái lập trong cùng environment và configuration.

### NFR-02 — Modularity

Classical model, Quantum model, feature engineering, service và API phải có boundary rõ ràng.

### NFR-03 — Testability

Core logic phải có thể kiểm thử độc lập với UI.

### NFR-04 — Explainability

Output phải cung cấp đủ context/evidence để người dùng hiểu tại sao một transaction được đánh giá là đáng chú ý trong phạm vi khả năng của model.

### NFR-05 — Performance

V1 phải đo latency và computational cost của pipeline, đặc biệt khi có Quantum component.

### NFR-06 — Scalability

Architecture phải cho phép mở rộng mà không yêu cầu thay đổi toàn bộ application core.

### NFR-07 — Security & Data Handling

Dữ liệu tài chính phải được xử lý theo nguyên tắc tối thiểu hóa dữ liệu, không commit dữ liệu nhạy cảm vào repository và tách data artifacts khỏi source code.

### NFR-08 — Maintainability

Code production phải được tách khỏi notebook/experimental code và tuân thủ project engineering rules.

---

## 11. Constraints

### 11.1. Data Constraints

Hiệu quả của Sentinel phụ thuộc vào:

- Chất lượng dataset.
- Mức độ mất cân bằng.
- Feature availability.
- Label availability.
- Temporal information.
- Behavioral history.

### 11.2. Quantum Constraints

Quantum pipeline bị giới hạn bởi:

- Số qubit.
- Circuit depth.
- Encoding/state preparation.
- Shots.
- Noise.
- Simulator/hardware availability.
- Computational cost.

### 11.3. Research Constraints

Không được đánh giá Quantum chỉ bằng một metric hoặc một experiment thuận lợi.

Benchmark phải giữ fairness về:

- Dataset.
- Preprocessing.
- Feature representation.
- Evaluation split.
- Metric.
- Hyperparameter protocol.
- Computational accounting.

### 11.4. Product Constraints

V1 ưu tiên một vertical slice hoàn chỉnh và demonstrable thay vì cố gắng bao phủ toàn bộ fraud platform.

---

## 12. Success Criteria & Metrics

Thành công của Sentinel không được định nghĩa chỉ bằng việc Quantum model có metric cao hơn Classical.

### 12.1. Detection Metrics

Tùy bài toán và dataset, có thể sử dụng:

- Precision.
- Recall.
- F1-score.
- PR-AUC / Average Precision.
- ROC-AUC khi phù hợp.
- False Positive Rate.
- False Negative Rate.

Với dữ liệu fraud mất cân bằng, Precision-Recall based metrics cần được ưu tiên xem xét thay vì chỉ dựa vào Accuracy.

### 12.2. Behavioral Intelligence Metrics

Đánh giá:

- Khả năng phát hiện behavioral deviation.
- Khả năng phát hiện novelty/anomaly.
- Robustness trước behavioral drift trong phạm vi dataset.
- Chất lượng representation nếu có ground truth/evaluation protocol phù hợp.

### 12.3. Quantum Evaluation

Phải báo cáo đồng thời:

- Detection performance.
- Quantum vs Classical performance.
- Qubit count.
- Circuit depth.
- Shots.
- Noise assumptions.
- Runtime/cost.
- Encoding/state-preparation cost khi có thể đo.
- End-to-end computational cost.

### 12.4. Product Metrics

Đối với investigation interface:

- Thời gian để xác định case đáng chú ý.
- Khả năng truy xuất evidence.
- Tính rõ ràng của decision support.
- Tính nhất quán giữa score và decision.

Các metric UX cụ thể sẽ được xác định chi tiết hơn trong `DESIGN.md`.

### 12.5. Success Definition

Sentinel được xem là đạt mục tiêu V1 khi:

1. Có một end-to-end fraud/anomaly intelligence workflow hoạt động.
2. Classical baseline được xây dựng và đánh giá rõ ràng.
3. Quantum pipeline được tích hợp mà không phá vỡ application architecture.
4. Quantum được đánh giá bằng benchmark công bằng.
5. Có thể xác định rõ Quantum có giá trị, không có giá trị, hoặc chỉ có giá trị trong một điều kiện/vùng dữ liệu cụ thể.
6. Kết quả được đưa tới investigator qua API và UI.
7. Hệ thống có đủ tính modular và reproducible để tiếp tục research.

---

## 13. Roadmap sản phẩm

### V1 — Core Behavioral Fraud Intelligence

```text
Transaction
→ Behavioral Features
→ Classical Baseline
→ Quantum Kernel / OCSVM
→ Scoring
→ Decision Support
→ FastAPI
→ Taipy UI
```

Mục tiêu chính: chứng minh end-to-end product workflow và đánh giá Quantum một cách khoa học.

### V2 — Temporal Behavioral Intelligence

Mở rộng:

```text
Behavior History
→ Temporal Representation
→ Behavioral Embedding
→ Classical / Quantum Anomaly Detection
```

Có thể nghiên cứu temporal encoders và temporal behavioral representation.

### V3 — Advanced Quantum Behavioral Intelligence

Có thể nghiên cứu:

- Quantum Autoencoder.
- FiD-QAE.
- Quantum representation learning.
- Graph/Temporal Graph approaches.
- Uncertainty-aware routing.

Chỉ triển khai khi có hypothesis, experimental evidence và resource justification.

### Future — Behavioral Intelligence Platform

Mục tiêu dài hạn:

```text
Transaction Intelligence
        +
Behavioral Intelligence
        +
Anomaly Detection
        +
Risk Intelligence
        +
Decision Support
        ↓
Behavioral Intelligence API
```

Sentinel có thể trở thành một intelligence layer tích hợp với ngân hàng, fintech, payment systems và các hệ thống financial crime/risk hiện hữu.

---

## 14. Product Principles

### Principle 01 — Classical First

Luôn có Classical baseline phù hợp trước khi đánh giá Quantum.

### Principle 02 — Quantum Where Justified

Quantum chỉ được sử dụng khi có scientific hoặc practical justification.

### Principle 03 — Fair Benchmark

Classical và Quantum phải được so sánh trên cùng một evaluation framework phù hợp.

### Principle 04 — Measure Real Value

Không chỉ đo model metric; phải đo resource cost, end-to-end cost và practical utility.

### Principle 05 — Behavior Before Classification

Ưu tiên hiểu behavioral pattern và deviation thay vì chỉ dựa vào binary fraud classification.

### Principle 06 — Decision Intelligence

Model output là nguyên liệu cho decision support, không phải quyết định cuối cùng trong mọi trường hợp.

### Principle 07 — Research ≠ Production

Experimental code phải được kiểm chứng trước khi trở thành production implementation.

### Principle 08 — API-first

Core intelligence phải có thể được sử dụng độc lập với presentation layer.

### Principle 09 — No Over-engineering

Chỉ xây infrastructure và abstraction khi có nhu cầu thực tế.

### Principle 10 — Scientific Honesty

Nếu Quantum không tốt hơn Classical, Sentinel phải kết luận đúng như vậy.

Nếu advantage chỉ tồn tại trong một điều kiện cụ thể, điều kiện đó phải được nêu rõ.

Nếu chưa đủ bằng chứng, kết luận phải được ghi nhận là:

- `[Giả thuyết]`
- `[Suy luận]`
- `[Chưa xác minh]`

---

## 15. Ranh giới với các tài liệu khác

PRD này xác định **what và why** của Sentinel.

Các câu hỏi chi tiết hơn được chuyển sang các tài liệu tiếp theo:

| Câu hỏi | Tài liệu |
|---|---|
| Sentinel xây gì và tại sao? | `PRD.md` |
| Người dùng trải nghiệm thế nào? | `DESIGN.md` |
| System được cấu trúc ra sao? | `ARCHITECTURE.md` |
| Data được tổ chức thế nào? | `SCHEMA.md` |
| Team phải tuân thủ nguyên tắc nào? | `RULES.md` |
| Dùng công nghệ gì? | `TECH_STACK.md` |
| Team là ai? | `TEAM.md` |
| Ai sở hữu phần nào? | `ROLES.md` |
| Team làm việc thế nào? | `WORKFLOW.md` |

PRD không thay thế các tài liệu trên và không đi sâu vào implementation details.

---

## 16. Tóm tắt

Sentinel là một hệ thống **Behavioral Fraud Intelligence** nhằm phát hiện hành vi tài chính bất thường, định lượng anomaly/risk signals và hỗ trợ investigation/decision-making.

Sản phẩm kết hợp Classical AI/ML và Quantum Machine Learning theo nguyên tắc:

```text
Classical First
        ↓
Quantum Where Justified
        ↓
Fair Benchmark
        ↓
Measure Real Value
        ↓
Decision Intelligence
        ↓
Product
```

Mục tiêu của Sentinel không phải chứng minh rằng Quantum luôn tốt hơn Classical.

Mục tiêu là xác định một cách khoa học và thực tiễn:

> **Quantum có thể đóng góp ở đâu trong Behavioral Fraud Intelligence, đóng góp bao nhiêu, với chi phí nào, và contribution đó có đủ giá trị để trở thành một capability của sản phẩm hay không.**

Đó là nền tảng để Sentinel phát triển từ một research/competition system thành một **Behavioral Intelligence layer** có khả năng tích hợp vào các hệ thống tài chính thực tế.
