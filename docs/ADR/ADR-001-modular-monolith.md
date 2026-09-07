# ADR-001 — Modular Monolith

## Trạng thái

Accepted

## Bối cảnh

Sentinel cần một kiến trúc giữ được research/development velocity cao nhưng vẫn có module boundaries rõ ràng giữa UI, API, services, domain và models. Không có evidence nào về nhu cầu scale-out ở V1.

## Quyết định

Sentinel V1 sử dụng **Modular Monolith**: một repository, một application boundary, các module có responsibility rõ ràng, một FastAPI product interface và một Taipy reference client. Không tách microservices chỉ vì các module được gọi là "service".

## Hệ quả

- **Tích cực:** Velocity cao, ít infrastructure complexity, module boundaries vẫn rõ ràng.
- **Trung tính:** Module boundary và process boundary là hai khái niệm khác nhau; chỉ tách process khi workload thực sự yêu cầu.
- **Tiêu cực:** Cần kỷ luật để không biến modular monolith thành god application.