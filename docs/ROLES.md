# Sentinel — Roles & Responsibilities

> **Phiên bản:** V1.0  
> **Trạng thái:** Draft chính thức cho giai đoạn phát triển V1  
> **Dự án:** Quantstellar Sentinel  
> **Phạm vi:** Định nghĩa trách nhiệm, ownership, deliverables, interfaces và tiêu chí hoàn thành của từng role.

---

## 1. Mục đích

`ROLES.md` định nghĩa **ai chịu trách nhiệm làm gì** trong Sentinel.

Nếu `TEAM.md` mô tả:

> Team gồm những functional areas nào và phối hợp với nhau ra sao,

thì `ROLES.md` đi sâu hơn vào:

> Mỗi role phải chịu trách nhiệm gì, tạo ra output nào, giao tiếp với role nào và khi nào một nhiệm vụ được xem là hoàn thành.

Tài liệu này được xây dựng ở cấp **functional role**, không tự gán tên cá nhân nếu chưa có thông tin ownership chính thức.

---

# 2. Role Model

Sentinel V1 có sáu functional roles:

```text
1. Data Engineering
2. Classical Machine Learning
3. Quantum 1
4. Quantum 2
5. MLOps
6. UI & API
```

Sáu role này không đồng nghĩa với sáu thành viên.

Với team nhỏ:

```text
1 thành viên
    ↓
1 Primary Role
+
0–1 Secondary Responsibility
```

Một người có thể hỗ trợ nhiều area, nhưng mỗi responsibility quan trọng phải có **Primary Owner**.

---

# 3. Ownership Model

## 3.1. Primary Owner

Primary Owner chịu trách nhiệm chính về:

- Thiết kế component.
- Implementation.
- Testing.
- Documentation.
- Validation.
- Handover.
- Theo dõi technical debt trong phạm vi component.

Primary Owner không có nghĩa là làm mọi thứ một mình.

---

## 3.2. Contributor

Contributor hỗ trợ Primary Owner bằng:

- Research.
- Implementation.
- Review.
- Testing.
- Data analysis.
- Documentation.

---

## 3.3. Reviewer

Reviewer kiểm tra:

- Correctness.
- Compatibility.
- Scientific validity khi có liên quan.
- Architectural consistency.
- Regression risk.

---

# 4. Role 01 — Data Engineering

## 4.1. Mission

Đảm bảo Sentinel có dữ liệu đầu vào đáng tin cậy và pipeline dữ liệu phù hợp cho behavioral intelligence.

## 4.2. Core Responsibilities

### Data ingestion

- Thu nhận dữ liệu từ nguồn được phép sử dụng.
- Chuẩn hóa input format.
- Kiểm tra schema ban đầu.
- Theo dõi data source/version khi cần.

### Data preprocessing

- Cleaning.
- Missing-value handling.
- Type normalization.
- Duplicate handling.
- Data validation.
- Preprocessing reproducibility.

### Dataset management

Tổ chức:

```text
Raw
 ↓
Processed
 ↓
Features
 ↓
Predictions
```

Không trộn các tầng dữ liệu.

### Data quality

Kiểm tra:

- Missingness.
- Invalid values.
- Duplicates.
- Distribution anomalies.
- Data drift khi phù hợp.
- Label quality nếu sử dụng supervised data.

### Leakage prevention

Đặc biệt kiểm tra:

- Temporal leakage.
- Target leakage.
- Feature leakage.

## 4.3. Deliverables

```text
Validated Dataset
Data Processing Pipeline
Data Validation Rules
Dataset Metadata
Data Dictionary / Schema Contribution
```

## 4.4. Interfaces

### Input

```text
Raw / Source Data
```

### Output

```text
Processed Data
Feature-ready Data
Data Metadata
```

### Phối hợp với

- Classical ML.
- Quantum 1.
- Quantum 2.
- MLOps.
- UI/API khi cần contract data.

## 4.5. Done Criteria

Một data pipeline được xem là đủ điều kiện khi:

- Schema rõ ràng.
- Processing reproducible.
- Không có leakage đã biết.
- Data quality checks chạy được.
- Output phù hợp với downstream pipeline.

---

# 5. Role 02 — Classical Machine Learning

## 5.1. Mission

Xây dựng behavioral/anomaly detection baseline và đóng vai trò chuẩn so sánh cho mọi Quantum approach.

## 5.2. Core Responsibilities

### Behavioral modeling

- Xác định behavioral representation.
- Xây dựng transaction-level và contextual features.
- Temporal feature engineering khi phù hợp.
- Similarity/novelty representation khi cần.

### Classical baseline

Classical baseline core V1 (theo `SENTINEL_THESIS.md`):

- Logistic Regression.
- LightGBM.
- Classical OCSVM.

XGBoost và Isolation Forest không nằm trong classical baseline core V1. Classical kernel method (RBF Kernel + OCSVM) có thể được dùng làm classical counterpart cho Quantum Kernel + OCSVM.

Không algorithm nào được mặc định là final method.

### Evaluation

Theo dõi các metric phù hợp với research question, ví dụ:

- Precision.
- Recall.
- F1.
- PR-AUC / Average Precision.
- ROC-AUC.
- False Positive Rate.
- False Negative Rate.

Accuracy không được sử dụng một mình cho bài toán fraud mất cân bằng.

### Error analysis

Phân tích:

```text
False Positive
False Negative
Borderline Cases
Behavioral Drift
```

## 5.3. Deliverables

```text
Behavioral Feature Pipeline
Classical Baseline
Evaluation Pipeline
Benchmark Results
Error Analysis
Ablation Results
```

## 5.4. Interfaces

### Input

```text
Processed Data
```

### Output

```text
Behavioral Representation
Classical Model
Anomaly Scores
Evaluation Results
```

### Phối hợp với

- Data Engineering.
- Quantum 1.
- Quantum 2.
- MLOps.
- UI/API.

## 5.5. Done Criteria

Classical baseline phải:

- Có formulation rõ.
- Có evaluation protocol.
- Có reproducible configuration.
- Có benchmark result.
- Có limitation được ghi nhận.

---

# 6. Role 03 — Quantum 1

## 6.1. Mission

Phụ trách Quantum modeling direction chính của Sentinel và nghiên cứu liệu Quantum có thể cải thiện behavioral anomaly detection trong điều kiện benchmark công bằng hay không.

## 6.2. Core Responsibilities

### Quantum formulation

Xác định:

- Quantum hypothesis.
- Quantum contribution.
- Input representation.
- Encoding strategy.
- Quantum model boundary.

### Quantum Kernel

Hướng V1 ưu tiên:

```text
Behavioral Representation
        ↓
Quantum Feature Map
        ↓
Quantum Kernel
        ↓
OCSVM
        ↓
Anomaly Assessment
```

### Circuit development

Phụ trách:

- Feature map.
- Circuit construction.
- Kernel computation.
- Parameter configuration.
- Simulator execution.

### Classical comparison

Mọi Quantum experiment phải có Classical counterpart phù hợp.

Ví dụ:

```text
Quantum Kernel + OCSVM
vs
RBF Kernel + OCSVM
```

Comparison phải giữ evaluation protocol nhất quán.

## 6.3. Deliverables

```text
Quantum Method Specification
Quantum Circuit / Feature Map
Quantum Kernel Pipeline
Experiment Configuration
Benchmark Results
Research Findings
```

## 6.4. Interfaces

### Input

```text
Behavioral Representation
```

### Output

```text
Quantum Kernel / Model Output
Quantum Experiment Metadata
```

### Phối hợp với

- Classical ML.
- Quantum 2.
- MLOps.
- Data Engineering.

## 6.5. Done Criteria

Quantum method chỉ được xem là validated khi:

- Hypothesis rõ.
- Encoding rõ.
- Classical baseline tồn tại.
- Benchmark reproducible.
- Resource assumptions được ghi nhận.
- Kết luận phản ánh đúng evidence.

---

# 7. Role 04 — Quantum 2

## 7.1. Mission

Phụ trách experimental validation, resource analysis, reproducibility và hỗ trợ các Quantum research direction bổ sung.

## 7.2. Core Responsibilities

### Quantum resource analysis

Theo dõi khi phù hợp:

```text
Qubits
Circuit Depth
Shots
Backend
Noise
Runtime
Encoding / State Preparation
```

### Noise analysis

Phân biệt:

```text
Ideal Simulation
Noisy Simulation
Real Hardware
```

Không gộp ba execution context thành một loại result.

### Experimental validation

- Re-run experiments.
- Kiểm tra stability.
- Ablation.
- Seed/configuration tracking.
- So sánh simulator/backend.

### Hardware feasibility

Nếu có hardware access:

- Backend compatibility.
- Qubit availability.
- Circuit constraints.
- Noise impact.
- Execution cost.

## 7.3. Deliverables

```text
Resource Analysis
Noise Analysis
Quantum Experiment Validation
Reproducibility Configuration
Hardware Feasibility Notes
```

## 7.4. Interfaces

### Input

```text
Quantum Method
Experiment Configuration
Behavioral Representation
```

### Output

```text
Validated Quantum Results
Resource Metadata
Execution Metadata
```

### Phối hợp với

- Quantum 1.
- Classical ML.
- MLOps.

## 7.5. Done Criteria

Experiment phải có:

- Execution context rõ.
- Configuration rõ.
- Resource metadata phù hợp.
- Có thể tái chạy.
- Kết luận không vượt quá evidence.

---

# 8. Role 05 — MLOps

## 8.1. Mission

Biến research/model pipeline thành workflow reproducible, testable và có thể tích hợp vào application.

## 8.2. Core Responsibilities

### Environment

Quản lý:

```text
Python
uv
Dependencies
Configuration
Runtime Environment
```

### Training / inference pipeline

Hỗ trợ:

```text
Data
 ↓
Features
 ↓
Model
 ↓
Prediction
 ↓
Assessment
```

### Reproducibility

Theo dõi khi cần:

- Dataset version.
- Feature version.
- Model version.
- Configuration.
- Random seed.
- Experiment metadata.

### Testing

Phối hợp xây:

- Unit tests.
- Integration tests.
- Pipeline tests.
- API tests.
- Evaluation execution.

### CI/CD

Chỉ triển khai automation khi project requirement cần.

## 8.3. Deliverables

```text
Reproducible Environment
Training Pipeline
Inference Pipeline
Configuration
Model Artifacts
Test Infrastructure
Experiment Runtime Support
```

## 8.4. Interfaces

### Input

```text
Data Pipeline
ML Models
Quantum Models
Configuration
```

### Output

```text
Runnable Pipelines
Model Artifacts
Evaluation Artifacts
Runtime Configuration
```

### Phối hợp với

- Data Engineering.
- Classical ML.
- Quantum 1.
- Quantum 2.
- UI/API.

## 8.5. Done Criteria

Pipeline phải:

- Chạy được từ clean environment.
- Có configuration rõ.
- Có test phù hợp.
- Có model/version metadata khi cần.
- Không phụ thuộc notebook để chạy production flow.

---

# 9. Role 06 — UI & API

## 9.1. Mission

Xây application boundary và investigation interface để expose Sentinel capabilities cho người dùng.

Role này bao gồm hai responsibility liên kết:

```text
API
+
Presentation UI
```

---

## 9.2. API Responsibilities

### FastAPI

- API routes.
- Request validation.
- Response serialization.
- Error handling.
- Application service integration.
- API documentation.

### Pydantic

- Request schemas.
- Response schemas.
- Contract validation.

### Boundary

```text
HTTP Request
    ↓
FastAPI
    ↓
Application Service
    ↓
Sentinel Core
```

API route không được chứa:

- Feature engineering.
- Model training.
- Quantum circuit logic.
- Complex business logic.

---

## 9.3. UI Responsibilities

### Taipy

Xây:

- Dashboard.
- Investigation workflow.
- Transaction view.
- Behavioral timeline.
- Anomaly visualization.
- Risk context.
- Model result presentation.

### Plotly

Sử dụng cho:

- Interactive charts.
- Behavioral patterns.
- Time-series visualization.
- Distribution visualization.
- Model comparison.

## 9.4. UI Principles

UI phải ưu tiên:

```text
Attention
 ↓
Anomaly / Risk
 ↓
Evidence
 ↓
Behavioral Context
 ↓
Model Details
 ↓
Technical Details
```

UI không được tự tạo:

- Fraud score.
- Risk score.
- Confidence.
- Quantum score.
- Explanation.

## 9.5. Deliverables

```text
FastAPI Application
API Contracts
Taipy Application
Plotly Visualizations
Investigation Views
API/UI Integration
```

## 9.6. Done Criteria

UI/API component phải:

- Có contract rõ.
- Tách presentation khỏi core logic.
- Hiển thị đúng backend result.
- Có error/loading states phù hợp.
- Có API test ở boundary quan trọng.

---

# 10. Cross-role Responsibility Matrix

| Công việc | Data | Classical ML | Quantum 1 | Quantum 2 | MLOps | UI/API |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Data ingestion | **P** | S | S | S | S | - |
| Data validation | **P** | S | S | S | S | - |
| Feature engineering | **P** | **P** | S | S | S | - |
| Classical baseline | - | **P** | S | S | S | - |
| Behavioral modeling | S | **P** | S | S | S | - |
| Quantum method | - | S | **P** | S | S | - |
| Quantum experiment | - | S | **P** | **P** | S | - |
| Resource analysis | - | S | P | **P** | S | - |
| Model pipeline | S | P | P | S | **P** | - |
| Reproducibility | S | S | S | S | **P** | - |
| API | - | - | - | - | S | **P** |
| UI | - | S | S | S | - | **P** |
| Visualization | S | P | S | S | - | **P** |
| Product integration | S | S | S | S | S | **P** |

**P = Primary Owner**  
**S = Support / Contributor**

---

# 11. Role Interaction Map

```text
                Data Engineering
                       │
                       ▼
             Behavioral Representation
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
      Classical ML           Quantum 1
             │                   │
             │              Quantum Method
             │                   │
             │                   ▼
             │              Quantum 2
             │                   │
             └─────────┬─────────┘
                       ▼
                  Evaluation
                       │
                       ▼
                     MLOps
                       │
                       ▼
                  Application
                       │
                 ┌─────┴─────┐
                 ▼           ▼
              FastAPI      Taipy
                 │           │
                 └─────┬─────┘
                       ▼
               Investigation UI
```

---

# 12. Handoff Contracts

Mỗi role khi bàn giao component phải cung cấp tối thiểu:

```text
Purpose
Input
Output
Interface
Configuration
Version
Known Limitations
Test Status
Evaluation Status
```

Ví dụ:

### Data → ML

```text
Dataset
+
Schema
+
Feature Definitions
+
Data Quality Status
+
Leakage Notes
```

### ML → Quantum

```text
Behavioral Representation
+
Feature Version
+
Baseline
+
Evaluation Protocol
```

### Quantum → MLOps

```text
Quantum Model
+
Circuit Configuration
+
Backend/Simulator
+
Resource Metadata
+
Reproduction Instructions
```

### Core → UI/API

```text
API Contract
+
Response Schema
+
Score Semantics
+
Evidence
+
Error States
```

---

# 13. Role Boundaries

## Data Engineering không chịu trách nhiệm

- Quyết định final model.
- Tự quyết định Quantum method.
- Quyết định UI.

## Classical ML không chịu trách nhiệm

- Tự tuyên bố Quantum advantage.
- Tự thay đổi product architecture.
- Định nghĩa UI behavior.

## Quantum 1 không chịu trách nhiệm

- Bỏ qua Classical baseline.
- Tự định nghĩa product value.
- Tuyên bố hardware advantage nếu chưa có evidence.

## Quantum 2 không chịu trách nhiệm

- Chỉ tối ưu circuit mà không xét problem value.
- Gọi simulation là hardware result.
- Tạo infrastructure phức tạp không cần thiết.

## MLOps không chịu trách nhiệm

- Quyết định research hypothesis.
- Thay đổi model semantics.
- Xây infrastructure vượt requirement.

## UI/API không chịu trách nhiệm

- Tính lại model result.
- Tạo fake explanation.
- Chứa business logic.
- Định nghĩa Quantum methodology.

---

# 14. Definition of Done theo Role

Một role chỉ được xem là hoàn thành responsibility khi output của mình:

```text
Implemented
+
Tested
+
Documented
+
Integrated
+
Validated
```

Tùy loại task, “validated” có thể là:

- Unit test.
- Integration test.
- Benchmark.
- Experiment.
- Data validation.
- UI verification.

Không phải mọi task đều yêu cầu cùng một loại validation.

---

# 15. Role Escalation

Khi một task vượt khỏi responsibility hiện tại:

```text
Identify Boundary
       ↓
Notify Relevant Owner
       ↓
Agree Interface
       ↓
Implement
       ↓
Cross-review
```

Không tự ý thay đổi responsibility của role khác nếu thay đổi đó ảnh hưởng đến contract.

---

# 16. Research Ownership Rule

Một research component quan trọng phải có:

```text
Primary Research Owner
+
At least One Reviewer
```

Đặc biệt đối với:

- Quantum method.
- Novel feature representation.
- Major model architecture.
- Evaluation protocol.
- Quantum advantage claim.

Reviewer phải đủ độc lập để phát hiện:

- Leakage.
- Benchmark bias.
- Incorrect interpretation.
- Unsupported claims.

---

# 17. Product Ownership Rule

Model output chỉ trở thành product capability khi có:

```text
Scientific Validity
+
Engineering Feasibility
+
User Utility
```

Ví dụ:

```text
Quantum Kernel performs better
```

chưa đủ.

Cần tiếp tục hỏi:

```text
Có reproducible không?
Có resource feasible không?
Có scale được không?
Có giúp investigator không?
Có tạo decision value không?
```

---

# 18. Anti-Patterns

Team cần tránh:

### Everyone owns everything

Không có owner rõ ràng.

### Role silos

Một role không hiểu downstream impact của mình.

### Quantum isolation

Quantum research không kết nối với financial problem.

### UI-driven architecture

Architecture được quyết định bởi UI framework.

### Infrastructure-first

Xây MLOps/infrastructure lớn trước khi có workload thực.

### Notebook dependency

Production pipeline phụ thuộc notebook.

### Metric-only ownership

Một role chỉ tối ưu metric mà bỏ qua practical utility.

### Hero developer

Một thành viên trở thành single point of failure.

---

# 19. Role Evolution

Role có thể thay đổi khi Sentinel trưởng thành.

Ví dụ:

```text
V1
Functional Roles
     ↓
Validated Product
     ↓
Larger Team
     ↓
More Specialized Ownership
```

Không nên tạo specialization trước khi workload chứng minh nhu cầu.

---

# 20. Role Summary

| Role | Primary Focus | Core Output |
|---|---|---|
| Data Engineering | Data pipeline & quality | Validated data |
| Classical ML | Behavioral baseline | Classical model + benchmark |
| Quantum 1 | Quantum modeling | Quantum method |
| Quantum 2 | Quantum validation | Resource/experiment analysis |
| MLOps | Reproducibility & pipelines | Runnable ML/Quantum pipeline |
| UI & API | Product interface | API + Investigation UI |

---

# 21. Final Principle

Mỗi role có một trách nhiệm riêng, nhưng Sentinel chỉ tạo ra giá trị khi các role hoạt động như **một hệ thống thống nhất**:

```text
Data
 ↓
Behavior
 ↓
Classical Intelligence
 ↓
Quantum Enhancement
 ↓
Validation
 ↓
Operational Pipeline
 ↓
API
 ↓
Investigation
 ↓
Decision Support
```

Không role nào là “phụ”.

Không role nào tự mình định nghĩa toàn bộ Sentinel.

Và đặc biệt:

> **Quantum là một responsibility quan trọng của team, nhưng financial/behavioral problem mới là trung tâm của toàn bộ system.**

Đó là nguyên tắc để giữ Sentinel vừa có chiều sâu nghiên cứu, vừa có engineering discipline, vừa có khả năng trở thành một product thực sự.
