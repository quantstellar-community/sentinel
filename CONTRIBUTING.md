# Contributing to Sentinel

Cảm ơn bạn đã quan tâm và đóng góp cho **Quantstellar Sentinel**.

Sentinel là dự án **Behavioral Fraud Intelligence** kết hợp Classical AI/ML với Quantum Computing/Quantum Machine Learning khi có cơ sở khoa học và giá trị đo lường được.

Contribution nên ưu tiên:

```text
Financial Problem
→ Clear Hypothesis / Requirement
→ Classical Baseline
→ Quantum Where Justified
→ Fair Benchmark
→ Validation
→ Product Integration
```

## 1. Trước khi bắt đầu

Hãy đọc các tài liệu chính trong repository:

- `PRD.md` — Product requirements.
- `DESIGN.md` — UI/UX và investigation experience.
- `ARCHITECTURE.md` — system architecture.
- `SCHEMA.md` — data contracts.
- `RULES.md` — engineering và research rules.
- `TECH_STACK.md` — technology stack.
- `TEAM.md` — team structure.
- `ROLES.md` — responsibility/ownership.
- `WORKFLOW.md` — development và research workflow.

Nếu contribution ảnh hưởng architecture, schema, API hoặc research methodology, hãy đọc tài liệu liên quan trước khi implementation.

## 2. Các loại contribution

Contribution có thể thuộc một trong các nhóm:

- Data Engineering
- Classical Machine Learning
- Quantum Computing / QML
- MLOps / Reproducibility
- API / Backend
- UI / Visualization
- Testing
- Documentation

## 3. Quy trình development

Workflow cơ bản:

```text
Task / Issue
    ↓
Understand Scope
    ↓
Check Existing Architecture
    ↓
Implement
    ↓
Test / Validate
    ↓
Review
    ↓
Document
    ↓
Merge
```

Không thực hiện refactor hoặc thay đổi architecture lớn ngoài scope của task nếu chưa có thống nhất.

## 4. Research contributions

Research contribution nên mô tả rõ:

```text
Problem
Hypothesis
Method
Classical Baseline
Experiment
Evaluation
Conclusion
```

Đối với Quantum research, cần xem xét thêm:

- Encoding / state preparation.
- Qubit count.
- Circuit depth.
- Shots.
- Noise.
- Backend.
- Runtime.
- End-to-end computational cost.

Không tuyên bố **quantum advantage** chỉ dựa trên một model metric tốt hơn Classical.

Negative results và inconclusive results vẫn là kết quả hợp lệ.

## 5. Code guidelines

- Giữ module đúng responsibility.
- Không đưa business/model logic vào API route.
- Không để UI phụ thuộc trực tiếp vào model internals.
- Không tạo abstraction hoặc dependency khi chưa có nhu cầu rõ ràng.
- Ưu tiên code dễ đọc, dễ test và dễ tái sử dụng.
- Không commit credentials, API keys hoặc dữ liệu nhạy cảm.

## 6. Testing

Trước khi mở Pull Request, chạy các test phù hợp với thay đổi.

Tối thiểu cần kiểm tra:

```text
Unit tests
Integration tests khi có liên quan
API tests khi API thay đổi
Model evaluation khi model thay đổi
Data validation khi data pipeline thay đổi
```

Một experiment đạt metric tốt không thay thế cho software testing.

## 7. Data

Không commit dữ liệu tài chính hoặc dữ liệu nhạy cảm vào repository.

Khi thay đổi data/feature pipeline, cần kiểm tra:

- Schema.
- Missing values.
- Data leakage.
- Temporal leakage.
- Feature leakage.
- Reproducibility.

Nếu thay đổi data contract, cập nhật `SCHEMA.md` khi cần.

## 8. API và UI

API boundary:

```text
Taipy
  ↓
FastAPI
  ↓
Application Services
  ↓
Sentinel Core
```

UI không tự tính:

- Anomaly score.
- Risk score.
- Confidence.
- Quantum result.
- Model explanation.

Nếu thay đổi public API contract, phải kiểm tra cả backend consumer và UI consumer.

## 9. Documentation

Nếu contribution làm thay đổi một trong các nội dung sau, hãy cập nhật documentation tương ứng:

| Thay đổi | Tài liệu |
|---|---|
| Product requirement | `PRD.md` |
| UI/UX | `DESIGN.md` |
| Architecture | `ARCHITECTURE.md` |
| Data/API schema | `SCHEMA.md` |
| Engineering/research rule | `RULES.md` |
| Technology/dependency | `TECH_STACK.md` |
| Team responsibility | `TEAM.md` / `ROLES.md` |
| Development workflow | `WORKFLOW.md` |

Mục tiêu:

```text
Implementation ≈ Documentation
```

## 10. Pull Request

Một Pull Request nên có:

### Summary

Thay đổi gì?

### Motivation

Tại sao cần thay đổi?

### Implementation

Đã thay đổi những gì?

### Validation

Đã chạy test/experiment nào?

### Impact

Có ảnh hưởng đến:

- API?
- Schema?
- Architecture?
- Model?
- UI?
- Dependencies?

### Limitations

Có limitation hoặc known issue nào không?

## 11. Review

Reviewer nên tập trung vào:

- Correctness.
- Scope.
- Architecture.
- Data/API contracts.
- Tests.
- Scientific validity khi có liên quan.
- Security.
- Regression risk.

Các thay đổi lớn về Quantum methodology, architecture hoặc public schema nên có review từ role liên quan.

## 12. Commit

Commit nên:

- Có scope rõ.
- Mô tả đúng thay đổi.
- Không trộn nhiều thay đổi không liên quan.
- Không commit generated artifacts hoặc secrets.

Ví dụ:

```text
feat: add behavioral feature pipeline
fix: validate transaction timestamp
research: benchmark quantum kernel
docs: update schema contract
test: add anomaly scoring tests
```

## 13. Không làm

Không nên:

- Thêm dependency chỉ vì “có thể cần sau này”.
- Xây infrastructure lớn trước khi có requirement.
- Bỏ qua Classical baseline để đi thẳng vào Quantum.
- Cherry-pick kết quả tốt và bỏ qua kết quả xấu.
- Gọi simulation là hardware result.
- Đưa prototype notebook trực tiếp vào production.
- Đưa business logic vào UI.
- Commit sensitive data.

## 14. Nguyên tắc cuối cùng

Một contribution tốt cho Sentinel không nhất thiết là contribution lớn nhất.

Contribution tốt là contribution:

```text
Clear
+
Correct
+
Testable
+
Reproducible
+
Documented
+
Aligned with Sentinel Architecture
```

Và quan trọng nhất:

> **Đóng góp cho Sentinel để giải quyết bài toán Behavioral Fraud Intelligence tốt hơn — không phải chỉ để thêm code hoặc thêm Quantum.**
