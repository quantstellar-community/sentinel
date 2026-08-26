"""
Extraction stage
Merge train_transaction + train_identity, tối ưu dtype để giảm RAM,
xuất ra data/raw/merged.parquet (bước cleaning tiếp theo sẽ tạo canonical data).

Cách chạy:
    python src/extraction/extract.py --data-dir data/raw --output data/raw/merged.parquet
"""
import argparse
import logging
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def optimize_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """Downcast numeric columns để giảm RAM. object columns -> category nếu cardinality thấp."""
    for col in df.columns:
        col_type = df[col].dtype
        if col_type == "float64":
            df[col] = pd.to_numeric(df[col], downcast="float")
        elif col_type == "int64":
            df[col] = pd.to_numeric(df[col], downcast="integer")
        elif col_type == "object":
            n_unique = df[col].nunique(dropna=True)
            if n_unique / max(len(df), 1) < 0.5:
                df[col] = df[col].astype("category")
    return df


def extract(data_dir: Path, output_path: Path, split: str = "train") -> None:
    transaction_path = data_dir / f"{split}_transaction.csv"
    identity_path = data_dir / f"{split}_identity.csv"

    if not transaction_path.exists():
        raise FileNotFoundError(
            f"Không tìm thấy {transaction_path}. "
            f"Đảm bảo đã tải IEEE-CIS dataset vào {data_dir}"
        )

    logger.info(f"Đọc {transaction_path} ...")
    df_transaction = pd.read_csv(transaction_path)
    logger.info(f"transaction shape: {df_transaction.shape}")

    if identity_path.exists():
        logger.info(f"Đọc {identity_path} ...")
        df_identity = pd.read_csv(identity_path)
        logger.info(f"identity shape: {df_identity.shape}")

        logger.info("Left join transaction <- identity trên TransactionID ...")
        df = df_transaction.merge(df_identity, on="TransactionID", how="left")
        df["has_identity"] = df["TransactionID"].isin(df_identity["TransactionID"]).astype("int8")
    else:
        logger.warning(f"Không tìm thấy {identity_path}, chỉ dùng transaction data.")
        df = df_transaction
        df["has_identity"] = 0

    n_dup = df["TransactionID"].duplicated().sum()
    if n_dup > 0:
        logger.warning(f"Phát hiện {n_dup} TransactionID trùng lặp!")

    logger.info("Tối ưu dtype để giảm RAM ...")
    df = optimize_dtypes(df)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)
    logger.info(f"Đã lưu {df.shape} vào {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--output", type=Path, default=Path("data/raw/merged.parquet"))
    parser.add_argument("--split", type=str, default="train", choices=["train", "test"])
    args = parser.parse_args()

    extract(args.data_dir, args.output, args.split)
