# ADR-006 — Classical Independent from Quantum

## Trạng thái

Accepted

## Bối cảnh

Quantum backend có thể unavailable. Sentinel phải vẫn functional khi Quantum path không chạy được.

## Quyết định

**Classical pipeline phải hoạt động độc lập với Quantum.** Classical intelligence không được phụ thuộc vào Quantum availability (RULE-14).

## Hệ quả

- **Tích cực:** Sentinel còn hoạt động khi Quantum backend unavailable; Classical là baseline bắt buộc cho mọi Quantum so sánh.
- **Trung tính:** Quantum chỉ là enhancement layer được gọi khi routing policy yêu cầu.
- **Tiêu cực:** Cần tránh tạo dependency khiến toàn bộ product fail vì Quantum path không available.