# Sentinel — Rules & Engineering Guidelines

> **Phiên bản:** V1.0  
> **Trạng thái:** Draft chính thức cho giai đoạn phát triển V1  
> **Dự án:** Quantstellar Sentinel  
> **Vai trò tài liệu:** Quy định các nguyên tắc, engineering constraints và chuẩn làm việc cần được tuân thủ trong quá trình phát triển Sentinel.

---

## 1. Mục đích

`RULES.md` định nghĩa các nguyên tắc mà mọi implementation, research experiment, API, UI và documentation của Sentinel phải tôn trọng.

Nếu:

- `PRD.md` trả lời **Sentinel cần xây gì và tại sao**,
- `DESIGN.md` trả lời **người dùng trải nghiệm như thế nào**,
- `ARCHITECTURE.md` trả lời **system được cấu trúc ra sao**,
- `SCHEMA.md` trả lời **data được tổ chức thế nào**,

thì `RULES.md` trả lời:

> **“Trong quá trình xây Sentinel, chúng ta phải tuân thủ những nguyên tắc nào?”**

Rules không thay thế code style tool, linter hoặc framework documentation. Nó định nghĩa **engineering principles và project constraints** ở cấp độ dự án.

---

# 2. Core Principles

## RULE-01 — Classical First

Classical methods là baseline và nền tảng của Sentinel.

Mọi Quantum approach phải được đánh giá cùng một Classical baseline phù hợp.

Không bắt đầu research bằng:

> “Quantum model nào có thể dùng?”

Mà phải bắt đầu bằng:

> “Financial/behavioral bottleneck nào đáng giải quyết, và Quantum có thể đóng góp gì?”

---

## RULE-02 — Quantum Where Justified

Quantum không được sử dụng chỉ vì Sentinel là một Quantum Finance project.

Một Quantum component phải có:

- Scientific motivation.
- Problem formulation.
- Hypothesis.
- Classical baseline.
- Quantum method.
- Evaluation protocol.
- Resource analysis.
- Practical/research justification.

Nếu Quantum không tạo ra giá trị có thể chứng minh, Classical approach được ưu tiên.

---

## RULE-03 — Fair Benchmark

Classical và Quantum phải được benchmark một cách công bằng.

Khi so sánh, cần kiểm soát phù hợp:

- Dataset.
- Data split.
- Preprocessing.
- Feature representation.
- Evaluation metrics.
- Hyperparameter protocol.
- Relevant computational cost.

Không được cố tình xây một Classical baseline yếu để làm Quantum trông tốt hơn.

---

## RULE-04 — Measure Real Value

Không đánh giá Quantum chỉ bằng một model metric.

Khi phù hợp, cần xem xét:

```text
Accuracy / Detection Performance
+
Encoding / State Preparation
+
Circuit Cost
+
Qubits
+
Depth
+
Shots
+
Noise
+
Runtime
+
End-to-End Cost
+
Practical Utility
```

Theoretical speedup không tự động đồng nghĩa với end-to-end quantum advantage.

---

## RULE-05 — Scientific Honesty

Mọi kết luận phải phản ánh đúng evidence.

Nếu:

- Quantum tốt hơn → chỉ ra điều kiện và evidence.
- Quantum kém hơn → ghi nhận rõ.
- Advantage chỉ tồn tại trong một regime → nêu rõ regime.
- Chưa đủ evidence → không đưa ra strong claim.

Các trạng thái chưa chắc chắn phải được đánh dấu khi cần:

```text
[Giả thuyết]
[Suy luận]
[Chưa xác minh]
```

---

# 3. Product Rules

## RULE-06 — Behavior Before Classification

Sentinel ưu tiên behavioral intelligence thay vì chỉ binary fraud classification.

Core mental model:

```text
Transaction History
→ Behavioral Representation
→ Normal Behavior Space
→ Deviation / Novelty
→ Anomaly
→ Risk
→ Decision Support
```

Classification có thể là một component, nhưng không được định nghĩa toàn bộ product identity.

---

## RULE-07 — Decision Support, Not Blind Automation

Model output không mặc định là final decision.

```text
Model Output
    ↓
Assessment
    ↓
Evidence
    ↓
Decision Policy
    ↓
Decision Support
```

Sentinel phải ưu tiên human-in-the-loop trong investigation context.

---

## RULE-08 — Evidence Before Conclusion

Một anomaly/risk result phải có context/evidence phù hợp khi hệ thống có khả năng cung cấp.

Không chỉ hiển thị:

```text
Fraud = True
```

mà hướng tới:

```text
What is abnormal?
Why?
Compared with what?
How significant?
What should be reviewed?
```

---

## RULE-09 — No Fake Explainability

Không được tạo explanation chỉ để UI trông dễ hiểu.

Explanation/evidence phải có nguồn từ:

- Input data.
- Feature pipeline.
- Model output.
- Explicit decision rules.

UI không được tự bịa model explanation.

---

## RULE-10 — No Metric Inflation

Không thêm score/metric chỉ để dashboard có vẻ “AI” hơn.

Mỗi metric phải có:

- Semantic rõ ràng.
- Source rõ ràng.
- Decision value hoặc analytical value.

Ví dụ:

Không tự gọi raw anomaly score là `Confidence`.

Không tạo `Quantum Score` nếu tên đó không mô tả đúng measurement.

---

# 4. Architecture Rules

## RULE-11 — UI Is Presentation Layer

Taipy là presentation/reference UI layer V1.

UI không chứa:

- Core business logic.
- Feature engineering.
- Model inference.
- Quantum circuit logic.
- Risk policy.

Flow:

```text
Taipy
 ↓
API Client
 ↓
FastAPI
 ↓
Application Services
 ↓
Core
```

---

## RULE-12 — API Boundary Must Be Preserved

FastAPI là application/integration boundary.

API route chỉ nên:

- Nhận request.
- Validate input.
- Gọi application service.
- Trả response.

Không đặt:

- Model computation.
- Feature engineering.
- Quantum logic.
- Complex decision logic

trực tiếp trong route.

---

## RULE-13 — Application Orchestrates; Models Compute

Responsibility phải được tách:

```text
Application Service
→ Orchestrate

Feature Layer
→ Transform data

Classical / Quantum Model
→ Compute

Assessment / Decision Layer
→ Interpret

API
→ Expose

UI
→ Present
```

Không để một module làm tất cả.

---

## RULE-14 — Classical Must Remain Independent

Sentinel phải tiếp tục hoạt động nếu Quantum backend unavailable.

```text
Quantum unavailable
        ↓
Classical pipeline
        ↓
Sentinel remains functional
```

Không được tạo dependency khiến toàn bộ product fail chỉ vì Quantum path không available.

---

## RULE-15 — Quantum Is a Computational Layer

Quantum không định nghĩa financial semantics.

Quantum module cung cấp computational/model output.

Các khái niệm:

- Fraud.
- Risk.
- Investigation.
- Decision

được định nghĩa ở domain/application layer.

---

## RULE-16 — No Premature Microservices

Không tách module thành microservice chỉ vì:

- Module có tên khác nhau.
- Có Classical và Quantum.
- Muốn architecture trông enterprise.

V1 ưu tiên:

```text
Modular Monolith
+
Clear Boundaries
+
API-first
```

Chỉ tách service/process khi workload hoặc product requirement thực sự yêu cầu.

---

## RULE-17 — No Premature Infrastructure

Không mặc định thêm:

- Kubernetes.
- Service mesh.
- Kafka.
- Distributed workers.
- Complex orchestration.
- Enterprise IAM.
- Large-scale cloud infrastructure.

Architecture chỉ được mở rộng khi có measurable requirement hoặc bottleneck.

---

# 5. Data Rules

## RULE-18 — Raw Data ≠ Derived Data

Luôn phân biệt:

```text
Raw Data
≠
Processed Data
≠
Features
≠
Model Output
≠
Assessment
≠
Decision
```

Không đưa derived model outputs vào raw transaction schema.

---

## RULE-19 — Data Contracts Must Be Explicit

Mọi API/data boundary quan trọng phải có contract rõ ràng.

Contract cần có semantic về:

- Field.
- Type.
- Required/optional.
- Meaning.
- Range khi có.
- Version khi cần.

Không dựa vào implicit assumptions giữa các module.

---

## RULE-20 — Scores Must Have Semantic

Mọi score phải xác định:

- Nó đo cái gì.
- Được tạo bởi method nào.
- Range là gì nếu có.
- Higher/lower có ý nghĩa gì nếu có.

Không đổi tên score để làm nó nghe “thông minh” hơn.

---

## RULE-21 — Confidence Must Be Earned

Không tạo `confidence` field nếu Sentinel chưa có phương pháp confidence/uncertainty hợp lệ.

Raw score không mặc định là confidence.

Uncertainty phải có:

```text
Method
+
Interpretation
+
Appropriate calibration/evaluation
```

---

## RULE-22 — Traceability

Khi phù hợp, model result/assessment phải có khả năng truy nguyên về:

```text
Decision
 ↓
Assessment
 ↓
Model
 ↓
Features
 ↓
Processed Data
 ↓
Raw Input
```

Metadata có thể gồm:

- `transaction_id`
- `model_name`
- `model_version`
- `feature_version`
- `configuration_version`
- execution timestamp

---

## RULE-23 — No Sensitive Data in Repository

Không commit:

- Sensitive financial data.
- Credentials.
- API keys.
- Private datasets.
- Unnecessary PII.

Sample/demo data phải được anonymize hoặc sanitize khi cần.

---

# 6. Machine Learning Rules

## RULE-24 — Baseline Before Optimization

Không tối ưu Quantum model trước khi có baseline rõ ràng.

Research sequence:

```text
Problem
→ Baseline
→ Hypothesis
→ Quantum Method
→ Benchmark
→ Ablation
→ Resource Analysis
→ Conclusion
```

---

## RULE-25 — Reproducible Evaluation

Evaluation phải cố gắng cố định:

- Dataset/version.
- Split.
- Random seed khi phù hợp.
- Feature pipeline.
- Evaluation metrics.
- Model configuration.

Thay đổi protocol phải được ghi nhận.

---

## RULE-26 — Imbalanced Fraud Data

Với fraud dataset mất cân bằng, không sử dụng Accuracy làm metric duy nhất.

Khi phù hợp, xem xét:

- Precision.
- Recall.
- F1.
- PR-AUC / Average Precision.
- ROC-AUC.
- False Positive Rate.
- False Negative Rate.

Metric cuối cùng phải phù hợp với research question.

---

## RULE-27 — Temporal Leakage Must Be Avoided

Nếu bài toán sử dụng temporal information, không được để future information leak vào historical behavioral representation hoặc training/evaluation split.

Đặc biệt phải kiểm tra:

```text
Training Period
    <
Validation Period
    <
Test Period
```

khi temporal evaluation là một phần của experiment.

---

## RULE-28 — Feature Leakage Must Be Avoided

Feature không được sử dụng information mà tại thời điểm prediction thực tế chưa tồn tại.

Mọi derived feature quan trọng phải xác định source và time availability khi cần.

---

# 7. Quantum Rules

## RULE-29 — Quantum Hypothesis First

Không xây quantum circuit trước rồi mới tìm problem.

Mỗi Quantum experiment cần bắt đầu bằng:

```text
Problem
→ Hypothesis
→ Why Quantum?
→ Method
→ Baseline
→ Experiment
```

---

## RULE-30 — Encoding Is Part of the Cost

Không bỏ qua:

- Data encoding.
- State preparation.
- Feature map construction.

Khi đánh giá end-to-end cost, encoding/state preparation phải được xem xét phù hợp.

---

## RULE-31 — Resource Accounting

Quantum experiment nên ghi nhận khi có thể:

```text
Qubits
Circuit Depth
Shots
Backend
Noise
Runtime
Encoding Cost
```

Không báo cáo model performance mà hoàn toàn bỏ qua resource context nếu resource là một phần của research claim.

---

## RULE-32 — No Quantum Advantage by Metric Alone

Không tuyên bố:

> “Quantum Advantage”

chỉ vì:

```text
Quantum metric > Classical metric
```

Cần xem xét cả:

```text
Performance
+
Cost
+
Scalability
+
Noise
+
End-to-End Pipeline
```

---

## RULE-33 — Quantum Reproducibility

Quantum experiment phải ghi nhận khi phù hợp:

- Backend/simulator.
- Number of qubits.
- Circuit configuration.
- Shots.
- Noise assumptions.
- Seed khi framework hỗ trợ.
- Feature map/encoding configuration.

---

## RULE-34 — Hardware Claims Must Be Explicit

Phải phân biệt:

```text
Simulation
≠
Noisy Simulation
≠
Real Quantum Hardware
```

Không gọi simulation result là hardware result.

---

# 8. Research Rules

## RULE-35 — Research Code Is Experimental

Notebook có thể:

- Thử nghiệm.
- Visualize.
- Debug.
- Prototype.

Nhưng notebook không phải production module.

---

## RULE-36 — Promotion Requires Validation

Research code chỉ được đưa vào production sau khi:

```text
Experiment
→ Validation
→ Test
→ Benchmark
→ Stable Implementation
```

---

## RULE-37 — Ablation Matters

Khi một component được claim là quan trọng, cần xem xét ablation phù hợp.

Ví dụ:

```text
Full Model
vs
Without Quantum Component
vs
Without Behavioral Feature Group
```

Ablation phải phục vụ hypothesis thực tế.

---

## RULE-38 — Negative Results Are Valid

Nếu experiment cho thấy:

```text
Quantum < Classical
```

đó vẫn là một scientific result.

Không được:

- Cherry-pick favorable experiments.
- Bỏ qua negative result.
- Thay evaluation protocol chỉ vì kết quả không đẹp.

---

# 9. API Rules

## RULE-39 — Stable Public Contracts

API response phải ưu tiên semantic ổn định.

Internal implementation có thể thay đổi nhưng public contract chỉ thay đổi có kiểm soát.

---

## RULE-40 — Validate at the Boundary

Input validation phải xảy ra ở API/data boundary trước khi data đi sâu vào core.

Nhưng domain/application layer vẫn phải bảo vệ invariant của chính nó.

---

## RULE-41 — No Business Logic in Schemas

Schema dùng để:

- Validate.
- Serialize.
- Deserialize.
- Define contract.

Schema không phải nơi chứa toàn bộ application logic.

---

# 10. UI Rules

## RULE-42 — Investigation First

UI phải ưu tiên:

```text
Attention
→ Risk / Anomaly
→ Evidence
→ Behavioral Context
→ Model Details
→ Technical Details
```

---

## RULE-43 — Progressive Disclosure

Technical details chỉ xuất hiện khi người dùng cần.

Investigator không cần nhìn:

```text
Qubit Count
Circuit Depth
Shots
```

trên màn hình chính nếu những thông tin đó không phục vụ quyết định.

---

## RULE-44 — Quantum Must Not Dominate the UI

Quantum là capability, không phải product identity.

Không thiết kế UI khiến người dùng mặc định hiểu:

> Quantum = Better.

---

## RULE-45 — UI Must Not Invent Data

UI chỉ hiển thị:

- API result.
- Explicit local UI state.
- Backend-provided evidence.

Không tự tạo:

- Risk score.
- Confidence.
- Explanation.
- Quantum result.

---

# 11. Testing Rules

## RULE-46 — Test the Core

Core business logic phải có test độc lập với UI.

---

## RULE-47 — Test Boundaries

Ưu tiên test:

```text
API
↔
Services
↔
Features
↔
Models
```

đặc biệt với data contracts.

---

## RULE-48 — Evaluation Is Not Unit Testing

Model performance evaluation không thay thế unit/integration tests.

Cả hai đều cần thiết nhưng phục vụ mục tiêu khác nhau.

```text
Tests
→ Does the system behave correctly?

Evaluation
→ Does the model solve the intended problem?
```

---

## RULE-49 — Test Reproducibility

Critical experiments phải có cách tái chạy rõ ràng.

Configuration, seed và dataset version phải được ghi nhận khi phù hợp.

---

# 12. Code Organization Rules

## RULE-50 — Responsibility-Based Modules

Module nên được tổ chức theo responsibility thay vì chỉ theo framework.

Ví dụ:

```text
domain/
features/
models/
services/
api/
```

---

## RULE-51 — Avoid God Modules

Không tạo một module chứa đồng thời:

```text
Data loading
+
Feature engineering
+
Model training
+
Quantum circuits
+
API
+
Decision logic
```

Nếu một file/class làm quá nhiều responsibility, phải xem xét tách boundary.

---

## RULE-52 — Avoid Premature Abstraction

Không tạo abstraction chỉ vì:

> “Có thể sẽ cần trong tương lai.”

Abstraction cần có consumer/use case thực tế hoặc architectural justification.

---

## RULE-53 — Keep Research and Product Code Separate

Không import notebook trực tiếp vào production core.

Không biến notebook thành dependency của application runtime.

---

# 13. Dependency Rules

## RULE-54 — Dependency Direction

Ưu tiên dependency direction:

```text
UI
 ↓
API
 ↓
Application / Services
 ↓
Domain / Features / Models / Data
```

Core không phụ thuộc ngược vào UI.

### RULE-55 — Framework Isolation

Business/domain logic không nên phụ thuộc không cần thiết vào framework presentation.

Ví dụ domain không cần biết:

```text
Taipy
FastAPI
HTTP
UI State
```

---

# 14. Configuration Rules

## RULE-56 — Configuration Is Not Logic

Configuration có thể chứa:

- Model parameters.
- Thresholds.
- Runtime settings.
- Experiment parameters.

Nhưng không chứa application logic.

---

## RULE-57 — Secrets Outside Repository

Credentials phải được cung cấp qua environment hoặc secret management phù hợp.

Không commit:

```text
API_KEY
TOKEN
PASSWORD
PRIVATE_KEY
```

---

# 15. Documentation Rules

## RULE-58 — Documentation Is Part of the System

Documentation phải được version-control cùng project.

Các docs chính:

```text
PRD.md
DESIGN.md
ARCHITECTURE.md
SCHEMA.md
RULES.md
TECH_STACK.md
TEAM.md
ROLES.md
WORKFLOW.md
```

---

## RULE-59 — One Source of Truth

Mỗi loại thông tin nên có một authoritative document.

Ví dụ:

```text
Product Requirements → PRD.md
UX → DESIGN.md
Architecture → ARCHITECTURE.md
Schema → SCHEMA.md
Rules → RULES.md
Technology → TECH_STACK.md
```

Không copy cùng một architectural fact vào nhiều file rồi để chúng drift.

---

## RULE-60 — Documentation Must Match Implementation

Nếu implementation thay đổi architectural/data behavior quan trọng, documentation liên quan phải được cập nhật.

Không để:

```text
Docs ≠ System
```

---

# 16. Git và Change Rules

## RULE-61 — Small, Understandable Changes

Ưu tiên thay đổi có scope rõ ràng.

Một change nên có thể trả lời:

> “Thay đổi này giải quyết vấn đề gì?”

---

## RULE-62 — No Unrelated Changes

Không trộn:

```text
Feature
+
Massive Refactor
+
Formatting Everything
+
Unrelated Dependency Changes
```

trong một change nếu không cần thiết.

---

## RULE-63 — Review Before Merge

Các thay đổi quan trọng về:

- Architecture.
- Public API.
- Schema.
- Quantum methodology.
- Decision policy.

nên được review trước khi merge.

---

# 17. Dependency và Environment Rules

## RULE-64 — Reproducible Environment

Python version và dependency versions quan trọng phải được quản lý rõ ràng.

Environment V1 phải có thể tái tạo từ project configuration.

---

## RULE-65 — Minimal Dependencies

Chỉ thêm dependency khi có use case thực tế.

Không thêm library chỉ vì:

> “Có thể sẽ dùng sau này.”

---

## RULE-66 — Dependency Changes Need Justification

Một dependency mới cần có:

- Purpose.
- Consumer.
- Compatibility check.
- Impact assessment khi phù hợp.

---

# 18. Security và Data Handling Rules

## RULE-67 — Least Data

Chỉ thu thập/lưu trữ dữ liệu cần thiết cho use case.

---

## RULE-68 — No Credential Leakage

Không để credentials xuất hiện trong:

- Git history.
- Logs.
- Notebook outputs.
- Screenshots.
- Documentation.
- API responses.

---

## RULE-69 — Demo Data Must Be Safe

Competition/demo data phải được kiểm tra để tránh expose sensitive information.

---

# 19. Architecture Change Rules

Một architectural change đáng kể phải trả lời:

```text
Problem
→ Proposed Change
→ Why Existing Architecture Is Insufficient
→ Trade-offs
→ Impact
→ Migration
```

Ví dụ cần architectural review:

- Modular monolith → microservice.
- Local Quantum simulation → remote hardware workflow.
- In-process execution → job queue.
- New persistent database.
- Major API contract change.
- Major domain/schema change.

Không cần ADR cho mọi refactor nhỏ.

---

# 20. Rule Priority

Khi có conflict, ưu tiên theo thứ tự:

```text
1. Product correctness
2. Scientific integrity
3. Security / data integrity
4. Architectural integrity
5. Reproducibility
6. Maintainability
7. Performance
8. Convenience
```

Performance optimization không được phá scientific correctness.

Convenience không được phá architecture hoặc data integrity.

---

# 21. Rule Exceptions

Không phải rule nào cũng tuyệt đối trong mọi context.

Nếu cần exception, phải ghi rõ:

```text
Rule
Reason for exception
Scope
Expected duration
Impact
```

Một exception không được trở thành cách né rule mặc định.

---

# 22. MVP Rule Set

Trong V1, các rule quan trọng nhất cần bảo vệ trước:

```text
Classical First
Quantum Where Justified
Fair Benchmark
Scientific Honesty

UI / API Separation
Classical / Quantum Independence
No Premature Infrastructure

Raw ≠ Features ≠ Model Output ≠ Decision
Explicit Data Contracts
No Fake Confidence
No Sensitive Data

Baseline Before Quantum
Reproducible Evaluation
No Leakage
Negative Results Are Valid

Research ≠ Production
Documentation ≈ Implementation
Minimal Dependencies
```

Đây là minimum discipline để Sentinel có thể vừa là competition project, vừa giữ nền tảng đủ nghiêm túc cho research và productization.

---

# 23. Ranh giới với các tài liệu khác

| Câu hỏi | Tài liệu |
|---|---|
| Sentinel xây gì và tại sao? | `PRD.md` |
| Người dùng trải nghiệm thế nào? | `DESIGN.md` |
| System được cấu trúc ra sao? | `ARCHITECTURE.md` |
| Data được tổ chức thế nào? | `SCHEMA.md` |
| Phải tuân thủ nguyên tắc nào? | `RULES.md` |
| Công nghệ nào được sử dụng? | `TECH_STACK.md` |
| Team là ai? | `TEAM.md` |
| Ai ownership phần nào? | `ROLES.md` |
| Team làm việc thế nào? | `WORKFLOW.md` |

---

# 24. Rules Summary

Sentinel phải được phát triển theo nguyên tắc:

```text
Scientific Rigor
        +
Clean Architecture
        +
Explicit Data Contracts
        +
Reproducible Engineering
        +
Human-Centered Investigation
        +
Measured Quantum Contribution
```

Và nguyên tắc cao nhất:

> **Không xây Sentinel để chứng minh rằng mọi quyết định của chúng ta đều đúng. Xây Sentinel để có thể kiểm chứng một cách nghiêm túc điều gì thực sự đúng.**

Quantum có thể thắng hoặc thua.

Classical có thể thắng hoặc thua.

Một hypothesis có thể đúng hoặc sai.

Điều không được phép là để architecture, benchmark, data hoặc UI làm sai lệch kết luận.

Đó là tiêu chuẩn engineering và research của Sentinel V1.
