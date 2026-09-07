# ADR-003 — Taipy as Reference Client

## Trạng thái

Accepted

## Bối cảnh

Sentinel cần một presentation layer cho investigation UI trong V1, phù hợp với Python-centric research/product prototype, mà không đưa UI logic vào Core.

## Quyết định

**Taipy là reference UI client V1.** Taipy giao tiếp với Sentinel Core chỉ thông qua API client (`ui/api_client.py`), không gọi trực tiếp Qiskit, models hay services.

## Hệ quả

- **Tích cực:** Xây investigation interface nhanh, giữ UI logic ngoài Core.
- **Trung tính:** Nếu sau này thay Taipy bằng React/Next.js/mobile, Core và API contract vẫn giữ nguyên về nguyên tắc.
- **Tiêu cực:** UI không được tự ý bịa data hay explanation (RULE-09, RULE-45).