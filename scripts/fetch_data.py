"""Tải European credit-card dataset từ Kaggle về data/raw/.

Cách chạy:
    uv run python scripts/fetch_data.py

Yêu cầu:
    - Kaggle account và API credentials (kaggle.json) đặt tại ~/.kaggle/kaggle.json
    - Xem hướng dẫn chi tiết tại data/README.md
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import kagglehub

DATASET_ID = "mlg-ulb/creditcardfraud"
TARGET_FILE = "creditcard.csv"

DEFAULT_RAW_DIR = Path("data/raw")


def fetch_data(raw_dir: Path, force: bool = False) -> Path:
    """Tải dataset credit-card từ Kaggle về raw_dir.

    Args:
        raw_dir: Thư mục đích (mặc định data/raw).
        force: Tải lại ngay cả khi file đã tồn tại.

    Returns:
        Đường dẫn tới file creditcard.csv đã tải.
    """
    target = raw_dir / TARGET_FILE
    if target.exists() and not force:
        print(f"File đã tồn tại: {target} — bỏ qua (dùng --force để tải lại)")
        return target

    raw_dir.mkdir(parents=True, exist_ok=True)

    print(f"Tải dataset từ Kaggle: {DATASET_ID}")
    download_path = Path(kagglehub.dataset_download(DATASET_ID))

    source = download_path / TARGET_FILE
    if not source.exists():
        raise FileNotFoundError(f"Không tìm thấy {TARGET_FILE} trong {download_path}")

    shutil.copy2(source, target)
    print(f"Đã tải xong: {target}")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="Tải credit-card dataset từ Kaggle")
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR, help="Thư mục đích")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Tải lại ngay cả khi file đã tồn tại",
    )
    args = parser.parse_args()

    fetch_data(args.raw_dir, force=args.force)


if __name__ == "__main__":
    main()