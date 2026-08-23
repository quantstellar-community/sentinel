# Sentinel — Team

> **Phiên bản:** V1.0  
> **Trạng thái:** Draft chính thức cho giai đoạn phát triển V1  
> **Dự án:** Quantstellar Sentinel  
> **Phạm vi:** Cấu trúc team, functional roles, responsibility boundaries và cơ chế phối hợp.

---

## 1. Mục đích

`TEAM.md` mô tả cấu trúc tổ chức của team Sentinel ở cấp độ functional responsibility.

Tài liệu tập trung vào:

- Team composition.
- Các nhóm responsibility chính.
- Ranh giới ownership.
- Cách các role phối hợp với nhau.
- Cách kết nối Research → Engineering → Product.

`TEAM.md` không phải CV của thành viên và không nhằm mô tả chi tiết background cá nhân.

---

# 2. Team Mission

Team Sentinel xây dựng một hệ thống **Behavioral Fraud Intelligence** nhằm phát hiện các hành vi và giao dịch bất thường trong môi trường tài chính, kết hợp Classical AI/ML với Quantum Computing/Quantum Machine Learning khi có cơ sở khoa học và giá trị đo lường được.

Team theo đuổi nguyên tắc:

```text
Financial Problem
      ↓
Behavioral Intelligence
      ↓
Classical Baseline
      ↓
Quantum Enhancement Where Justified
      ↓
Fair Benchmark
      ↓
Validated Result
      ↓
Decision Support
      ↓
Product
```

Mục tiêu của team không phải chứng minh Quantum luôn tốt hơn Classical, mà là xác định **Quantum có thể đóng góp giá trị thực tế ở đâu trong bài toán fraud/behavioral intelligence**.

---

# 3. Team Structure

Sentinel V1 có các functional responsibility chính:

```text
                    SENTINEL TEAM
                         │
        ┌────────────────┼────────────────┐
        │                │                │
   Data Engineering   Classical ML    Quantum Computing
        │                │             ┌───┴───┐
        │                │          Quantum 1  Quantum 2
        │                │
        └────────────────┼────────────────┘
                         │
                    MLOps / Engineering
                         │
                    UI & API
                         │
                      Product
```

Các responsibility này là **functional roles**, không bắt buộc tương ứng một-một với số lượng thành viên.

Một thành viên có thể:

- Có một Primary Role.
- Có một hoặc nhiều Secondary Responsibilities.
- Phối hợp với các role khác trong cùng một workflow.

Điều này phù hợp với team nhỏ và tránh tạo organizational overhead không cần thiết.

---

# 4. Functional Roles

## 4.1. Data Engineering

### Mục tiêu

Đảm bảo dữ liệu đầu vào cho Sentinel có chất lượng, cấu trúc và pipeline phù hợp với behavioral modeling.

### Trách nhiệm chính

- Data ingestion.
- Data cleaning.
- Data preprocessing.
- Data validation.
- Dataset organization.
- Feature data preparation.
- Data lineage ở mức cần thiết.
- Kiểm tra data leakage.
- Chuẩn bị dữ liệu cho Classical và Quantum pipeline.

### Output

```text
Raw Data
    ↓
Processed Data
    ↓
Feature-ready Data
```

### Phối hợp

Data Engineering làm việc trực tiếp với:

- Classical ML.
- Quantum roles.
- MLOps.
- UI/API khi cần data contract.

---

# 5. Classical Machine Learning

## 5.1. Mục tiêu

Xây dựng behavioral/anomaly detection baseline và các phương pháp Classical làm chuẩn so sánh cho Quantum.

### Trách nhiệm chính

- Behavioral feature modeling.
- Classical anomaly detection.
- Baseline construction.
- One-Class learning.
- Model training.
- Evaluation.
- Hyperparameter experiments.
- Error analysis.
- Feature ablation.
- Benchmark với Quantum methods.

### Các hướng có thể sử dụng

Tùy formulation và dataset:

- Isolation Forest.
- One-Class SVM.
- Classical kernel methods.
- Các anomaly detection methods phù hợp khác.

### Nguyên tắc

Classical ML là **baseline bắt buộc**, không phải phần phụ của Quantum research.

Flow:

```text
Behavioral Representation
        ↓
Classical Baseline
        ↓
Evaluation
        ↓
Quantum Comparison
```

---

# 6. Quantum 1

## 6.1. Mục tiêu

Phụ trách hướng nghiên cứu và phát triển Quantum model chính của Sentinel.

### Trách nhiệm chính

- Quantum method formulation.
- Quantum feature map / encoding.
- Quantum kernel research.
- Quantum OCSVM pipeline.
- Quantum circuit design.
- Quantum experiment implementation.
- Classical-vs-Quantum model comparison.

### Hướng V1 ưu tiên

```text
Behavioral Representation
        ↓
Quantum Feature Map
        ↓
Quantum Kernel
        ↓
OCSVM
        ↓
Behavioral Anomaly Score
```

### Nguyên tắc

Quantum 1 không tự quyết định rằng Quantum method là tốt hơn.

Mọi claim phải đi qua:

```text
Hypothesis
→ Classical Baseline
→ Quantum Experiment
→ Fair Benchmark
→ Conclusion
```

---

# 7. Quantum 2

## 7.1. Mục tiêu

Hỗ trợ Quantum research theo hướng experimental validation, resource analysis và các hướng Quantum bổ sung.

### Trách nhiệm chính

- Quantum experiment support.
- Circuit/resource analysis.
- Simulator configuration.
- Noise analysis.
- Shot analysis.
- Hardware feasibility analysis khi có điều kiện.
- Quantum ablation.
- Reproducibility.
- Hỗ trợ đánh giá scalability.

### Resource dimensions

Khi phù hợp cần theo dõi:

```text
Qubits
Circuit Depth
Shots
Backend
Noise
Runtime
Encoding / State Preparation Cost
```

### Phối hợp

Quantum 2 làm việc chặt với:

- Quantum 1.
- Classical ML.
- MLOps.

Mục tiêu là đảm bảo Quantum result không chỉ có model metric mà còn có **resource context**.

---

# 8. MLOps

## 8.1. Mục tiêu

Đảm bảo research và model pipeline có thể được tái chạy, kiểm thử và đưa vào application một cách có kiểm soát.

### Trách nhiệm chính

- Environment reproducibility.
- Dependency management.
- Experiment configuration.
- Model artifact management.
- Training/inference pipeline.
- Testing infrastructure.
- Evaluation pipeline.
- Runtime configuration.
- CI/CD khi cần.
- Monitoring foundations khi product stage yêu cầu.

### Nguyên tắc

MLOps không được trở thành infrastructure project độc lập.

Ưu tiên:

```text
Need
→ Minimal Infrastructure
→ Reproducibility
→ Automation Where Valuable
```

Không xây distributed infrastructure nếu workload chưa yêu cầu.

---

# 9. UI & API

## 9.1. Mục tiêu

Xây application interface để người dùng có thể quan sát, điều tra và sử dụng kết quả của Sentinel.

Role này bao gồm hai boundary:

```text
API
+
Presentation
```

### API responsibilities

- FastAPI endpoints.
- Request validation.
- Response serialization.
- API contracts.
- Application service integration.
- Error handling ở API boundary.

### UI responsibilities

- Taipy application.
- Plotly visualizations.
- Investigation workflow.
- Transaction analysis.
- Behavioral visualization.
- Risk/anomaly presentation.
- Decision-support interface.

### Architecture

```text
Taipy + Plotly
       ↓
FastAPI + Pydantic
       ↓
Application Services
       ↓
Sentinel Core
```

### Nguyên tắc

UI không tự tính:

- Fraud score.
- Confidence.
- Risk score.
- Quantum score.
- Model explanation.

UI chỉ trình bày kết quả được cung cấp bởi backend/core.

---

# 10. Role Ownership Matrix

| Responsibility | Data Eng. | Classical ML | Quantum 1 | Quantum 2 | MLOps | UI/API |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Data ingestion | Primary | Support | Support | Support | Support | - |
| Data preprocessing | Primary | Primary | Support | Support | Support | - |
| Behavioral features | Primary | Primary | Support | Support | - | - |
| Classical baseline | - | Primary | Support | Support | Support | - |
| Quantum model | - | Support | Primary | Primary/Support | Support | - |
| Quantum resources | - | Support | Primary | Primary | Support | - |
| Experiment reproducibility | Support | Support | Support | Primary | Primary | - |
| Model pipeline | Support | Primary | Primary | Support | Primary | - |
| API | - | - | - | - | Support | Primary |
| UI | - | - | - | - | - | Primary |
| Visualization | Support | Primary | Support | Support | - | Primary |
| Product presentation | - | Support | Support | Support | Support | Primary |

> **Lưu ý:** Matrix thể hiện functional ownership, không phải quyền hạn tuyệt đối. Các component quan trọng vẫn cần cross-review.

---

# 11. Primary và Secondary Ownership

Vì team có quy mô nhỏ, mỗi thành viên nên có:

```text
1 Primary Responsibility
+
0–1 Secondary Responsibility
```

Primary responsibility nghĩa là người đó chịu trách nhiệm chính về:

- Thiết kế.
- Implementation.
- Documentation.
- Validation.
- Handover.

Secondary responsibility nghĩa là người đó có thể hỗ trợ nhưng không nhất thiết là owner cuối cùng.

Điều này giúp tránh:

```text
Everyone owns everything
```

và đồng thời tránh:

```text
One person knows everything
```

---

# 12. Cross-functional Workflow

## 12.1. Data → ML

```text
Data Engineering
      ↓
Validated Dataset
      ↓
Classical ML
      ↓
Behavioral Representation
```

Classical ML phản hồi yêu cầu về:

- Feature quality.
- Temporal information.
- Missing data.
- Leakage risk.

---

## 12.2. Classical → Quantum

```text
Classical Baseline
      ↓
Behavioral Representation
      ↓
Quantum Hypothesis
      ↓
Quantum Method
      ↓
Benchmark
```

Quantum team không nên tự tạo một problem formulation hoàn toàn tách khỏi Classical baseline nếu mục tiêu là fair comparison.

---

## 12.3. ML/Quantum → MLOps

```text
Validated Model
      ↓
Pipeline
      ↓
Configuration
      ↓
Reproducible Execution
      ↓
Application Integration
```

---

## 12.4. Core → API → UI

```text
Core Result
    ↓
Application Service
    ↓
FastAPI
    ↓
Taipy
    ↓
Investigation / Decision Support
```

---

# 13. Research Collaboration

Mọi research idea quan trọng nên đi qua:

```text
Problem
→ Hypothesis
→ Mathematical Formulation
→ Classical Baseline
→ Quantum Method
→ Fair Benchmark
→ Ablation
→ Resource Analysis
→ Scientific Conclusion
→ Product Evaluation
```

Không để một role tự phát triển một research component quan trọng mà không có baseline hoặc evaluation plan.

---

# 14. Decision Ownership

Các quyết định được phân loại:

### Domain/Product Decision

Ví dụ:

- Sentinel giải quyết vấn đề gì?
- User target là ai?
- Output nào có giá trị?

→ Team/Product leadership.

### ML Decision

Ví dụ:

- Feature representation.
- Classical baseline.
- Evaluation metric.

→ Classical ML + relevant team members.

### Quantum Research Decision

Ví dụ:

- Quantum feature map.
- Quantum kernel.
- Circuit design.
- Quantum experiment.

→ Quantum roles + Classical ML review.

### Architecture Decision

Ví dụ:

- API boundary.
- Module boundary.
- Persistence.
- Deployment architecture.

→ Architecture/technical lead + relevant owners.

### UI Decision

Ví dụ:

- Investigation workflow.
- Dashboard hierarchy.
- Visualization.

→ UI/API owner + Product requirements.

---

# 15. Review Principle

Không phải mọi thay đổi đều cần toàn team review.

Review intensity phụ thuộc impact:

```text
Small Implementation
→ Role Review

Model / Feature Change
→ ML Review

Quantum Method Change
→ Quantum + ML Review

Schema/API Change
→ Relevant Architecture + API Review

Major Architecture Change
→ Team-level Review
```

---

# 16. Communication Principle

Communication nên tập trung vào:

```text
What changed?
Why?
Evidence?
Impact?
Next action?
```

Thay vì chỉ báo:

> “Đã làm xong.”

Ví dụ một research update tốt:

```text
Hypothesis:
Quantum Kernel có thể cải thiện separation của behavioral representation.

Experiment:
Quantum Kernel + OCSVM
vs
RBF OCSVM

Result:
[Chưa xác minh]

Next:
Kiểm tra robustness và resource cost.
```

---

# 17. Handoff Principle

Khi một role bàn giao component cho role khác, cần có tối thiểu:

- Mục đích.
- Input.
- Output.
- Interface.
- Configuration.
- Known limitations.
- Test/evaluation status.

Ví dụ:

```text
Feature Engineering
        ↓
Input Contract
Output Contract
Feature Version
Known Limitations
        ↓
ML Owner
```

---

# 18. Documentation Ownership

Các role phải cập nhật documentation liên quan đến responsibility của mình.

| Documentation | Primary Contributors |
|---|---|
| `PRD.md` | Product/Team Lead |
| `DESIGN.md` | UI/API + Product |
| `ARCHITECTURE.md` | Technical/Architecture owners |
| `SCHEMA.md` | Data + ML + API |
| `RULES.md` | Team/Technical owners |
| `TECH_STACK.md` | Technical owners |
| `TEAM.md` | Team Lead |
| `ROLES.md` | Team Lead + members |
| `WORKFLOW.md` | Team |

Documentation phải phản ánh implementation thực tế.

---

# 19. Team Operating Model

Sentinel hoạt động theo mô hình:

```text
Research
   ↕
Engineering
   ↕
Product
```

Không tách ba nhóm này thành silos.

Ví dụ:

```text
Quantum Research
      ↓
Benchmark
      ↓
Engineering Feasibility
      ↓
Product Utility
```

Một research result chỉ trở thành product capability khi:

```text
Scientific Validity
+
Engineering Feasibility
+
User Value
```

được xác nhận ở mức phù hợp.

---

# 20. Team Non-goals

Team structure không nhằm:

- Tạo hierarchy phức tạp.
- Tạo title cho đẹp.
- Ép mỗi thành viên chỉ làm một loại việc.
- Tách team thành nhiều silo.
- Biến MLOps thành infrastructure team độc lập.
- Biến Quantum thành một team tách khỏi financial problem.
- Để UI/API tự quyết định business logic.

---

# 21. Team Principles

Sentinel team tuân thủ các nguyên tắc:

### 1. Ownership rõ ràng

Mỗi responsibility phải có owner.

### 2. Collaboration bắt buộc ở boundary

Các component giao tiếp với nhau phải có cross-functional review khi cần.

### 3. Evidence over opinion

Technical/research decisions nên dựa trên experiment, benchmark hoặc requirement.

### 4. Classical First

Classical ML là baseline và không bị xem là “less important” vì project có Quantum.

### 5. Quantum Where Justified

Quantum chỉ được đưa vào nơi có scientific motivation và measurable value.

### 6. Product Awareness

Research phải luôn có consideration về khả năng trở thành usable capability.

### 7. No Over-engineering

Team nhỏ → architecture và workflow phải tương xứng với team size.

---

# 22. Team Success Criteria

Team được xem là vận hành tốt khi:

```text
Responsibilities rõ ràng
        +
Boundaries rõ ràng
        +
Research reproducible
        +
Engineering maintainable
        +
Communication effective
        +
Product direction thống nhất
```

Không đánh giá team chỉ bằng số lượng code hoặc số lượng Quantum experiment.

---

# 23. Summary

Cấu trúc team Sentinel V1 được xây quanh sáu functional responsibility:

```text
Data Engineering
Classical Machine Learning
Quantum 1
Quantum 2
MLOps
UI & API
```

Các responsibility này kết nối thành một pipeline:

```text
Data
 ↓
Behavioral Representation
 ↓
Classical Baseline
 ↓
Quantum Enhancement
 ↓
Evaluation
 ↓
Reproducible Pipeline
 ↓
API
 ↓
Investigation UI
 ↓
Decision Support
```

Mục tiêu của team là biến một research idea thành một hệ thống có thể:

```text
Understand Behavior
        ↓
Detect Anomaly
        ↓
Quantify Evidence
        ↓
Evaluate Risk
        ↓
Support Investigation
        ↓
Create Measurable Value
```

**Sentinel không phải là một nhóm Quantum làm thêm một bài fraud detection.**

Sentinel là một team xây dựng **Behavioral Fraud Intelligence**, trong đó Quantum là một computational capability được nghiên cứu và sử dụng khi nó thực sự có cơ sở để tạo ra giá trị.
