# ADR-011 — Temporal Split 70/15/15

## Trạng thái

Accepted

## Bối cảnh

Bài toán fraud có temporal information. Chia ngẫu nhiên sẽ làm rò rỉ tương lai vào train (RULE-27, RULE-28). Cần một split tôn trọng trật tự thời gian để đánh giá đúng.

## Quyết định

Chia dữ liệu **strict theo thời gian** (train < validation < test), **không shuffle**, tỷ lệ mặc định **70/15/15** cấu hình được qua `configs/dev.yaml`. Scaler (StandardScaler cho `Amount`) chỉ fit trên **train**, transform validation/test bằng cùng scaler đó để tránh feature leakage.

## Hệ quả

- **Tích cực:** Không leakage về thời gian; đánh giá đúng hành vi trên dữ liệu tương lai; reproducible (tỷ lệ + seed trong config).
- **Trung tính:** Tỷ lệ split nằm trong config, có thể điều chỉnh cho từng experiment.
- **Tiêu cực:** Phần test nhỏ hơn so với random split; dataset không có entity nên không xây được behavioral trajectory dài hạn (giới hạn đã ghi nhận trong thesis §5).