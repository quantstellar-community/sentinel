"""
Split stage — tạo MỘT split_manifest.parquet DUY NHẤT, cố định cho toàn bộ project.

QUAN TRỌNG: đây là nguồn sự thật duy nhất về việc dòng nào thuộc train/val/cal/test.
classical_tree, classical_kernel, quantum_kernel KHÔNG được tự split riêng —
tất cả phải join theo split_manifest này để đảm bảo benchmark công bằng
(cùng ID, cùng split, giữa 3 nhánh).

Time-based split theo TransactionDT (KHÔNG random split) để tránh leakage.

4 phần:
    train — dùng để fit imputer/scaler/PCA và train model
    val   — dùng để tune hyperparameter
    cal   — dùng để calibrate threshold/probability (đặc biệt quan trọng cho fraud
            detection vì cần chọn ngưỡng theo precision/recall mong muốn)
    test  — chỉ đánh giá cuối cùng, không được đụng vào trong lúc phát triển

Cách chạy:
    python src/split/split.py \
        --input data/cleaned/merged_cleaned.parquet \
        --output data/manifests/split_manifest.parquet
"""
import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

ID_COL = "TransactionID"
TIME_COL = "TransactionDT"
LABEL_COL = "isFraud"


def create_split_manifest(
    df: pd.DataFrame,
    train_frac: float = 0.60,
    val_frac: float = 0.15,
    cal_frac: float = 0.10,
    test_frac: float = 0.15,
) -> pd.DataFrame:
    total = train_frac + val_frac + cal_frac + test_frac
    assert abs(total - 1.0) < 1e-6, f"Tổng tỷ lệ split phải = 1.0, hiện tại = {total}"

    if TIME_COL not in df.columns:
        raise ValueError(f"Thiếu cột {TIME_COL} — không thể split theo thời gian.")

    # Time-based split: sort theo thời gian, KHÔNG shuffle, KHÔNG random.
    df_sorted = df.sort_values(TIME_COL).reset_index(drop=True)
    n = len(df_sorted)

    train_end = int(n * train_frac)
    val_end = train_end + int(n * val_frac)
    cal_end = val_end + int(n * cal_frac)

    split = np.empty(n, dtype=object)
    split[:train_end] = "train"
    split[train_end:val_end] = "val"
    split[val_end:cal_end] = "cal"
    split[cal_end:] = "test"

    manifest = pd.DataFrame(
        {
            ID_COL: df_sorted[ID_COL].values,
            "split": split,
            "label": df_sorted[LABEL_COL].values if LABEL_COL in df_sorted.columns else np.nan,
            TIME_COL: df_sorted[TIME_COL].values,
        }
    )

    for s in ["train", "val", "cal", "test"]:
        part = manifest[manifest["split"] == s]
        fraud_rate = part["label"].mean() if part["label"].notna().any() else float("nan")
        logger.info(f"  {s}: {len(part)} dòng, fraud_rate={fraud_rate:.4f}")

    return manifest


def run(input_path: Path, output_path: Path, **frac_kwargs) -> None:
    logger.info(f"Đọc {input_path} ...")
    df = pd.read_parquet(input_path, columns=[ID_COL, TIME_COL, LABEL_COL])

    logger.info("Tạo split_manifest (time-based, KHÔNG random) ...")
    manifest = create_split_manifest(df, **frac_kwargs)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    manifest.to_parquet(output_path, index=False)
    logger.info(f"Đã lưu split_manifest ({manifest.shape}) vào {output_path}")
    logger.info(
        "LƯU Ý: file này là nguồn sự thật duy nhất cho mọi nhánh (tree/kernel/quantum). "
        "Không tạo split riêng ở bước feature engineering."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("data/cleaned/merged_cleaned.parquet"))
    parser.add_argument("--output", type=Path, default=Path("data/manifests/split_manifest.parquet"))
    parser.add_argument("--train-frac", type=float, default=0.60)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--cal-frac", type=float, default=0.10)
    parser.add_argument("--test-frac", type=float, default=0.15)
    args = parser.parse_args()

    run(
        args.input,
        args.output,
        train_frac=args.train_frac,
        val_frac=args.val_frac,
        cal_frac=args.cal_frac,
        test_frac=args.test_frac,
    )
