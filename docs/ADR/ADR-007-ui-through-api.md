# ADR-007 — UI Through API

## Trạng thái

Accepted

## Bối cảnh

UI (Taipy) không được gọi trực tiếp Core, models hay Quantum. Cần một boundary rõ ràng để bảo vệ separation of concerns và cho phép thay thế client.

## Quyết định

**Taipy chỉ giao tiếp với Sentinel Core thông qua API** (`ui/api_client.py` → FastAPI → Core). UI không trực tiếp gọi Qiskit, XGBoost/LightGBM, scikit-learn, feature engineering hay services.

## Hệ quả

- **Tích cực:** Separation of concerns được bảo vệ; cho phép thay thế client (React, mobile, financial system) mà không đổi Core/API contract.
- **Trung tính:** UI phụ thuộc vào API contract (schema) — schema phải ổn định.
- **Tiêu cực:** Mọi tính năng UI cần API endpoint tương ứng — thêm bước nhưng giữ kiến trúc sạch.