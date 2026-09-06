# Sentinel — Design Document

> **Phiên bản:** V1.0  
> **Trạng thái:** Draft chính thức cho giai đoạn phát triển V1  
> **Dự án:** Quantstellar Sentinel  
> **Vai trò tài liệu:** Xác định trải nghiệm người dùng, information architecture và nguyên tắc thiết kế của Sentinel.

---

## 1. Tổng quan Design

### 1.1. Mục đích

`DESIGN.md` định nghĩa cách người dùng tương tác với Sentinel và cách hệ thống trình bày Behavioral Intelligence để hỗ trợ phát hiện, điều tra và ra quyết định.

Tài liệu tập trung vào **user experience và product interaction**, không thay thế `PRD.md`, `ARCHITECTURE.md`, `SCHEMA.md` hay tài liệu implementation.

### 1.2. Design Philosophy

Sentinel được thiết kế theo tư duy:

```text
Detection
    ↓
Behavioral Context
    ↓
Deviation
    ↓
Evidence
    ↓
Anomaly / Risk
    ↓
Investigation
    ↓
Decision Support
```

Giao diện không chỉ trả lời:

> “Transaction này có phải fraud không?”

mà phải giúp người dùng trả lời:

> “Điều gì bất thường, tại sao bất thường, mức độ đáng chú ý ra sao và tôi cần làm gì tiếp theo?”

### 1.3. Design Scope

V1 tập trung vào:

- Transaction monitoring.
- Risk/anomaly overview.
- Transaction investigation.
- Behavioral context.
- Model evidence.
- Classical/Quantum result presentation.
- Decision support.
- API-driven UI.

---

## 2. Người dùng và Context

### 2.1. Fraud / Financial Crime Investigator

Mục tiêu:

- Xác định nhanh case đáng chú ý.
- Hiểu transaction context.
- Kiểm tra behavioral deviation.
- Xem evidence hỗ trợ anomaly/risk assessment.
- Đưa ra hoặc hỗ trợ quyết định investigation.

### 2.2. Risk / Compliance Analyst

Mục tiêu:

- Theo dõi risk/anomaly patterns.
- Xác định các trường hợp cần review.
- Phân tích các behavioral signals.
- Hiểu giới hạn và mức độ tin cậy của kết quả.

### 2.3. Data Scientist / ML Engineer / Researcher

Mục tiêu:

- Theo dõi model behavior.
- So sánh Classical và Quantum.
- Xem evaluation results.
- Kiểm tra experiment/resource characteristics.

### 2.4. Context sử dụng

Sentinel V1 ưu tiên hai context:

**Operational Investigation**

```text
Nhiều transactions
    ↓
Prioritization
    ↓
Case Selection
    ↓
Investigation
```

**Model / Research Analysis**

```text
Model
    ↓
Evaluation
    ↓
Classical vs Quantum
    ↓
Performance / Resource Analysis
```

Hai context này được trình bày trong cùng sản phẩm nhưng không trộn lẫn information hierarchy.

---

## 3. UX Principles

### 3.1. Investigation-first

Sentinel là investigation-oriented intelligence system.

Dashboard không phải đích cuối cùng; dashboard phải dẫn người dùng tới những case cần được hiểu và điều tra.

### 3.2. Evidence before conclusion

Kết quả phải được trình bày cùng evidence phù hợp.

Không ưu tiên một nhãn:

```text
FRAUD
```

mà ưu tiên:

```text
Risk / Anomaly
    +
Behavioral Evidence
    +
Model Evidence
    +
Decision Support
```

### 3.3. Behavioral context matters

Một transaction không nên được trình bày tách khỏi context khi behavioral history có sẵn.

UI cần có khả năng liên kết:

```text
Current Transaction
        ↓
Historical Behavior
        ↓
Behavioral Deviation
```

### 3.4. Progressive disclosure

Không hiển thị mọi technical detail cùng lúc.

Information hierarchy:

```text
Decision / Attention
        ↓
Risk / Anomaly
        ↓
Evidence
        ↓
Behavioral Context
        ↓
Model Details
        ↓
Quantum / Technical Details
```

Người dùng có thể đi sâu hơn khi cần.

### 3.5. Human-in-the-loop

Sentinel hỗ trợ quyết định, không mặc định thay thế investigator.

UI phải tạo điều kiện cho:

- Review.
- Investigation.
- Evidence inspection.
- Decision support.

### 3.6. Semantic clarity

Mọi score, metric và status phải có ý nghĩa rõ ràng.

Không tạo thêm metric chỉ vì có thể hiển thị.

Ví dụ:

- `Quantum Anomaly Score` phải được định nghĩa rõ.
- `Risk Score` phải có semantic rõ.
- `Confidence` chỉ được hiển thị khi hệ thống thực sự có phương pháp xác định/calibrate confidence hoặc uncertainty.

### 3.7. Scientific honesty

UI không được tạo impression rằng Quantum mặc định tốt hơn Classical.

Khi hiển thị Quantum, cần bảo toàn context:

```text
Classical Baseline
        +
Quantum Result
        +
Benchmark Context
```

---

## 4. Information Architecture

### 4.1. Cấu trúc tổng thể

V1 có thể tổ chức thành các khu vực chính:

```text
Sentinel
│
├── Overview
│
├── Investigation
│
├── Model Intelligence
│
└── System
```

### 4.2. Overview

Mục đích:

- Cho biết trạng thái tổng quan.
- Ưu tiên cases cần attention.
- Hiển thị risk/anomaly distribution.
- Cung cấp context trước khi đi vào investigation.

Không nên biến Overview thành một màn hình chứa mọi metric.

### 4.3. Investigation

Đây là khu vực trung tâm của Sentinel.

Mục đích:

- Chọn case.
- Xem transaction.
- Xem behavioral context.
- Xem anomaly/risk.
- Xem evidence.
- Xem model assessment.
- Hỗ trợ decision.

### 4.4. Model Intelligence

Mục đích:

- So sánh Classical và Quantum.
- Xem detection metrics.
- Xem threshold analysis.
- Xem resource characteristics.
- Kiểm tra experimental results.

Đây là khu vực dành nhiều hơn cho analyst/researcher thay vì investigator thông thường.

### 4.5. System

Mục đích:

- Theo dõi application/model status.
- Model version.
- Quantum backend/simulator information khi cần.
- Runtime/latency information.
- Routing statistics.

Technical information phải được giữ ở mức cần thiết cho operational/research context.

---

## 5. Core User Journey

Flow chính:

```text
Transaction / Case
        ↓
Prioritization
        ↓
Transaction Analysis
        ↓
Behavioral Context
        ↓
Anomaly Signals
        ↓
Model Evidence
        ↓
Risk Assessment
        ↓
Decision Support
```

### 5.1. Bước 1 — Case Selection

Người dùng nhìn thấy danh sách hoặc tổng quan cases và chọn transaction cần phân tích.

### 5.2. Bước 2 — Transaction Analysis

UI hiển thị các thông tin cốt lõi:

- Transaction identifier.
- Amount.
- Time.
- Merchant/category.
- Location.
- Device/context nếu có.
- Risk/anomaly state.

### 5.3. Bước 3 — Behavioral Context

Người dùng có thể xem:

- Historical transaction context.
- Behavioral baseline.
- Deviations.
- Temporal pattern khi dữ liệu hỗ trợ.

### 5.4. Bước 4 — Evidence

UI giải thích những tín hiệu chính dẫn tới anomaly/risk assessment.

Ví dụ:

```text
WHY FLAGGED?

• Amount deviation from baseline
• Unusual transaction time
• Increased transaction velocity
• Geographic deviation
• Behavioral representation differs from normal region
```

Danh sách evidence phải phản ánh output thực tế của system; UI không được tự tạo explanation không có nguồn từ model/data.

### 5.5. Bước 5 — Decision Support

UI cung cấp:

- Risk/anomaly state.
- Supporting evidence.
- Model result.
- Relevant uncertainty khi có.
- Recommended attention level nếu system có decision policy.

Quyết định cuối cùng vẫn thuộc investigator hoặc quy trình bên ngoài Sentinel.

---

## 6. Investigation Workflow

### 6.1. Investigation flow

```text
Case Queue
    ↓
Select Transaction
    ↓
Transaction Summary
    ↓
Behavioral Timeline / Context
    ↓
Anomaly & Risk
    ↓
Model Evidence
    ↓
Quantum Evidence (nếu được sử dụng)
    ↓
Decision Support
```

### 6.2. Transaction Summary

Phần đầu trang phải trả lời nhanh:

> “Tôi đang xem transaction nào và tại sao nó đáng chú ý?”

Có thể gồm:

```text
Transaction ID
Risk Level
Decision / Attention State
Amount
Timestamp
Merchant
Location
```

### 6.3. Behavioral View

Khi dữ liệu hỗ trợ, hiển thị:

- Transaction history.
- Normal range/baseline.
- Temporal pattern.
- Amount deviation.
- Velocity.
- Merchant pattern.
- Geographic behavior.

Visualization phải phục vụ câu hỏi investigation, không chỉ trang trí.

### 6.4. Anomaly View

Hiển thị anomaly assessment và các signals liên quan.

Không nên chỉ có:

```text
Anomaly Score: 0.89
```

mà cần context:

```text
Anomaly Score
    ↓
What contributed?
    ↓
How unusual?
    ↓
Compared with what baseline?
```

### 6.5. Model Evidence

Model evidence có thể bao gồm:

- Classical model assessment.
- Quantum anomaly assessment.
- Relevant feature/evidence signals.
- Model version.
- Evaluation context khi phù hợp.

---

## 7. UI Structure

### 7.1. Application Shell

V1 có thể sử dụng:

```text
┌─────────────────────────────────────────────┐
│ Sentinel                                     │
├──────────────┬──────────────────────────────┤
│ Navigation   │ Main Content                 │
│              │                              │
│ Overview     │                              │
│ Investigation│                              │
│ Models       │                              │
│ System       │                              │
└──────────────┴──────────────────────────────┘
```

Taipy là presentation layer của V1.

### 7.2. Pages

```text
ui/
├── app.py
├── pages/
│   ├── overview
│   ├── investigation
│   ├── model_intelligence
│   └── system
├── components/
├── api_client.py
├── state/
└── assets/
```

Tên implementation cụ thể có thể thay đổi; design requirement là các responsibilities phải được giữ rõ ràng.

### 7.3. Components

Các component nên được xây theo responsibility:

- Transaction table.
- Risk indicator.
- Anomaly indicator.
- Behavioral timeline.
- Evidence panel.
- Score card.
- Model comparison.
- Metric visualization.
- System status.

Không tạo abstraction/component chỉ vì có thể tạo.

---

## 8. Dashboard Design

### 8.1. Mục tiêu

Dashboard phải giúp người dùng nhanh chóng trả lời:

1. Có bao nhiêu cases đáng chú ý?
2. Case nào cần attention?
3. Risk/anomaly distribution đang như thế nào?
4. Tôi nên đi đâu tiếp theo?

### 8.2. Nội dung

Có thể bao gồm:

```text
Cases Requiring Attention
Risk Distribution
Anomaly Distribution
Recent Alerts
Key Behavioral Signals
```

### 8.3. Nguyên tắc

Dashboard không nên biến thành:

```text
20 cards
15 charts
10 scores
```

Mọi visual phải có decision value.

---

## 9. Transaction Investigation Design

### 9.1. Layout định hướng

```text
┌──────────────────────────────────────────────┐
│ Transaction Summary                          │
├───────────────────┬──────────────────────────┤
│ Transaction        │ Risk / Anomaly          │
│ Context            │ Assessment              │
├───────────────────┴──────────────────────────┤
│ Behavioral Timeline / Context                │
├──────────────────────────────────────────────┤
│ Evidence                                     │
├──────────────────────────────────────────────┤
│ Model Analysis                               │
├──────────────────────────────────────────────┤
│ Decision Support                             │
└──────────────────────────────────────────────┘
```

### 9.2. Risk presentation

Risk level cần dễ nhận biết nhưng không được thay thế evidence.

Ví dụ:

```text
HIGH
Manual Review
```

sau đó mới đến score và evidence.

### 9.3. Behavioral timeline

Khi dữ liệu temporal có sẵn, timeline là một visualization quan trọng.

Ví dụ:

```text
08:12  Coffee        $8
08:43  Grocery      $42
09:10  Electronics  $1,250   ← deviation
09:12  ATM            $500   ← deviation
```

Timeline phải phản ánh dữ liệu thật.

---

## 10. Score và Result Presentation

### 10.1. Score hierarchy

V1 ưu tiên một hierarchy đơn giản:

```text
Risk / Attention State
        ↓
Classical Assessment
        ↓
Quantum Anomaly Assessment
        ↓
Evidence
```

### 10.2. Classical score

Nếu classical model cung cấp fraud probability hoặc anomaly score, UI phải dùng đúng tên và semantic của model.

Không gọi một probability là “confidence” nếu nó chưa được calibration/định nghĩa như confidence.

### 10.3. Quantum anomaly score

Nếu Quantum Kernel + OCSVM được sử dụng, UI có thể hiển thị:

```text
Quantum Anomaly Score
```

kèm context về method khi cần.

Không gọi chung chung là:

```text
Quantum Score
```

vì tên này không cho biết score đang đo điều gì.

### 10.4. Confidence / Uncertainty

`Confidence` hoặc `Uncertainty` chỉ xuất hiện khi Sentinel có phương pháp xác định tương ứng.

Nếu chưa có:

```text
Không hiển thị.
```

Không suy diễn confidence từ raw model score.

### 10.5. Classical vs Quantum

Khi cần so sánh:

```text
Classical Baseline
        vs
Quantum Enhancement
```

phải hiển thị cùng evaluation context.

Không nên chỉ đưa hai số:

```text
Classical: 0.71
Quantum:   0.86
```

rồi để người dùng tự hiểu Quantum “tốt hơn”.

---

## 11. Explainability và Evidence

### 11.1. Evidence-first presentation

Sentinel nên ưu tiên:

```text
Result
  ↓
Why?
  ↓
Evidence
  ↓
Context
```

### 11.2. Evidence categories

Có thể phân loại:

**Transaction evidence**

- Amount.
- Time.
- Merchant.
- Location.

**Behavioral evidence**

- Amount deviation.
- Velocity.
- Merchant frequency.
- Geographic deviation.
- Temporal deviation.

**Model evidence**

- Classical assessment.
- Quantum anomaly assessment.
- Relevant model information.

### 11.3. Không tạo explanation giả

UI chỉ hiển thị explanation/evidence được hỗ trợ bởi:

- Input data.
- Feature pipeline.
- Model output.
- Explicit decision rules.

Không được tạo narrative explanation chỉ để làm kết quả có vẻ dễ hiểu hơn.

### 11.4. Model limitations

Khi cần, UI phải cho phép người dùng biết:

- Model version.
- Analysis context.
- Whether Quantum was actually invoked.
- Backend/simulator context nếu liên quan.
- Relevant limitations.

---

## 12. Quantum UX

### 12.1. Quantum không phải primary visual identity

Sentinel không được thiết kế theo tư duy:

```text
QUANTUM
QUANTUM
QUANTUM
```

Quantum là một capability bên trong Behavioral Intelligence.

### 12.2. Khi nào hiển thị Quantum?

Quantum information được hiển thị khi:

- Transaction thực sự được route qua Quantum pipeline.
- Người dùng đang xem model analysis.
- Người dùng cần hiểu contribution của Quantum.

Nếu Quantum không được sử dụng:

```text
Quantum Analysis: Not invoked
```

thay vì tạo một giá trị giả.

### 12.3. Progressive disclosure

Investigator thông thường có thể chỉ cần:

```text
Quantum Enhancement: Used
Quantum Anomaly: High
```

Researcher có thể mở rộng:

```text
Method
Quantum Kernel
OCSVM
Feature Map
Backend
Qubits
Circuit Depth
Shots
Runtime
```

Technical details không nên chiếm vị trí chính của investigation workflow.

### 12.4. Quantum result phải có baseline

Khi hiển thị Quantum, nếu mục đích là comparison:

```text
Classical Baseline
        +
Quantum Result
        +
Evaluation Context
```

Không được thiết kế visual hierarchy khiến Quantum mặc định trông “cao cấp hơn” chỉ vì nó là Quantum.

---

## 13. Visual và Interaction Principles

### 13.1. Information hierarchy

Ưu tiên:

```text
Attention
    ↓
Risk / Anomaly
    ↓
Evidence
    ↓
Behavior
    ↓
Model
    ↓
Technical Detail
```

### 13.2. Tables

Transaction table phải hỗ trợ:

- Sorting.
- Filtering.
- Prioritization.
- Case selection.

Không đưa quá nhiều columns vào default view.

### 13.3. Charts

Mỗi chart phải trả lời một câu hỏi.

Ví dụ:

```text
Risk distribution
→ Risk đang phân bố thế nào?

Behavior timeline
→ Hành vi thay đổi ở đâu?

Model comparison
→ Classical và Quantum khác nhau thế nào?
```

Không tạo chart chỉ để “có visualization”.

### 13.4. Status và color semantics

Color phải có semantic nhất quán.

Ví dụ:

- Neutral → informational.
- Warning → cần chú ý.
- High-risk → mức độ nghiêm trọng cao.
- Success/normal → trạng thái bình thường.

Không phụ thuộc hoàn toàn vào màu; text/icon/label vẫn phải truyền tải meaning.

### 13.5. Readability

UI phải ưu tiên:

- Clear typography.
- Sufficient contrast.
- Consistent spacing.
- Predictable navigation.
- Readable tables.
- Không quá tải thông tin.

---

## 14. UI ↔ API Boundary

### 14.1. Taipy là Presentation Layer

```text
ui/
    ↓
Taipy
    ↓
HTTP/JSON
    ↓
FastAPI
```

Taipy không trực tiếp gọi:

```text
Qiskit
LightGBM
OCSVM
Feature Engineering
```

### 14.2. FastAPI là Application Interface

API chịu trách nhiệm:

```text
Request
    ↓
Validation
    ↓
Application Service
    ↓
Result
```

### 14.3. Business logic không nằm trong UI

UI không quyết định:

- Fraud logic.
- Anomaly algorithm.
- Quantum routing policy.
- Model scoring.
- Feature computation.

UI chỉ trình bày kết quả và thực hiện user interaction.

### 14.4. UI phải có thể thay thế

Nếu Taipy được thay bằng một frontend khác:

```text
React
Next.js
Mobile
External Client
```

thì Sentinel Core và API contract không cần được thiết kế lại chỉ vì thay presentation layer.

---

## 15. MVP Design Scope

### 15.1. Pages bắt buộc

V1 ưu tiên:

```text
1. Overview
2. Investigation
3. Model Intelligence
4. System
```

### 15.2. Investigation là trọng tâm

Nếu thời gian hạn chế, ưu tiên theo thứ tự:

```text
Investigation
    ↓
Overview
    ↓
Model Intelligence
    ↓
System
```

Một investigation flow hoàn chỉnh có giá trị hơn việc có nhiều page nhưng không có workflow end-to-end.

### 15.3. MVP interactions

Phải hỗ trợ:

- Xem transaction list.
- Filter/sort case.
- Chọn transaction.
- Xem transaction context.
- Xem behavioral evidence.
- Xem anomaly/risk.
- Xem model assessment.
- Xem Quantum result khi được invoke.
- Xem decision-support information.

### 15.4. Không cần trong UI V1

Không ưu tiên:

- Enterprise authentication.
- RBAC.
- Collaboration/newsfeed.
- Complex case management.
- Real-time multi-user editing.
- Advanced administration.
- Excessive customization.

Những capability này chỉ được thêm khi có product requirement rõ ràng.

---

## 16. Future Design Direction

### 16.1. Temporal Behavioral Intelligence

Khi Sentinel có temporal representation:

```text
Transaction History
        ↓
Temporal Representation
        ↓
Behavior Embedding
        ↓
Anomaly Analysis
```

UI có thể mở rộng behavioral timeline và temporal patterns.

### 16.2. Advanced Investigation

Có thể bổ sung:

- Richer investigation timeline.
- Customer behavioral profile.
- Cross-transaction relationships.
- Case aggregation.
- Investigation history.

### 16.3. Graph / Relationship Intelligence

Nếu Sentinel phát triển graph/temporal graph capabilities, UI có thể bổ sung:

```text
Customer
  ↕
Device
  ↕
Merchant
  ↕
Location
  ↕
Transaction
```

Chỉ triển khai khi graph intelligence thực sự trở thành product capability.

### 16.4. Advanced Quantum Analysis

Có thể mở rộng UI cho:

- Quantum Autoencoder.
- Fidelity-based anomaly analysis.
- Quantum representation learning.
- Advanced quantum resource analysis.

Các capability này chỉ xuất hiện khi được hỗ trợ bởi research/implementation thực tế.

---

## 17. Design Quality Criteria

Một thiết kế Sentinel tốt phải đáp ứng:

### Clarity

Người dùng hiểu transaction đang được đánh giá thế nào.

### Context

Kết quả được đặt trong behavioral context phù hợp.

### Evidence

Người dùng có thể hiểu các tín hiệu chính dẫn tới assessment.

### Actionability

Kết quả giúp người dùng biết case có cần attention/investigation hay không.

### Scientific Integrity

UI không làm sai lệch ý nghĩa của model hoặc Quantum result.

### Simplicity

Không có information hoặc interaction không phục vụ use case.

### Extensibility

Design có thể mở rộng khi Sentinel phát triển nhưng không yêu cầu xây enterprise features trước thời điểm cần thiết.

---

## 18. Ranh giới với các tài liệu khác

`DESIGN.md` xác định **experience và interaction**.

| Câu hỏi | Tài liệu |
|---|---|
| Sentinel xây gì và tại sao? | `PRD.md` |
| Người dùng trải nghiệm thế nào? | `DESIGN.md` |
| System được cấu trúc ra sao? | `ARCHITECTURE.md` |
| Data được tổ chức thế nào? | `SCHEMA.md` |
| Các constraint/rules là gì? | `RULES.md` |
| Công nghệ nào được sử dụng? | `TECH_STACK.md` |
| Team là ai? | `TEAM.md` |
| Ownership thuộc về ai? | `ROLES.md` |
| Team làm việc thế nào? | `WORKFLOW.md` |

Implementation details của Taipy, FastAPI hoặc component code không thuộc phạm vi của document này.

---

## 19. Design Summary

Sentinel được thiết kế như một **investigation-oriented Behavioral Intelligence system**.

Trải nghiệm cốt lõi:

```text
Case
 ↓
Transaction
 ↓
Behavioral Context
 ↓
Anomaly
 ↓
Evidence
 ↓
Risk
 ↓
Decision Support
```

UI không phải nơi thực hiện intelligence computation.

```text
Taipy
  ↓
Presentation
  ↓
FastAPI
  ↓
Sentinel Core
```

Quantum không phải trung tâm của visual identity. Quantum xuất hiện như một **computational enhancement capability** khi thực sự được sử dụng và phải được trình bày cùng baseline/context phù hợp.

Design principle cuối cùng của Sentinel là:

> **Giúp con người hiểu điều gì bất thường, tại sao nó bất thường và cần làm gì tiếp theo — thay vì chỉ đưa ra một nhãn fraud.**
