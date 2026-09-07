# ADR-005 — Quantum Inside Core Boundary

## Trạng thái

Accepted

## Bối cảnh

Sentinel có cả Classical và Quantum computation. Cần quyết định Quantum là một service/microservice riêng hay nằm trong Core.

## Quyết định

**Quantum là module computation trong Sentinel Core** (`src/sentinel/models/quantum/`), không phải microservice riêng ở V1. Quantum không định nghĩa financial/business semantics — chỉ cung cấp computational result cho application layer (RULE-15).

## Hệ quả

- **Tích cực:** Giữ computation, model evaluation và application orchestration gần nhau; chưa có workload justification cho quantum service độc lập.
- **Trung tính:** Nếu quantum execution trở thành long-running workload thực tế, có thể chuyển sang job-based execution nhưng là future option, không phải V1 requirement.
- **Tiêu cực:** Cần đảm bảo Classical độc lập với Quantum availability (RULE-14).