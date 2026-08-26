"""
Airflow DAG — Fraud Detection ETL/ELT + EDA Pipeline

Orchestrate 5 stage theo thu tu:
    extract -> clean -> split -> build_features -> eda

Moi stage goi `dvc repro <stage>` de:
  - Tan dung DVC cache (khong re-run neu input/code/params khong doi)
  - Airflow theo doi tung task rieng biet (visibility, retry, alert)
  - MLOps team co the trigger thu cong tung stage neu can debug

Cach dang ky DAG voi Airflow:
    cp dags/fraud_detection_dag.py $AIRFLOW_HOME/dags/
    airflow dags list          # kiem tra da nhan dien
    airflow dags trigger fraud_detection_pipeline

Bien moi truong can thiet:
    PIPELINE_ROOT  — absolute path den thu muc goc cua project
                     Vi du: /opt/fraud_detection_quantum
    VENV_PYTHON    — path den python trong venv
                     Vi du: /opt/fraud_detection_quantum/.venv/bin/python
                     Mac dinh: {PIPELINE_ROOT}/.venv/Scripts/python.exe (Windows)
"""
import os
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

# ---------------------------------------------------------------------------
# Config — thay doi o day, khong phai trong tung task
# ---------------------------------------------------------------------------
PIPELINE_ROOT = os.environ.get(
    "PIPELINE_ROOT",
    str(Path(__file__).resolve().parent.parent),  # root cua project
)
VENV_PYTHON = os.environ.get(
    "VENV_PYTHON",
    str(Path(PIPELINE_ROOT) / ".venv" / "Scripts" / "python.exe"),
)
DVC_BIN = os.environ.get(
    "DVC_BIN",
    str(Path(PIPELINE_ROOT) / ".venv" / "Scripts" / "dvc.exe"),
)
N_COMPONENTS = int(os.environ.get("N_COMPONENTS", "8"))

# ---------------------------------------------------------------------------
# Default args cho moi task
# ---------------------------------------------------------------------------
DEFAULT_ARGS = {
    "owner": "data-engineering",
    "depends_on_past": False,               # moi DAG run doc lap nhau
    "email_on_failure": False,              # bat sau khi co SMTP config
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(hours=3),
}

# ---------------------------------------------------------------------------
# DAG definition
# ---------------------------------------------------------------------------
with DAG(
    dag_id="fraud_detection_pipeline",
    description=(
        "ETL/ELT + EDA pipeline cho Fraud Detection (Quantum + Classical ML). "
        "4 stage ETL: extract->clean->split->build_features (via DVC). "
        "1 stage EDA: sinh bao cao san sang cho downstream team."
    ),
    default_args=DEFAULT_ARGS,
    start_date=days_ago(1),
    schedule_interval=None,   # Manual trigger — day la training pipeline, khong chay theo lich
    catchup=False,            # Khong backfill khi DAG duoc kich hoat lan dau
    tags=["fraud-detection", "data-engineering", "etl", "eda"],
    doc_md="""
## Fraud Detection — Data Pipeline

**Owner:** Data Engineering  
**Downstream:** Classical ML, Quantum 1, Quantum 2, UI/API  

### Stage order
```
extract → clean → split → build_features → eda
```

### Cach chay thu cong (debug tung stage)
```bash
airflow tasks test fraud_detection_pipeline extract 2026-01-01
airflow tasks test fraud_detection_pipeline build_features 2026-01-01
```

### Luu y quan trong
- Moi stage deu goi `dvc repro <stage>` — neu input/code/params chua doi,
  DVC se skip va task ket thuc thanh cong ngay lap tuc (cache hit).
- Thay doi tham so: sua `params.yaml` roi trigger DAG lai.
- KHONG tu y sua split hay tao split rieng — split_manifest.parquet
  la nguon su that duy nhat dung chung cho moi nhanh model.
    """,
) as dag:

    # ------------------------------------------------------------------
    # Task 1: Extract — merge transaction + identity CSV -> parquet
    # ------------------------------------------------------------------
    t_extract = BashOperator(
        task_id="extract",
        bash_command=(
            f"cd {PIPELINE_ROOT} && "
            f"{DVC_BIN} repro extract"
        ),
        doc_md="""
**Script:** `src/extraction/extract.py`  
**Input:** `data/raw/train_transaction.csv` + `data/raw/train_identity.csv`  
**Output:** `data/raw/merged.parquet`  
**DVC cached:** yes — skip neu CSV khong thay doi.
        """,
    )

    # ------------------------------------------------------------------
    # Task 2: Clean — tao canonical cleaned data duy nhat
    # ------------------------------------------------------------------
    t_clean = BashOperator(
        task_id="clean",
        bash_command=(
            f"cd {PIPELINE_ROOT} && "
            f"{DVC_BIN} repro clean"
        ),
        doc_md="""
**Script:** `src/cleaning/clean.py`  
**Input:** `data/raw/merged.parquet`  
**Output:** `data/cleaned/merged_cleaned.parquet`  
Tao canonical data DUY NHAT — moi nhanh doc tu day, khong clean rieng.
        """,
    )

    # ------------------------------------------------------------------
    # Task 3: Split — tao split_manifest (nguon su that duy nhat)
    # ------------------------------------------------------------------
    t_split = BashOperator(
        task_id="split",
        bash_command=(
            f"cd {PIPELINE_ROOT} && "
            f"{DVC_BIN} repro split"
        ),
        doc_md="""
**Script:** `src/split/split.py`  
**Input:** `data/cleaned/merged_cleaned.parquet`  
**Output:** `data/manifests/split_manifest.parquet`  
Time-based split (KHONG random). Ty le: train=60% / val=15% / cal=10% / test=15%.  
**KHONG nhanh nao duoc tu split rieng** — phai join vao file manifest nay.
        """,
    )

    # ------------------------------------------------------------------
    # Task 4: Build Features — tao 3 view + fit artifacts
    # ------------------------------------------------------------------
    t_build_features = BashOperator(
        task_id="build_features",
        bash_command=(
            f"cd {PIPELINE_ROOT} && "
            f"{DVC_BIN} repro build_features"
        ),
        doc_md="""
**Script:** `src/feature_engineering/build_features.py`  
**Output:**
- `data/views/classical_tree/` — full features, giu NaN, cho LightGBM/XGBoost
- `data/views/classical_kernel_Nf/` — impute+PCA+scale[0,1], cho OCSVM classical
- `data/views/quantum_Nq/` — impute+PCA+scale[0,pi], cho Quantum 1/2
- `data/artifacts/` — imputer/pca/scaler joblib da fit tren train

Imputer/PCA/Scaler chi fit tren tap `train` — khong leakage.
        """,
    )

    # ------------------------------------------------------------------
    # Task 5: EDA — sinh bao cao tu dong
    # ------------------------------------------------------------------
    t_eda = BashOperator(
        task_id="eda",
        bash_command=(
            f"cd {PIPELINE_ROOT} && "
            f"{VENV_PYTHON} src/eda/eda_report.py "
            f"--cleaned data/cleaned/merged_cleaned.parquet "
            f"--manifest data/manifests/split_manifest.parquet "
            f"--views-dir data/views "
            f"--artifacts-dir data/artifacts "
            f"--output-dir data/eda "
            f"--n-components {N_COMPONENTS}"
        ),
        doc_md="""
**Script:** `src/eda/eda_report.py`  
**Output:**
- `data/eda/eda_report.json` — machine-readable (CI/CD friendly)
- `data/eda/eda_summary.md` — human-readable, dan vao wiki/PR

Bao gom: dataset overview, fraud rate per split, missing analysis,
PCA explained variance, quantum view range check.

**Note:** EDA khong anh huong den data/features — chi doc, khong ghi vao views.
        """,
    )

    # ------------------------------------------------------------------
    # Dependencies — thu tu bat buoc
    # ------------------------------------------------------------------
    t_extract >> t_clean >> t_split >> t_build_features >> t_eda
