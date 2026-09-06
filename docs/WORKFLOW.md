# Sentinel — Workflow

> **Phiên bản:** V1.0  
> **Trạng thái:** Draft chính thức cho giai đoạn phát triển V1  
> **Dự án:** Quantstellar Sentinel  
> **Phạm vi:** Research workflow, data/ML workflow, development workflow, integration workflow, review, testing, documentation và release.

---

## 1. Mục đích

`WORKFLOW.md` định nghĩa cách team Sentinel biến một problem hoặc requirement thành một capability có thể nghiên cứu, kiểm chứng, tích hợp và trình bày.

Nếu:

- `PRD.md` → Sentinel cần xây gì và tại sao.
- `DESIGN.md` → người dùng trải nghiệm như thế nào.
- `ARCHITECTURE.md` → system được cấu trúc ra sao.
- `SCHEMA.md` → data được tổ chức thế nào.
- `RULES.md` → những nguyên tắc nào phải tuân thủ.
- `TECH_STACK.md` → sử dụng công nghệ nào.
- `TEAM.md` → team được tổ chức thế nào.
- `ROLES.md` → responsibility của từng role là gì.

thì:

> **`WORKFLOW.md` → team biến những yêu cầu đó thành một hệ thống hoạt động như thế nào.**

Workflow V1 phải đủ nghiêm túc để hỗ trợ research và engineering, nhưng không được tạo overhead không cần thiết cho team nhỏ.

---

# 2. Workflow Philosophy

Sentinel sử dụng workflow:

```text
Problem
  ↓
Understand
  ↓
Formulate
  ↓
Build Baseline
  ↓
Research / Experiment
  ↓
Validate
  ↓
Integrate
  ↓
Expose
  ↓
Investigate
  ↓
Release
```

Nguyên tắc:

```text
Problem First
→ Classical First
→ Quantum Where Justified
→ Fair Benchmark
→ Validate
→ Productize
```

Không bắt đầu workflow bằng technology.

---

# 3. Workflow Layers

Workflow của Sentinel gồm các lớp:

```text
1. Product / Requirement Workflow
2. Research Workflow
3. Data Workflow
4. ML Workflow
5. Quantum Workflow
6. Engineering Workflow
7. API / UI Integration Workflow
8. Testing / Validation Workflow
9. Documentation Workflow
10. Release Workflow
```

Các layer liên kết với nhau nhưng không phải mọi task đều phải đi qua toàn bộ pipeline.

---

# 4. End-to-End Sentinel Workflow

Workflow tổng thể:

```text
Requirement / Problem
        ↓
Problem Definition
        ↓
Data Assessment
        ↓
Behavioral Representation
        ↓
Classical Baseline
        ↓
Quantum Hypothesis
        ↓
Quantum Experiment
        ↓
Fair Benchmark
        ↓
Scientific Validation
        ↓
Engineering Validation
        ↓
Core Integration
        ↓
FastAPI
        ↓
Taipy + Plotly
        ↓
Investigation / Decision Support
        ↓
Testing
        ↓
Documentation
        ↓
Release / Demo
```

Một component không cần đi đến production chỉ vì experiment đã chạy được.

---

# 5. Workflow 01 — Requirement / Task Intake

Mọi task quan trọng bắt đầu bằng việc xác định:

```text
What?
Why?
Who?
Expected Output?
Success Criteria?
```

Ví dụ:

```text
What?
Improve behavioral anomaly detection.

Why?
Current representation does not capture temporal behavior adequately.

Who?
Classical ML + Data Engineering.

Output?
New behavioral feature representation.

Success?
Improved validation under the same evaluation protocol.
```

Không bắt đầu implementation nếu problem chưa đủ rõ để biết output cần là gì.

---

# 6. Task Classification

Task được phân loại đơn giản:

### Research Task

Có hypothesis hoặc uncertainty khoa học.

Ví dụ:

```text
Quantum Kernel có cải thiện behavioral separation không?
```

### Engineering Task

Có implementation requirement rõ.

Ví dụ:

```text
Thêm endpoint lấy transaction detail.
```

### Data Task

Liên quan đến data pipeline hoặc data quality.

### Product/UI Task

Liên quan đến user workflow hoặc presentation.

### Architecture Task

Thay đổi boundary hoặc structure của system.

Mỗi loại task có validation khác nhau.

---

# 7. Workflow 02 — Problem Definition

Trước khi model hoặc code, phải xác định:

```text
Problem
Input
Output
User
Constraints
Evaluation
```

Đối với Sentinel:

```text
Transaction History
      ↓
Behavioral Representation
      ↓
Deviation / Novelty
      ↓
Anomaly
      ↓
Risk
      ↓
Decision Support
```

Fraud không mặc định được formulation thành binary classification.

---

# 8. Workflow 03 — Data Workflow

Data workflow:

```text
Source
 ↓
Raw
 ↓
Validation
 ↓
Preprocessing
 ↓
Processed
 ↓
Feature Engineering
 ↓
Feature Validation
 ↓
Model Input
```

## 8.1. Data Validation

Kiểm tra khi phù hợp:

- Schema.
- Missing values.
- Invalid values.
- Duplicates.
- Distribution.
- Temporal consistency.
- Leakage.

## 8.2. Data Version

Khi experiment quan trọng cần ghi nhận:

```text
Dataset Version
Feature Version
Processing Configuration
```

---

# 9. Workflow 04 — Behavioral Representation

Sentinel ưu tiên behavioral representation thay vì chỉ transaction-level classification.

Workflow:

```text
Transaction History
        ↓
Context Construction
        ↓
Behavioral Features
        ↓
Behavioral Representation
        ↓
Model Input
```

Representation phải phản ánh đúng information available tại thời điểm prediction.

Nếu có temporal features:

```text
Past
 ↓
Current Context
 ↓
Representation
```

Không sử dụng future information.

---

# 10. Workflow 05 — Classical Baseline

Mọi Quantum research direction quan trọng phải có Classical baseline phù hợp.

Workflow:

```text
Behavioral Representation
        ↓
Classical Model
        ↓
Validation
        ↓
Baseline Result
```

Classical baseline core V1 (theo `SENTINEL_THESIS.md`):

- Logistic Regression.
- LightGBM.
- Classical OCSVM.

XGBoost và Isolation Forest không nằm trong classical baseline core V1. Classical kernel method (RBF Kernel + OCSVM) có thể được dùng làm classical counterpart cho Quantum Kernel + OCSVM.

Baseline phải đủ mạnh và hợp lý để comparison có ý nghĩa.

---

# 11. Workflow 06 — Quantum Research

Quantum workflow:

```text
Problem
 ↓
Quantum Hypothesis
 ↓
Why Quantum?
 ↓
Quantum Formulation
 ↓
Encoding
 ↓
Circuit / Kernel
 ↓
Experiment
 ↓
Resource Analysis
 ↓
Benchmark
 ↓
Conclusion
```

Không được đảo thành:

```text
Quantum Model
 ↓
Find Problem
```

---

# 12. Workflow 07 — Quantum Kernel + OCSVM

Hướng Quantum V1 có thể được triển khai theo:

```text
Behavioral Representation
        ↓
Quantum Feature Map
        ↓
Quantum Kernel
        ↓
OCSVM
        ↓
Anomaly Score
        ↓
Assessment
```

Classical comparison:

```text
Behavioral Representation
        ↓
Classical Kernel
        ↓
OCSVM
        ↓
Anomaly Score
```

Hai pipeline phải dùng evaluation protocol tương thích.

---

# 13. Workflow 08 — Fair Benchmark

Benchmark:

```text
Same Dataset
Same Split
Same Representation
Same Evaluation Protocol
        ↓
Classical
vs
Quantum
```

Khi có khác biệt bắt buộc, phải ghi rõ.

Không được:

- Chọn dataset có lợi cho một method mà không có justification.
- Dùng metric khác nhau để tạo advantage.
- Tối ưu một baseline nhiều hơn method còn lại mà không ghi nhận.
- Cherry-pick favorable result.

---

# 14. Workflow 09 — Quantum Resource Analysis

Nếu Quantum result được dùng cho research claim, xem xét:

```text
Qubits
Circuit Depth
Shots
Backend
Noise
Runtime
Encoding / State Preparation
```

Phân biệt:

```text
Ideal Simulation
        ≠
Noisy Simulation
        ≠
Real Hardware
```

Quantum performance không được đánh giá chỉ bằng model metric khi claim liên quan đến computational advantage.

---

# 15. Workflow 10 — Experiment

Một experiment quan trọng nên có:

```text
Experiment ID
Hypothesis
Dataset Version
Feature Version
Model Configuration
Random Seed khi phù hợp
Execution Environment
Metrics
Results
Resource Information
Conclusion
```

Kết quả phải được phân loại:

```text
Validated
Partially Validated
Inconclusive
Failed
```

Negative result vẫn được lưu giữ.

---

# 16. Workflow 11 — Experiment → Production

Research code không được tự động trở thành production code.

Pipeline:

```text
Research Prototype
      ↓
Validation
      ↓
Stable Implementation
      ↓
Unit / Integration Test
      ↓
Benchmark
      ↓
Core Integration
```

Chỉ sau bước này model/component mới được xem xét đưa vào application.

---

# 17. Workflow 12 — Engineering Development

Engineering workflow:

```text
Task
 ↓
Understand Existing Boundary
 ↓
Design Change
 ↓
Implement
 ↓
Test
 ↓
Review
 ↓
Integrate
 ↓
Document
```

Không nên sửa architecture lớn trong một implementation task nhỏ nếu không có requirement.

---

# 18. Workflow 13 — Feature Development

Feature development:

```text
Requirement
 ↓
Acceptance Criteria
 ↓
Interface / Schema
 ↓
Implementation
 ↓
Tests
 ↓
Integration
 ↓
UI/API
 ↓
Documentation
```

Một feature được xem là hoàn thành khi:

```text
Implemented
+
Tested
+
Integrated
+
Documented
```

---

# 19. Workflow 14 — API Development

API workflow:

```text
Use Case
 ↓
Request / Response Contract
 ↓
Pydantic Schema
 ↓
FastAPI Endpoint
 ↓
Application Service
 ↓
Core
 ↓
Integration Test
 ↓
API Documentation
```

API route không chứa:

- Model training.
- Feature engineering.
- Quantum circuit construction.
- Complex decision logic.

---

# 20. Workflow 15 — UI Development

UI workflow:

```text
User Need
 ↓
Investigation Flow
 ↓
UI Structure
 ↓
Taipy Component
 ↓
Plotly Visualization
 ↓
API Integration
 ↓
Interaction Validation
```

UI phải lấy data từ API/application contract thay vì truy cập trực tiếp model internals.

---

# 21. Investigation Workflow

Sentinel UI ưu tiên investigation workflow:

```text
Alert / Transaction
        ↓
Anomaly Overview
        ↓
Behavioral Context
        ↓
Evidence
        ↓
Model Assessment
        ↓
Historical Comparison
        ↓
Investigator Interpretation
        ↓
Decision Support
```

UI không biến model score thành final decision một cách tự động.

---

# 22. Workflow 16 — Testing

Testing chia thành:

```text
Unit Test
Integration Test
API Test
Data Validation
Model Evaluation
Quantum Experiment Validation
UI Verification
```

Không một loại test nào thay thế hoàn toàn loại khác.

---

# 23. Workflow 17 — Model Evaluation

Model evaluation:

```text
Dataset
 ↓
Evaluation Protocol
 ↓
Model
 ↓
Metrics
 ↓
Error Analysis
 ↓
Ablation
 ↓
Robustness
 ↓
Conclusion
```

Với fraud/anomaly detection, metric phải phù hợp với problem.

Không dùng Accuracy làm metric duy nhất cho dữ liệu mất cân bằng.

---

# 24. Workflow 18 — Leakage Check

Trước khi tin vào result:

```text
Data Leakage Check
        ↓
Temporal Leakage Check
        ↓
Feature Leakage Check
        ↓
Target Leakage Check
        ↓
Re-run Evaluation
```

Nếu phát hiện leakage:

```text
Invalidate Result
        ↓
Fix Pipeline
        ↓
Re-run Experiment
```

Không giữ result cũ chỉ vì nó tốt hơn.

---

# 25. Workflow 19 — Code Review

Trước khi merge một change quan trọng:

```text
Author
 ↓
Self-check
 ↓
Tests
 ↓
Reviewer
 ↓
Feedback
 ↓
Fix
 ↓
Approval
 ↓
Merge
```

Reviewer tập trung vào:

- Correctness.
- Scope.
- Architecture.
- Tests.
- Security.
- Scientific validity nếu có.
- Regression risk.

---

# 26. Workflow 20 — Architecture Change

Architecture change:

```text
Problem
 ↓
Existing Architecture Limitation
 ↓
Proposed Change
 ↓
Trade-offs
 ↓
Impact
 ↓
Review
 ↓
Implementation
 ↓
Documentation
```

Không thay đổi architecture lớn chỉ để giải quyết một implementation inconvenience nhỏ.

---

# 27. Workflow 21 — Schema / API Change

Khi thay đổi schema hoặc API:

```text
Identify Contract
 ↓
Impact Analysis
 ↓
Update Schema
 ↓
Update Producer
 ↓
Update Consumer
 ↓
Tests
 ↓
Documentation
```

Đặc biệt kiểm tra:

```text
Core
↔
API
↔
UI
```

Không để consumer tiếp tục dùng contract cũ mà không biết.

---

# 28. Workflow 22 — Dependency Change

Dependency workflow:

```text
Need
 ↓
Evaluate Alternatives
 ↓
Compatibility Check
 ↓
Add / Upgrade
 ↓
Run Tests
 ↓
Check Runtime
 ↓
Update Lockfile
 ↓
Document if Significant
```

Không thêm dependency chỉ vì nó phổ biến.

---

# 29. Workflow 23 — Documentation

Documentation update workflow:

```text
Change
 ↓
Identify Affected Docs
 ↓
Update Documentation
 ↓
Check Consistency
 ↓
Review
```

Ví dụ:

```text
Architecture Change
→ ARCHITECTURE.md
→ TECH_STACK.md nếu technology thay đổi
→ SCHEMA.md nếu contract thay đổi
→ RULES.md nếu rule thay đổi
```

Documentation phải phản ánh implementation.

---

# 30. Workflow 24 — Release / Demo

Release workflow:

```text
Feature Freeze
 ↓
Test
 ↓
Model Evaluation
 ↓
API Verification
 ↓
UI Verification
 ↓
Documentation Check
 ↓
Environment Check
 ↓
Demo Preparation
 ↓
Release
```

Trước demo phải xác nhận:

```text
Application runs
+
Core model runs
+
API works
+
UI works
+
Data is safe
+
Results are reproducible enough
```

---

# 31. Workflow 25 — Competition Workflow

Trong context AI-Quantum Challenge:

```text
Challenge Requirement
        ↓
Problem Mapping
        ↓
Sentinel Formulation
        ↓
Prototype
        ↓
Classical Baseline
        ↓
Quantum Experiment
        ↓
Benchmark
        ↓
Demo
        ↓
Presentation
```

Ưu tiên:

```text
Clear Problem
+
Strong Baseline
+
Credible Quantum Contribution
+
Working Demo
+
Clear Story
```

Không ưu tiên complexity chỉ để làm project trông lớn hơn.

---

# 32. Research Artifact Lifecycle

Một research artifact đi qua:

```text
Idea
 ↓
Hypothesis
 ↓
Experiment
 ↓
Raw Result
 ↓
Analysis
 ↓
Validation
 ↓
Conclusion
 ↓
Documentation
 ↓
Candidate for Integration
```

Mọi experiment chưa được validate phải được xem là experimental.

---

# 33. Model Lifecycle

```text
Candidate
 ↓
Experiment
 ↓
Baseline Comparison
 ↓
Validation
 ↓
Approved
 ↓
Integrated
 ↓
Evaluated
 ↓
Retired / Replaced
```

Không coi model là permanent.

---

# 34. Quantum Model Lifecycle

```text
Quantum Hypothesis
 ↓
Prototype
 ↓
Simulator
 ↓
Noise Evaluation
 ↓
Resource Analysis
 ↓
Classical Benchmark
 ↓
Hardware Feasibility
 ↓
Validated / Rejected
 ↓
Integration Decision
```

Hardware execution không phải điều kiện bắt buộc để một Quantum method có research value, nhưng mọi claim phải phản ánh đúng execution context.

---

# 35. Decision Gates

Sentinel sử dụng các gate đơn giản.

## Gate A — Problem Gate

```text
Problem rõ?
User rõ?
Output rõ?
Evaluation rõ?
```

Nếu chưa → chưa implementation.

## Gate B — Baseline Gate

```text
Classical baseline tồn tại?
```

Nếu Quantum research → phải có justification nếu không có baseline.

## Gate C — Validation Gate

```text
Result reproducible?
Benchmark fair?
Leakage checked?
```

## Gate D — Integration Gate

```text
Scientific validity?
Engineering feasibility?
Product utility?
```

## Gate E — Release Gate

```text
Tests pass?
Application works?
Documentation updated?
Demo reproducible?
```

---

# 36. Failure Workflow

Nếu một task hoặc experiment thất bại:

```text
Failure
 ↓
Identify Cause
 ↓
Classify
 ├── Data
 ├── Model
 ├── Quantum
 ├── Engineering
 └── Integration
 ↓
Fix / Revise Hypothesis
 ↓
Re-run
```

Không che giấu failure.

Negative result là một phần của research history.

---

# 37. Uncertainty Workflow

Khi evidence chưa đủ:

```text
Result
 ↓
Evidence Assessment
 ↓
Confidence / Uncertainty
 ↓
Classification
```

Có thể sử dụng:

```text
[Giả thuyết]
[Suy luận]
[Chưa xác minh]
```

Không biến uncertainty thành false precision.

---

# 38. Productization Workflow

Một research result chỉ được productize khi:

```text
Scientific Validity
+
Engineering Feasibility
+
Operational Reproducibility
+
User Utility
```

Flow:

```text
Research Result
      ↓
Validation
      ↓
Core Module
      ↓
API Contract
      ↓
UI
      ↓
User Evaluation
      ↓
Product Capability
```

---

# 39. Workflow Ownership

| Workflow | Primary Owner | Main Contributors |
|---|---|---|
| Data workflow | Data Engineering | Classical ML, MLOps |
| Classical ML | Classical ML | Data, MLOps |
| Quantum research | Quantum 1 | Quantum 2, Classical ML |
| Quantum validation | Quantum 2 | Quantum 1, MLOps |
| Pipeline/reproducibility | MLOps | ML, Quantum, Data |
| API | UI/API | MLOps, Core owners |
| UI | UI/API | ML, Product |
| Architecture | Technical owners | Relevant roles |
| Documentation | Relevant owner | Team |
| Release/Demo | Team | All roles |

---

# 40. Minimum Workflow for Small Tasks

Không phải task nào cũng cần full workflow.

Một bug nhỏ:

```text
Issue
 ↓
Fix
 ↓
Test
 ↓
Review
 ↓
Merge
```

Một research task:

```text
Problem
 ↓
Hypothesis
 ↓
Experiment
 ↓
Benchmark
 ↓
Conclusion
```

Một feature:

```text
Requirement
 ↓
Implementation
 ↓
Test
 ↓
Integration
 ↓
Documentation
```

Workflow phải proportional với complexity.

---

# 41. Anti-patterns

## 41.1. Quantum First

```text
Quantum Model
→ Find Problem
```

Không được khuyến khích.

## 41.2. UI First Without Contract

```text
Build UI
→ Invent API/data
```

Tránh.

## 41.3. Research → Production Directly

Prototype không tự động trở thành production.

## 41.4. Metric Chasing

Thay đổi protocol chỉ để cải thiện metric.

## 41.5. Documentation Last

Đợi đến cuối project mới viết docs.

## 41.6. Infrastructure First

Xây infrastructure lớn trước khi có workload.

## 41.7. Hero Workflow

Một người duy nhất hiểu toàn bộ pipeline.

---

# 42. Workflow Health Check

Định kỳ kiểm tra:

```text
Are responsibilities clear?
Are interfaces stable?
Are experiments reproducible?
Are baselines fair?
Is Quantum justified?
Is UI using real backend data?
Are docs synchronized?
Is infrastructure proportional?
```

Nếu câu trả lời là “không”, workflow cần được điều chỉnh.

---

# 43. Final Sentinel Workflow

Workflow cốt lõi của Sentinel có thể tóm tắt:

```text
                    PROBLEM
                       │
                       ▼
               Problem Definition
                       │
                       ▼
                  Data Pipeline
                       │
                       ▼
             Behavioral Representation
                       │
              ┌────────┴────────┐
              ▼                 ▼
      Classical Baseline   Quantum Hypothesis
              │                 │
              │                 ▼
              │          Quantum Experiment
              │                 │
              │          Resource Analysis
              │                 │
              └────────┬────────┘
                       ▼
                 Fair Benchmark
                       │
                       ▼
               Scientific Validation
                       │
                       ▼
              Engineering Validation
                       │
                       ▼
                    Core
                       │
                       ▼
                    FastAPI
                       │
                       ▼
                Taipy + Plotly
                       │
                       ▼
              Investigation UI
                       │
                       ▼
               Decision Support
                       │
                       ▼
                 Documentation
                       │
                       ▼
                    Release
```

Đây là workflow reference của Sentinel V1.

Nguyên tắc cuối cùng:

> **Không tối ưu workflow để tạo ra nhiều code hơn. Tối ưu workflow để biến một financial problem thành một capability có thể kiểm chứng, vận hành và tạo ra giá trị.**
