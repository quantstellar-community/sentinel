# ADR-002 — FastAPI as Product API

## Trạng thái

Accepted

## Bối cảnh

Sentinel cần một integration boundary rõ ràng giữa Core và các clients (Taipy, CLI, notebook, external application, financial system tương lai). UI không được gọi trực tiếp vào Core.

## Quyết định

**FastAPI là integration boundary** của Sentinel. Tất cả clients giao tiếp với Core thông qua FastAPI; Core không phụ thuộc ngược vào UI.

## Hệ quả

- **Tích cực:** UI độc lập với Core; API contract rõ ràng cho nhiều loại client.
- **Trung tính:** API route phải giữ thin — chỉ validate, gọi service, trả response (RULE-12).
- **Tiêu cực:** Cần duy trì schema contract ổn định giữa API và clients.