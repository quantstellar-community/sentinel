# ADR-008 — No Premature Infrastructure

## Trạng thái

Accepted

## Bối cảnh

Có sức hút khi thêm microservices, Kubernetes, Kafka, Airflow/Prefect cho một dự án "enterprise-looking", nhưng Sentinel V1 chưa có requirement cho distributed infrastructure.

## Quyết định

**Không thêm microservices, Kubernetes, Kafka, Airflow/Prefect hoặc distributed infrastructure vào V1** nếu chưa có measurable requirement (RULE-17). Kiến trúc chỉ mở rộng khi workload hoặc product requirement thực sự yêu cầu.

## Hệ quả

- **Tích cực:** Tránh over-engineering; giữ architecture aligned với actual workload.
- **Trung tính:** Scalability path rõ ràng: modular monolith → measure → identify bottleneck → optimize → scale specific component.
- **Tiêu cực:** Cần kỷ luật để không thêm infrastructure chỉ vì trông chuyên nghiệp hơn.