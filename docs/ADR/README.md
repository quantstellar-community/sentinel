# Architecture Decision Records (ADR)

Thư mục này lưu các **Architecture Decision Records** của Sentinel — tài liệu ngắn ghi lại một quyết định kiến trúc: *bối cảnh*, *quyết định*, và *hệ quả*.

## Format

Dùng **MADR** (Markdown Any Decision Records), cấu trúc:

```markdown
# ADR-XXX — Tiêu đề

## Trạng thái
Accepted | Proposed | Superseded | Deprecated

## Bối cảnh
Vấn đề / tình huống dẫn tới quyết định.

## Quyết định
Ta chọn gì và vì sao.

## Hệ quả
- Tích cực / trung tính / tiêu cực
```

## Danh sách ADR

| ADR | Tiêu đề | Trạng thái |
|---|---|---|
| [ADR-001](ADR-001-modular-monolith.md) | Modular Monolith | Accepted |
| [ADR-002](ADR-002-fastapi-product-api.md) | FastAPI as Product API | Accepted |
| [ADR-003](ADR-003-taipy-reference-client.md) | Taipy as Reference Client | Accepted |
| [ADR-004](ADR-004-research-outside-core.md) | Research Outside Core | Accepted |
| [ADR-005](ADR-005-quantum-inside-core.md) | Quantum Inside Core Boundary | Accepted |
| [ADR-006](ADR-006-classical-independent.md) | Classical Independent from Quantum | Accepted |
| [ADR-007](ADR-007-ui-through-api.md) | UI Through API | Accepted |
| [ADR-008](ADR-008-no-premature-infrastructure.md) | No Premature Infrastructure | Accepted |
| [ADR-009](ADR-009-hatchling-src-layout.md) | Hatchling + src-layout Packaging | Accepted |
| [ADR-010](ADR-010-data-layer-contract.md) | Data Layer Contract (SplitData + config) | Accepted |
| [ADR-011](ADR-011-temporal-split.md) | Temporal Split 70/15/15 | Accepted |
| [ADR-012](ADR-012-kagglehub-data-fetch.md) | Kagglehub Data Fetch | Accepted |

## Nguyên tắc

- Mỗi quyết định kiến trúc đáng kể cần một ADR (xem `docs/ARCHITECTURE.md` §19).
- Thông tin chỉ ghi ở **một nơi** (RULE-59); các file khác chỉ link tới ADR, không copy nội dung.
- ADR cũ không xóa khi bị thay thế — ghi trạng thái `Superseded` và link tới ADR mới.