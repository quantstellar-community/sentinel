# ADR-004 — Research Outside Core

## Trạng thái

Accepted

## Bối cảnh

Sentinel có cả research experiments (notebooks, prototype quantum) lẫn production core. Nếu trộn lẫn, exploratory code sẽ xâm nhập runtime và phá vỡ reproducibility.

## Quyết định

**Research notebooks và experiments nằm ngoài `src/sentinel/`** (tại `research/`). Research code không được import vào production runtime (RULE-35, RULE-53).

## Hệ quả

- **Tích cực:** Bảo vệ production core khỏi exploratory code; duy trì reproducibility và maintainability.
- **Trung tính:** Promotion path rõ ràng: experiment → validation → benchmark → stable implementation → production.
- **Tiêu cực:** Research code cần được viết lại/refactor khi promote lên production.