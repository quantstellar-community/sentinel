# ADR-010 — Data Layer Contract (SplitData + config)

## Trạng thái

Accepted

## Bối cảnh

Data layer cần đưa `data/raw/creditcard.csv` thành dữ liệu model-ready mà **models/evaluation không phụ thuộc dataset cụ thể** (để sau này thay sang IEEE CIS hoặc data khách hàng). Cần một contract rõ ràng giữa data layer và tầng trên (RULE-19).

## Quyết định

Data layer trả về **`SplitData`** (dataclass): `train`, `validation`, `test` DataFrame + `feature_columns` + `metadata`. Config qua **YAML** (`configs/dev.yaml`) đọc bằng PyYAML (`src/sentinel/config/settings.py`). Chưa xây adapter đa-dataset trừu tượng (tránh premature abstraction — RULE-52).

## Hệ quả

- **Tích cực:** Models/evaluation chỉ nhìn vào `SplitData`, không biết dataset gốc; metadata giúp reproducibility (RULE-25); thay dataset chỉ cần viết loader mới.
- **Trung tính:** Cần `__init__.py` cho mọi package để import chuẩn.
- **Tiêu cực:** Feature engineering vẫn cần đổi theo từng dataset — adapter không giải quyết được điều đó (và không nên).