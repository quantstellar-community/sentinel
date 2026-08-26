"""
Cleaning stage — tạo CANONICAL cleaned data (nguồn dữ liệu chung duy nhất).

Đây là bước cleaning DUY NHẤT áp dụng cho toàn bộ project — mọi nhánh
(tree/kernel/quantum) đều bắt đầu từ cùng 1 file output ở đây, KHÔNG tự
clean riêng theo cách khác nhau.

Cách chạy:
    python src/cleaning/clean.py --input data/raw/merged.parquet --output data/cleaned/merged_cleaned.parquet
"""
import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

KEEP_EVEN_IF_HIGH_MISSING_PREFIXES = ("V",)
MISSING_DROP_THRESHOLD = 0.95


def drop_high_missing_columns(df: pd.DataFrame, threshold: float) -> pd.DataFrame:
    missing_ratio = df.isna().mean()
    cols_to_check = missing_ratio[missing_ratio > threshold].index.tolist()
    cols_to_drop = [
        c for c in cols_to_check
        if not c.startswith(KEEP_EVEN_IF_HIGH_MISSING_PREFIXES)
    ]
    if cols_to_drop:
        logger.info(f"Bỏ {len(cols_to_drop)} cột missing > {threshold*100:.0f}%: {cols_to_drop[:10]}...")
        df = df.drop(columns=cols_to_drop)
    return df


def add_missing_indicators(df: pd.DataFrame, prefixes=("V", "id_")) -> pd.DataFrame:
    for prefix in prefixes:
        cols = [c for c in df.columns if c.startswith(prefix)]
        if cols:
            df[f"{prefix}missing_count"] = df[cols].isna().sum(axis=1).astype("int16")
    return df


def clean_transaction_amt(df: pd.DataFrame) -> pd.DataFrame:
    if "TransactionAmt" in df.columns:
        df["TransactionAmt"] = df["TransactionAmt"].clip(lower=0)
        df["TransactionAmt_log"] = np.log1p(df["TransactionAmt"])
    return df


def normalize_categoricals(df: pd.DataFrame, min_freq: int = 20) -> pd.DataFrame:
    """Gộp category hiếm thành 'rare'. Lưu ý: threshold này tính trên toàn bộ data
    (train+val+cal+test) — chấp nhận được vì đây chỉ là gộp nhãn hiếm, không học
    tham số thống kê nhạy cảm (khác với impute/scale/PCA phải fit riêng trên train)."""
    cat_cols = df.select_dtypes(include=["category", "object"]).columns
    for col in cat_cols:
        vc = df[col].value_counts()
        rare = vc[vc < min_freq].index
        if len(rare) > 0:
            df[col] = df[col].astype("object")
            df.loc[df[col].isin(rare), col] = "rare"
            df[col] = df[col].astype("category")
    return df


def clean(input_path: Path, output_path: Path) -> None:
    logger.info(f"Đọc {input_path} ...")
    df = pd.read_parquet(input_path)
    logger.info(f"Shape ban đầu: {df.shape}")

    df = add_missing_indicators(df)
    df = drop_high_missing_columns(df, MISSING_DROP_THRESHOLD)
    df = clean_transaction_amt(df)
    df = normalize_categoricals(df)

    logger.info(f"Shape sau cleaning: {df.shape}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)
    logger.info(f"Đã lưu canonical cleaned data vào {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("data/raw/merged.parquet"))
    parser.add_argument("--output", type=Path, default=Path("data/cleaned/merged_cleaned.parquet"))
    args = parser.parse_args()

    clean(args.input, args.output)
