# Sentinel

### Behavioral Fraud Intelligence

Sentinel là nền tảng **Behavioral Fraud Intelligence** tập trung vào việc học hành vi bình thường của hệ thống, phát hiện các sai lệch có ý nghĩa và chuyển chúng thành các tín hiệu bất thường/risk có thể giải thích.

Ứng dụng đầu tiên của Sentinel là **phát hiện gian lận trong thanh toán trực tuyến**. Về dài hạn, kiến trúc được định hướng có thể mở rộng sang AML, cybersecurity, data-center monitoring, aerospace telemetry và các hệ thống động khác.

> **Trạng thái:** Early research & pre-implementation foundation.

Sentinel hiện tập trung vào problem framing, research direction, evaluation methodology và architectural foundation. Production pipeline, public API, deployed quantum circuits và operational decision system chưa được xem là hoàn thiện.

---

## 1. Problem

Cách tiếp cận truyền thống thường mô hình hóa fraud detection như:

```text
Transaction → Fraud / Non-Fraud
```

Sentinel tiếp cận bài toán theo hướng behavioral intelligence:

```text
Transaction History
        ↓
Behavioral Context
        ↓
Behavioral Representation
        ↓
Expected / Normal Behavior
        ↓
Deviation
        ↓
Anomaly
        ↓
Risk
        ↓
Decision Support
```

Nguyên tắc cốt lõi:

> **Learn normal behavior first; detect meaningful deviations second.**

Anomaly không mặc định đồng nghĩa với fraud. Sentinel vì vậy tách biệt **anomaly detection**, **risk assessment** và **final decision**.

---

## 2. Initial Use Case

Sentinel V1 tập trung vào **card-not-present và digital-payment fraud**.

Đây là môi trường phù hợp để nghiên cứu behavioral intelligence vì có:

- Class imbalance nghiêm trọng.
- Fraud pattern thay đổi theo thời gian.
- Temporal behavior.
- Quan hệ giữa transaction và các entity liên quan.
- Chi phí đáng kể của false positive và false negative.
- Yêu cầu về explainability và latency.

V1 hướng tới **research và controlled evaluation**, không phải hệ thống tự động authorize/decline giao dịch thực tế.

### Initial Objectives

1. Xây dựng Classical behavioral/anomaly baseline đáng tin cậy.
2. Đánh giá Quantum-enhanced methods dưới điều kiện benchmark công bằng.
3. Phát hiện deviation khỏi behavioral pattern bình thường.
4. Tạo anomaly/risk signals có thể kiểm tra và giải thích.
5. Xây dựng architecture có thể tái sử dụng cho các domain khác.

---

## 3. Architecture

Sentinel được tổ chức theo các lớp chính:

```text
Event / Transaction Data
        ↓
Data & Context Layer
        ↓
Behavioral Representation
        ↓
Normal / Expected Behavior
        ↓
Deviation Analysis
        ↓
Anomaly Intelligence
        ↓
Risk / Decision Support
```

Quantum được đặt như một **research enhancement layer**:

```text
Behavioral Representation
        ↓
Classical Baseline
        ↓
Quantum Representation / Similarity
        ↓
Fair Benchmark
        ↓
Validated Intelligence
```

Chi tiết kiến trúc được trình bày trong [`ARCHITECTURE.md`](ARCHITECTURE.md).

---

## 4. Classical-First, Quantum Where Justified

Sentinel không giả định Quantum tốt hơn Classical.

Mọi Quantum approach phải được đánh giá cùng với:

- Scientific motivation.
- Classical baseline.
- Encoding / state preparation.
- Circuit cost.
- Qubit count và circuit depth.
- Shots và noise.
- Hardware feasibility.
- Scalability.
- End-to-end computational cost.
- Practical utility.

Hướng nghiên cứu Quantum V1 ưu tiên **Quantum Kernel + OCSVM** và các phương pháp behavioral representation/similarity phù hợp.

Nguyên tắc:

```text
Problem
→ Hypothesis
→ Classical Baseline
→ Quantum Method
→ Fair Benchmark
→ Resource Analysis
→ Scientific Conclusion
→ Product Evaluation
```

Không claim **quantum advantage** chỉ dựa trên theoretical speedup hoặc một metric tốt hơn.

---

## 5. Evaluation

Do fraud detection thường có class imbalance rất lớn, accuracy không được sử dụng như tiêu chí chính duy nhất.

Evaluation có thể bao gồm:

- AUPRC / PR-AUC.
- ROC-AUC.
- Precision / Recall.
- F1.
- False-positive / false-negative analysis.
- Calibration.
- Robustness.
- Temporal generalization.
- Inference latency.
- Resource requirements.
- Explainability.

Mọi Quantum experiment phải có Classical counterpart phù hợp và ghi nhận execution context:

```text
Dataset / Split
Feature Representation
Model Configuration
Random Seed
Qubits
Circuit Depth
Shots
Noise / Backend
Runtime
```

Chi tiết evaluation rules được quản lý trong [`RULES.md`](RULES.md).

---

## 6. Research Direction

Roadmap hiện tại:

```text
Phase 0 — Research Contract
        ↓
Phase 1 — Classical Behavioral Baseline
        ↓
Phase 2 — Hybrid / Quantum Anomaly Layer
        ↓
Phase 3 — Behavioral State Intelligence
        ↓
Phase 4 — Sentinel Platform
```

### Phase 0 — Research Contract

- Canonical data schema.
- Problem formulation.
- Leakage-safe evaluation protocol.
- Classical baseline definition.

### Phase 1 — Classical Behavioral Baseline

- Reproducible data pipeline.
- Behavioral features.
- Classical anomaly detection.
- Evaluation và error analysis.

### Phase 2 — Hybrid / Quantum Anomaly Layer

- Quantum kernels.
- Quantum OCSVM.
- Quantum representation/similarity.
- Noise-aware experiments.
- Fair Classical-vs-Quantum benchmarking.

### Phase 3 — Behavioral State Intelligence

- Temporal behavioral state.
- Entity context.
- Behavioral trajectory.
- Expected-vs-observed deviation.

### Phase 4 — Sentinel Platform

- Reusable behavioral intelligence service.
- Investigation interface.
- Domain adapters.
- Expansion beyond financial fraud.

---

## 7. Dataset Context

Research foundation hiện có thể sử dụng anonymized European credit-card fraud dataset với:

- 284,807 transactions.
- 492 fraud cases.
- Fraud rate khoảng 0.1727%.
- 28 anonymized PCA features.
- Transaction time và amount.
- Binary fraud label.

Dataset phù hợp cho initial benchmark về:

- Classical anomaly detection.
- One-Class learning.
- Quantum-kernel experiments.
- Imbalanced classification.

Tuy nhiên, dataset không có rich customer, merchant, device hoặc identity histories. Vì vậy nó **không đủ để xác thực toàn bộ behavioral-trajectory vision** của Sentinel.

Các kết luận về behavioral intelligence ở quy mô entity/temporal cần dataset giàu context hơn.

---

## 8. Technology

Technology stack V1 được định hướng:

```text
Python 3.12.x
uv
FastAPI
Pydantic
Taipy
Plotly
NumPy
pandas
SciPy
scikit-learn
Qiskit
pytest
Jupyter
```

Vai trò chính:

- **FastAPI + Pydantic** → API boundary.
- **Taipy + Plotly** → investigation UI và visualization.
- **scikit-learn** → Classical ML/anomaly baseline.
- **Qiskit** → Quantum research layer.
- **NumPy / pandas / SciPy** → data/scientific computing.
- **pytest** → testing.
- **uv** → environment và dependency management.

Chi tiết xem [`TECH_STACK.md`](TECH_STACK.md).

---

## 9. Repository Documentation

Các tài liệu chính:

| Document | Mục đích |
|---|---|
| `PRD.md` | Product requirements |
| `DESIGN.md` | Product/UI design |
| `ARCHITECTURE.md` | System architecture |
| `SCHEMA.md` | Data và interface schemas |
| `RULES.md` | Project rules |
| `TECH_STACK.md` | Technology stack |
| `TEAM.md` | Team structure |
| `ROLES.md` | Role responsibilities |
| `WORKFLOW.md` | Research & development workflow |
| `CONTRIBUTING.md` | Contribution guidelines |

---

## 10. Design Principles

### Classical First

Classical baseline phải được xây dựng và đánh giá trước khi kết luận Quantum có giá trị.

### Behavioral Intelligence

Tập trung vào behavior, context và deviation thay vì chỉ classification.

### Anomaly ≠ Fraud

Anomaly là tín hiệu cần được đánh giá; không phải mọi anomaly đều là fraud.

### Fair Benchmark

Quantum và Classical phải được so sánh dưới evaluation protocol hợp lý và reproducible.

### Evidence Over Hype

Kết quả phải đi cùng limitations, cost, noise và practical utility.

### Explainability

Kết quả cần có evidence đủ để hỗ trợ investigation và decision-making.

### No Over-engineering

Infrastructure và abstraction chỉ được thêm khi workload hoặc product requirement thực sự cần.

---

## 11. Responsible Use

Fraud intelligence có thể ảnh hưởng trực tiếp đến legitimate users và financial decisions.

Sentinel research vì vậy phải quan tâm đến:

- False positives và customer friction.
- False negatives.
- Threshold selection.
- Human review.
- Data privacy.
- Dataset bias.
- Model drift.
- Adversarial adaptation.
- Auditability.

Cho đến khi reliability và governance được xác thực đầy đủ, Sentinel nên được xem là **decision-support system**, không phải autonomous financial decision maker.

---

## 12. Current Status

Sentinel hiện ở giai đoạn:

```text
Research Foundation
        ↓
Architecture / Documentation
        ↓
Environment Setup
        ↓
Core Implementation
        ↓
Classical Baseline
        ↓
Quantum Research
        ↓
Application Integration
```

Một capability chỉ được xem là validated khi có đủ evidence phù hợp về:

```text
Scientific Validity
+
Engineering Feasibility
+
Reproducibility
+
Practical Utility
```

---

## 13. Vision

Sentinel hướng tới một behavioral intelligence layer có khả năng:

```text
Observe
  ↓
Understand Behavior
  ↓
Learn Normality
  ↓
Detect Deviation
  ↓
Quantify Risk
  ↓
Explain Evidence
  ↓
Support Decisions
```

Mục tiêu cuối cùng không phải là xây một hệ thống **Quantum vì Quantum**.

> **Sentinel xây Behavioral Fraud Intelligence trước; Quantum được sử dụng ở nơi nó có thể chứng minh giá trị.**
