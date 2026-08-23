# Sentinel — Technology Stack

> **Phiên bản:** V1.0  
> **Trạng thái:** Draft chính thức cho giai đoạn phát triển V1  
> **Dự án:** Quantstellar Sentinel  
> **Nguyên tắc:** Chọn công nghệ theo product requirement, research requirement và engineering value — không chọn công nghệ chỉ để làm stack “enterprise” hơn.

---

## 1. Mục đích

`TECH_STACK.md` ghi nhận các công nghệ, framework, library và tooling được lựa chọn hoặc dự kiến sử dụng cho Sentinel V1.

Tài liệu trả lời:

> **Sentinel sử dụng công nghệ gì, công nghệ đó phục vụ responsibility nào và tại sao nó phù hợp với kiến trúc hiện tại?**

Tài liệu này không thay thế:

- `PRD.md` — Product requirements.
- `DESIGN.md` — UX/UI design.
- `ARCHITECTURE.md` — System architecture.
- `SCHEMA.md` — Data contracts.
- `RULES.md` — Engineering/research rules.

---

# 2. Technology Philosophy

Sentinel sử dụng Python-centric stack cho V1 vì product core, ML, Quantum ML, API và research đều có thể nằm trong cùng ecosystem.

Nguyên tắc lựa chọn:

```text
Product Requirement
        ↓
Architecture Requirement
        ↓
Research Requirement
        ↓
Technology Selection
        ↓
Measure
        ↓
Keep / Replace
```

Không có công nghệ nào được xem là “bắt buộc mãi mãi”.

Nếu một technology không còn phù hợp với workload hoặc product direction, nó có thể được thay thế mà không phá vỡ core architectural contracts.

---

# 3. Technology Stack Overview

Stack V1 được tổ chức theo các lớp:

```text
┌──────────────────────────────────────────────┐
│ Presentation                                  │
│ Taipy + Plotly                                │
├──────────────────────────────────────────────┤
│ API / Integration                             │
│ FastAPI + Pydantic                            │
├──────────────────────────────────────────────┤
│ Application / Core                            │
│ Python                                        │
├──────────────────────────────────────────────┤
│ Classical ML                                  │
│ scikit-learn + selected ML libraries          │
├──────────────────────────────────────────────┤
│ Quantum Computing                             │
│ Qiskit + selected quantum libraries           │
├──────────────────────────────────────────────┤
│ Data / Scientific Computing                   │
│ NumPy + pandas + SciPy                        │
├──────────────────────────────────────────────┤
│ Development / Environment                     │
│ uv + Python 3.12.x                            │
├──────────────────────────────────────────────┤
│ Testing / Quality                             │
│ pytest + project quality tooling              │
└──────────────────────────────────────────────┘
```

Các library cụ thể ngoài core stack chỉ được thêm khi có use case thực tế.

---

# 4. Runtime Language

## 4.1. Python

**Vai trò:** Ngôn ngữ chính của Sentinel V1.

Python được sử dụng cho:

- Application core.
- Data processing.
- Feature engineering.
- Classical ML.
- Quantum ML.
- FastAPI backend.
- Taipy UI.
- Research experiments.
- Evaluation.

Lý do:

- Một ecosystem thống nhất cho ML, data science, Quantum và backend.
- Giảm friction giữa research và product implementation.
- Phù hợp với architecture Python-centric của Sentinel.

---

# 5. Python Version

## 5.1. Python 3.12.x

V1 sử dụng Python 3.12.x làm baseline runtime.

Project phải pin một patch version cụ thể trong development environment khi dependency compatibility yêu cầu.

Ví dụ:

```text
.python-version
```

có thể xác định Python version mà `uv` sử dụng.

Python version phải được thống nhất giữa:

```text
Development
CI
Testing
Deployment
```

khi các môi trường đó tồn tại.

---

# 6. Environment & Dependency Management

## 6.1. uv

**Vai trò:** Python package manager và environment tooling.

`uv` được sử dụng để:

- Quản lý Python environment.
- Tạo virtual environment.
- Quản lý dependencies.
- Lock dependency versions.
- Chạy project commands trong environment.

Project configuration nằm tại:

```text
pyproject.toml
```

Dependency lock được quản lý bằng lockfile tương ứng của `uv`.

### Nguyên tắc

Không cài dependency production một cách tùy tiện bằng global Python environment.

Ưu tiên:

```text
uv
 ↓
Project Environment
 ↓
Locked Dependencies
```

---

# 7. API / Backend Stack

## 7.1. FastAPI

**Vai trò:** API và integration boundary.

Architecture:

```text
Taipy
   ↓ HTTP
FastAPI
   ↓
Application Services
   ↓
Sentinel Core
```

FastAPI chịu trách nhiệm:

- HTTP endpoints.
- Request validation.
- Response serialization.
- API documentation.
- Dependency injection ở mức cần thiết.

FastAPI không chứa:

- Model logic.
- Feature engineering.
- Quantum circuit logic.
- Business decision logic.

---

## 7.2. Pydantic

**Vai trò:** Data validation và API/data contracts.

Pydantic được sử dụng để:

- Validate request data.
- Validate/serialize response data.
- Define structured contracts.
- Giữ API boundary rõ ràng.

Pydantic schema không được biến thành nơi chứa toàn bộ application logic.

---

# 8. Presentation Stack

## 8.1. Taipy

**Vai trò:** Reference presentation/investigation UI V1.

Taipy được sử dụng để xây:

- Overview.
- Investigation interface.
- Transaction analysis.
- Behavioral visualization.
- Model analysis.
- Decision-support presentation.

Taipy không phải Sentinel Core.

Boundary:

```text
Taipy
 ↓
API Client
 ↓
FastAPI
 ↓
Sentinel Core
```

Nếu tương lai cần thay Taipy bằng frontend technology khác, API/core contract phải được giữ độc lập.

---

## 8.2. Plotly

**Vai trò:** Interactive data visualization.

Plotly phù hợp với Sentinel vì UI cần biểu diễn:

- Transaction patterns.
- Behavioral timeline.
- Risk/anomaly distributions.
- Model comparison.
- Evaluation results.

Visualization phải phục vụ investigation question, không được tạo chart chỉ để làm UI phong phú hơn.

---

# 9. Scientific Computing Stack

## 9.1. NumPy

**Vai trò:**

- Numerical arrays.
- Vectorized computation.
- Model input/output representation.
- Scientific computing foundation.

NumPy là nền tảng numerical computing cho các module cần array-based computation.

---

## 9.2. pandas

**Vai trò:**

- Tabular data processing.
- Dataset manipulation.
- Transaction history processing.
- Feature preparation.
- Evaluation result analysis.

pandas chủ yếu nằm trong data/research pipeline và không nên bị kéo trực tiếp vào mọi layer của application nếu không cần thiết.

---

## 9.3. SciPy

**Vai trò:**

- Scientific/statistical utilities.
- Mathematical operations.
- Statistical processing khi research/model yêu cầu.

SciPy chỉ được sử dụng ở nơi có computational/statistical justification.

---

# 10. Classical Machine Learning Stack

## 10.1. scikit-learn

**Vai trò:** Classical ML baseline và anomaly detection.

Có thể sử dụng cho:

- Isolation Forest.
- One-Class SVM.
- Classical preprocessing.
- Evaluation metrics.
- Classical model baselines.

Sentinel không coi một algorithm là mặc định tốt nhất.

Model selection phải dựa trên:

```text
Problem
→ Dataset
→ Baseline
→ Evaluation
→ Practical Utility
```

---

## 10.2. Supervised ML Libraries

Các library supervised ML bổ sung chỉ được thêm khi formulation của bài toán thực sự yêu cầu.

Ví dụ một model như XGBoost chỉ nên được đưa vào khi:

- Labelled formulation phù hợp.
- Có research/product reason.
- Có baseline/evaluation rõ ràng.

Không thêm supervised framework chỉ vì nó phổ biến.

---

# 11. Quantum Computing Stack

## 11.1. Qiskit

**Vai trò:** Quantum computing framework cho Quantum pipeline V1.

Qiskit có thể được sử dụng cho:

- Quantum circuits.
- Quantum feature maps.
- Quantum kernels.
- Quantum execution.
- Simulator/hardware integration khi phù hợp.

Quantum layer:

```text
Behavioral Representation
        ↓
Quantum Feature Map
        ↓
Quantum Kernel
        ↓
Classical OCSVM / downstream method
```

---

## 11.2. Quantum Kernel

Quantum Kernel là một **method**, không phải một framework.

V1 ưu tiên hướng:

```text
Behavioral Representation
        ↓
Quantum Kernel
        ↓
OCSVM
        ↓
Anomaly Assessment
```

Quantum Kernel phải được benchmark với classical kernel/baseline phù hợp.

---

## 11.3. Quantum Hardware / Simulator

Sentinel phải phân biệt:

```text
Ideal Simulation
≠
Noisy Simulation
≠
Real Quantum Hardware
```

Mọi experimental result phải ghi rõ execution context khi có liên quan.

Khi sử dụng hardware, cần theo dõi phù hợp:

- Backend.
- Qubit count.
- Circuit depth.
- Shots.
- Noise.
- Runtime.

---

# 12. Quantum Research Libraries

Quantum libraries ngoài Qiskit chỉ được thêm khi một research method thực sự cần.

Ví dụ potential future areas:

- Quantum Autoencoder.
- Advanced Quantum Kernel methods.
- Quantum generative models.
- Quantum uncertainty methods.

Không đưa toàn bộ quantum ecosystem vào dependency graph V1 chỉ để “chuẩn bị trước”.

---

# 13. Machine Learning Pipeline

Technology stack phải hỗ trợ pipeline:

```text
Transaction Data
      ↓
pandas / NumPy
      ↓
Feature Engineering
      ↓
scikit-learn / custom feature logic
      ↓
Classical Baseline
      ↓
Quantum Enhancement
      ↓
Assessment
      ↓
FastAPI
      ↓
Taipy + Plotly
```

Pipeline này phải giữ được:

- Reproducibility.
- Testability.
- Classical/Quantum comparability.

---

# 14. API ↔ UI Technology Boundary

Technology responsibilities:

```text
┌─────────────────────────────┐
│ Taipy                       │
│ Plotly                      │
│ Presentation                │
└──────────────┬──────────────┘
               │
             HTTP
               │
┌──────────────▼──────────────┐
│ FastAPI                     │
│ Pydantic                    │
│ API Contract                │
└──────────────┬──────────────┘
               │
┌──────────────▼──────────────┐
│ Sentinel Core               │
│ Domain / Services / Models  │
└─────────────────────────────┘
```

UI technology không được trở thành dependency của domain/model layer.

---

# 15. Testing Stack

## 15.1. pytest

**Vai trò:** Testing framework chính.

Dùng cho:

- Unit tests.
- Integration tests.
- API tests.
- Core logic tests.
- Data contract tests.

Cấu trúc:

```text
tests/
├── unit/
├── integration/
└── evaluation/
```

---

# 16. Code Quality & Developer Tooling

Các tooling bổ sung chỉ được lựa chọn khi phù hợp với project workflow.

Có thể bao gồm:

- Formatter.
- Linter.
- Static type checker.
- Pre-commit hooks.

Nguyên tắc:

```text
Tool
 ↓
Concrete Problem
 ↓
Adoption
```

Không thêm tooling chỉ để tăng số lượng developer tools.

---

# 17. Research Tooling

Research có thể sử dụng:

- Jupyter Notebook.
- Python scientific stack.
- Visualization libraries.
- Quantum simulators.
- Benchmark scripts.

Research dependencies nên được quản lý rõ ràng để tránh kéo experimental dependencies vào production runtime nếu không cần.

---

# 18. Data Storage

V1 không mặc định yêu cầu một database enterprise.

Data artifacts có thể được tổ chức:

```text
data/
├── raw/
├── processed/
├── features/
└── predictions/
```

Nếu Sentinel sau này cần persistence cho:

- Investigation cases.
- User state.
- Model metadata.
- Audit trail.

thì database technology sẽ được lựa chọn dựa trên requirement thực tế.

Không thêm database chỉ vì project “nên có database”.

---

# 19. Deployment Stack

V1 ưu tiên deployment đơn giản.

Conceptual:

```text
User
 ↓
Taipy
 ↓
FastAPI
 ↓
Sentinel Core
 ↓
Data / Quantum Backend
```

Không mặc định yêu cầu:

- Kubernetes.
- Docker orchestration.
- Service mesh.
- Kafka.
- Distributed compute.

Deployment technology có thể mở rộng khi workload chứng minh nhu cầu.

---

# 20. Technology Selection Matrix

| Layer | Technology | Vai trò | Trạng thái V1 |
|---|---|---|---|
| Language | Python 3.12.x | Runtime chính | Core |
| Environment | uv | Environment/dependency management | Core |
| API | FastAPI | API boundary | Core |
| Validation | Pydantic | Data contracts | Core |
| UI | Taipy | Presentation layer | Core |
| Visualization | Plotly | Interactive charts | Core |
| Numerical | NumPy | Numerical computing | Core |
| Data | pandas | Tabular processing | Core |
| Scientific | SciPy | Scientific utilities | Khi cần |
| Classical ML | scikit-learn | Baselines/anomaly detection | Core |
| Quantum | Qiskit | Quantum computing | Core research |
| Testing | pytest | Testing | Core |
| Notebook | Jupyter | Research | Research |
| Frontend | React / Next.js | Alternative future client | Không phải V1 |
| Database | TBD | Persistence | Chưa cần mặc định |
| Orchestration | TBD | Workflow | Chưa cần V1 |

---

# 21. Frontend Strategy

Sentinel V1 không cần đồng thời xây:

```text
React
Next.js
Node.js
Taipy
```

Taipy + Plotly là presentation stack được ưu tiên cho V1.

### Lý do

- Python-centric ecosystem.
- Phù hợp với ML/Quantum research stack.
- Giảm frontend/backend duplication.
- Tốc độ phát triển phù hợp với V1.
- Vẫn giữ FastAPI làm API boundary.

### Future

Nếu product cần frontend production chuyên biệt, có thể đánh giá:

```text
React
Next.js
TypeScript
```

nhưng đây là future option, không phải dependency V1.

---

# 22. Backend Strategy

Sentinel không cần Node.js backend trong V1.

Backend stack:

```text
Python
+
FastAPI
+
Pydantic
+
Sentinel Core
```

Node.js chỉ có ý nghĩa nếu một future frontend/build/deployment architecture thực sự cần nó.

Không thêm Node.js chỉ vì frontend technology có thể dùng Node ecosystem.

---

# 23. Dependency Principles

Mọi dependency mới phải trả lời:

1. Nó giải quyết vấn đề gì?
2. Module nào sử dụng?
3. Có dependency tương đương đang tồn tại không?
4. Nó ảnh hưởng Python/version compatibility thế nào?
5. Nó có cần thiết cho V1 không?
6. Nó có kéo theo infrastructure complexity không?

Nếu câu trả lời không rõ:

> Không thêm dependency.

---

# 24. Versioning Principles

Các dependency quan trọng phải được lock/reproduce trong project environment.

Đặc biệt chú ý compatibility giữa:

```text
Python
+
Taipy
+
FastAPI
+
Pydantic
+
NumPy
+
pandas
+
scikit-learn
+
Qiskit
```

Khi một dependency thay đổi major/minor version có breaking behavior, cần kiểm tra:

- API compatibility.
- Runtime compatibility.
- Model behavior.
- Test results.
- Quantum execution behavior.

---

# 25. Research vs Production Dependencies

Không phải dependency của research đều phải nằm trong production runtime.

Conceptual:

```text
Production
├── FastAPI
├── Pydantic
├── NumPy
├── pandas
├── scikit-learn
└── Qiskit (nếu Quantum runtime là V1 capability)

Research
├── Jupyter
├── Experiment tooling
└── Additional research libraries
```

Dependency graph thực tế phải được giữ đơn giản nhất có thể.

---

# 26. Technology Evaluation Rules

Một technology có thể được thay thế khi:

- Không còn maintained phù hợp với project.
- Không tương thích với architecture.
- Dependency conflict nghiêm trọng.
- Performance không đáp ứng requirement.
- Complexity vượt quá value.
- Có alternative tốt hơn đã được benchmark.

Không thay technology chỉ vì:

> “Công nghệ khác đang hot hơn.”

---

# 27. V1 Recommended Stack

Stack được khuyến nghị cho Sentinel V1:

```text
Python 3.12.x
│
├── uv
│
├── FastAPI
├── Pydantic
│
├── Taipy
├── Plotly
│
├── NumPy
├── pandas
├── SciPy
│
├── scikit-learn
│
├── Qiskit
│
├── pytest
└── Jupyter
```

Đây là stack đủ để xây:

```text
Research
+
ML
+
Quantum ML
+
API
+
Investigation UI
+
Evaluation
```

mà không tạo unnecessary infrastructure.

---

# 28. Technology Non-goals

V1 không có mục tiêu:

- Xây full React/Next.js frontend song song với Taipy.
- Xây Node.js backend.
- Xây microservice platform.
- Xây Kubernetes platform.
- Xây enterprise database platform.
- Thêm hàng chục ML frameworks.
- Thêm toàn bộ Quantum SDK ecosystem.
- Xây infrastructure trước product requirement.

---

# 29. Technology-to-Architecture Mapping

```text
                   Sentinel

       ┌─────────────────────────┐
       │ Taipy + Plotly          │
       │ Presentation            │
       └────────────┬────────────┘
                    │
              FastAPI / Pydantic
                    │
       ┌────────────▼────────────┐
       │ Application / Services  │
       └────────────┬────────────┘
                    │
          ┌─────────┴─────────┐
          │                   │
     Classical             Quantum
   scikit-learn             Qiskit
          │                   │
          └─────────┬─────────┘
                    │
             Assessment
                    │
                 Decision
```

Technology chỉ là implementation layer của architecture; technology không được quyết định product semantics.

---

# 30. Technology Governance

Mỗi technology quan trọng phải có:

```text
Purpose
Consumer
Reason
Compatibility
Cost / Complexity
Exit Option
```

Khi technology trở thành architectural dependency quan trọng, lý do lựa chọn phải được document.

Các thay đổi lớn có thể được ghi nhận bằng ADR hoặc architectural decision trong `ARCHITECTURE.md`.

---

# 31. Ranh giới với các tài liệu khác

| Câu hỏi | Tài liệu |
|---|---|
| Sentinel xây gì và tại sao? | `PRD.md` |
| Người dùng trải nghiệm thế nào? | `DESIGN.md` |
| System được cấu trúc ra sao? | `ARCHITECTURE.md` |
| Data được tổ chức thế nào? | `SCHEMA.md` |
| Các rules/constraints là gì? | `RULES.md` |
| Công nghệ nào được sử dụng? | `TECH_STACK.md` |
| Team là ai? | `TEAM.md` |
| Ai ownership phần nào? | `ROLES.md` |
| Team làm việc thế nào? | `WORKFLOW.md` |

---

# 32. Technology Stack Summary

Sentinel V1 sử dụng một stack Python-centric, modular và research-friendly:

```text
Python
   +
uv
   +
FastAPI / Pydantic
   +
Taipy / Plotly
   +
NumPy / pandas / SciPy
   +
scikit-learn
   +
Qiskit
   +
pytest / Jupyter
```

Mục tiêu của stack không phải tối đa hóa số lượng technology.

Mục tiêu là tạo một environment đủ mạnh để:

```text
Research
    ↓
Classical Baseline
    ↓
Quantum Experiment
    ↓
Fair Benchmark
    ↓
Validated Intelligence
    ↓
FastAPI
    ↓
Investigation UI
    ↓
Product
```

Nguyên tắc cuối cùng:

> **Technology phải phục vụ Sentinel. Sentinel không được trở thành một project chỉ để phục vụ technology stack.**
