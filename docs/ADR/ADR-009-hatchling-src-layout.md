# ADR-009 — Hatchling + src-layout Packaging

## Trạng thái

Accepted

## Bối cảnh

Code nằm trong `src/sentinel/` (src-layout) nhưng `pyproject.toml` thiếu `[build-system]` và không có package discovery config, nên package `sentinel` không cài được và `import sentinel` fail.

## Quyết định

Thêm `[build-system]` dùng **Hatchling** và khai báo `[tool.hatch.build.targets.wheel] packages = ["src/sentinel"]`. Dùng `uv sync` để cài package dạng editable. Đồng thời bỏ `xgboost` khỏi dependencies vì thesis chọn LightGBM (không giữ cả hai trong core).

## Hệ quả

- **Tích cực:** `import sentinel` hoạt động; editable install giúp sửa code có hiệu lực ngay, không cần cài lại; src-layout ngăn import nhầm.
- **Trung tính:** `uv.lock` thay đổi khi thay đổi dependencies.
- **Tiêu cực:** Cần `uv sync` lại mỗi khi pyproject thay đổi.