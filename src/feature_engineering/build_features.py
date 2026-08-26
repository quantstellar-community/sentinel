"""
Feature Engineering stage — v1 (đã sửa theo kiến trúc canonical + shared views)

NGUYÊN TẮC BẮT BUỘC:
    1. KHÔNG tự split — join với data/manifests/split_manifest.parquet (nguồn sự thật duy nhất).
    2. Mọi imputer/scaler/PCA CHỈ fit trên tập 'train', sau đó transform cho val/cal/test
       (tuyệt đối không fit lại trên test — tránh leakage).
    3. classical_kernel và quantum_kernel dùng CHUNG một PCA fit trên train — quantum view
       là phép biến đổi TIẾP từ kernel view (thêm 1 bước scale sang range của quantum encoding),
       không phải một pipeline độc lập.
    4. Lưu lại toàn bộ artifact (imputer, pca, scaler) ra .joblib để có thể transform
       dữ liệu mới sau này mà không cần fit lại.

Output — 3 "views" derive từ cùng 1 canonical data + cùng 1 split:
    data/views/classical_tree/{train,val,cal,test}.parquet
    data/views/classical_kernel_{n}f/{train,val,cal,test,train_normal_only}.parquet
    data/views/quantum_{n}q/{train,val,cal,test,train_normal_only}.parquet

Cách chạy:
    python src/feature_engineering/build_features.py \
        --input data/cleaned/merged_cleaned.parquet \
        --manifest data/manifests/split_manifest.parquet \
        --output-dir data/views \
        --artifacts-dir data/artifacts \
        --n-components 8 \
        --quantum-max-samples 3000
"""
import argparse
import json
import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import MinMaxScaler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

ID_COL = "TransactionID"
LABEL_COL = "isFraud"
TIME_COL = "TransactionDT"
SPLITS = ["train", "val", "cal", "test"]


# ---------------------------------------------------------------------------
# Load canonical data + join với split_manifest (nguồn sự thật duy nhất)
# ---------------------------------------------------------------------------
def load_canonical_with_split(input_path: Path, manifest_path: Path) -> pd.DataFrame:
    logger.info(f"Đọc canonical data: {input_path}")
    df = pd.read_parquet(input_path)

    logger.info(f"Đọc split_manifest: {manifest_path}")
    manifest = pd.read_parquet(manifest_path, columns=[ID_COL, "split"])

    df = df.merge(manifest, on=ID_COL, how="inner")
    missing_split = df["split"].isna().sum()
    if missing_split > 0:
        logger.warning(
            f"{missing_split} dòng không có trong split_manifest — bị loại "
            f"(có thể do canonical data mới hơn manifest, cần chạy lại split.py)"
        )
        df = df.dropna(subset=["split"])

    for s in SPLITS:
        logger.info(f"  split={s}: {(df['split'] == s).sum()} dòng")
    return df


# ---------------------------------------------------------------------------
# Feature engineering chung (áp dụng trên toàn bộ trước khi tách view)
# - add_time_features: biến đổi theo hàng, không học tham số → không leakage
# - add_frequency_features: expanding count theo thời gian → không leakage (đã fix Pha 2)
# ---------------------------------------------------------------------------
def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    if TIME_COL in df.columns:
        seconds_in_day = 24 * 60 * 60
        df["hour_of_day"] = ((df[TIME_COL] // 3600) % 24).astype("int8")
        df["day_of_week"] = ((df[TIME_COL] // seconds_in_day) % 7).astype("int8")
    return df


def add_frequency_features(df: pd.DataFrame) -> pd.DataFrame:
    """Expanding count theo thời gian — KHÔNG data leakage.

    Với mỗi giao dịch, đếm số lần card1/addr1 đã xuất hiện tính đến thời điểm đó
    (TransactionDT <= hiện tại, inclusive). Chỉ nhìn quá khứ → không rò rỉ tương lai.

    Cách hoạt động:
        1. Sort toàn bộ df theo TransactionDT (stable sort để giữ thứ tự khi tie).
        2. groupby(col).cumcount() → số lần value đó đã xuất hiện TRƯỚC dòng hiện tại (0-indexed).
        3. +1 → tính inclusive (kể cả lần xuất hiện hiện tại).

    So sánh với cách cũ (Pha 1):
        Cũ: df[col].value_counts() tính tổng toàn bộ df → giao dịch đầu tiên đã biết
            tổng số lần card đó xuất hiện trong tương lai → leakage.
        Mới: cumcount() chỉ đếm dựa trên các dòng đứng trước theo thời gian → clean.

    Lưu ý: df trả về sẽ được sort theo TransactionDT — downstream (save_view_by_split)
    chỉ filter theo split nên thứ tự dòng không ảnh hưởng đến correctness.
    """
    if TIME_COL not in df.columns:
        logger.warning(f"Thiếu cột {TIME_COL} — bỏ qua add_frequency_features.")
        return df

    # Sort stable theo thời gian: đảm bảo cumcount() đếm đúng thứ tự temporal
    df = df.sort_values(TIME_COL, kind="mergesort").copy()

    for col in ["card1", "addr1"]:
        if col in df.columns:
            # observed=True: bỏ qua categories không xuất hiện (tránh warning pandas >= 2.2)
            # sort=False: không sort lại keys của groupby, giữ thứ tự df đã sort theo thời gian
            # fillna(0): groupby bỏ qua NaN key → cumcount() trả NaN cho dòng đó
            #   → freq=0 nghĩa là "không có lịch sử / card/addr không xác định"
            df[f"{col}_freq"] = (
                df.groupby(col, observed=True, sort=False).cumcount() + 1
            ).fillna(0).astype("int32")

    return df


def engineer_base_features(df: pd.DataFrame) -> pd.DataFrame:
    df = add_time_features(df)
    df = add_frequency_features(df)
    return df


# ---------------------------------------------------------------------------
# Helper: lưu 1 view theo từng split (+ train_normal_only nếu cần cho OCSVM)
# ---------------------------------------------------------------------------
def save_view_by_split(df: pd.DataFrame, out_dir: Path, with_normal_only: bool = False) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for s in SPLITS:
        part = df[df["split"] == s]
        part.to_parquet(out_dir / f"{s}.parquet", index=False)
        logger.info(f"  -> {out_dir.name}/{s}.parquet: {part.shape}")

    if with_normal_only and LABEL_COL in df.columns:
        train_normal = df[(df["split"] == "train") & (df[LABEL_COL] == 0)]
        train_normal.to_parquet(out_dir / "train_normal_only.parquet", index=False)
        logger.info(f"  -> {out_dir.name}/train_normal_only.parquet: {train_normal.shape}")


# ---------------------------------------------------------------------------
# View 1: classical_tree — giữ full feature, giữ NaN, không PCA
# ---------------------------------------------------------------------------
def build_classical_tree(df: pd.DataFrame, output_dir: Path) -> None:
    out_dir = output_dir / "classical_tree"
    save_view_by_split(df, out_dir, with_normal_only=False)

    cat_cols = df.select_dtypes(include=["category"]).columns.tolist()
    with open(out_dir / "categorical_cols.txt", "w") as f:
        f.write("\n".join(cat_cols))
    logger.info(f"[classical_tree] Hoàn tất, {len(cat_cols)} cột categorical.")


# ---------------------------------------------------------------------------
# View 2 + 3: classical_kernel & quantum — dùng CHUNG imputer + PCA fit trên train,
# quantum là phép biến đổi TIẾP từ kernel view (chỉ khác bước scale cuối).
# ---------------------------------------------------------------------------
def build_kernel_and_quantum_views(
    df: pd.DataFrame,
    output_dir: Path,
    artifacts_dir: Path,
    n_components: int,
    quantum_encoding_range: tuple[float, float],
    quantum_max_samples: int,
    random_state: int = 42,
) -> None:
    exclude_cols = {ID_COL, LABEL_COL, TIME_COL, "has_identity", "split"}
    numeric_cols = [
        c for c in df.select_dtypes(include=[np.number]).columns if c not in exclude_cols
    ]
    logger.info(f"Số numeric feature dùng cho kernel/quantum view: {len(numeric_cols)}")

    train_mask = df["split"] == "train"
    X_all = df[numeric_cols]
    X_train = X_all[train_mask]

    # --- Bước 1: impute — FIT CHỈ TRÊN TRAIN, transform cho toàn bộ ---
    imputer = SimpleImputer(strategy="median")
    imputer.fit(X_train)
    X_imputed = imputer.transform(X_all)

    # --- Bước 2: PCA — FIT CHỈ TRÊN TRAIN (đã impute), transform cho toàn bộ ---
    n_components = min(n_components, X_imputed.shape[1])
    pca = PCA(n_components=n_components, random_state=random_state)
    X_train_imputed = imputer.transform(X_train)
    pca.fit(X_train_imputed)
    components_all = pca.transform(X_imputed)

    explained = pca.explained_variance_ratio_.sum()
    logger.info(f"PCA n_components={n_components} (fit trên train), explained_variance={explained:.3f}")

    component_cols = [f"pc_{i}" for i in range(n_components)]
    reduced = pd.DataFrame(components_all, columns=component_cols, index=df.index)
    reduced[ID_COL] = df[ID_COL].values
    reduced["split"] = df["split"].values
    if LABEL_COL in df.columns:
        reduced[LABEL_COL] = df[LABEL_COL].values

    train_components = components_all[train_mask.values]

    # --- View classical_kernel: scale [0,1], FIT CHỈ TRÊN TRAIN ---
    kernel_scaler = MinMaxScaler(feature_range=(0, 1))
    kernel_scaler.fit(train_components)
    kernel_df = reduced.copy()
    kernel_df[component_cols] = kernel_scaler.transform(components_all)

    kernel_out_dir = output_dir / f"classical_kernel_{n_components}f"
    save_view_by_split(kernel_df, kernel_out_dir, with_normal_only=True)

    with open(kernel_out_dir / "scaling_metadata.json", "w") as f:
        json.dump(
            {
                "method": "MinMaxScaler",
                "range": [0, 1],
                "n_components": n_components,
                "fitted_on": "train split only",
            },
            f,
            indent=2,
        )

    # --- View quantum: DẪN XUẤT TỪ kernel components (không PCA lại), chỉ đổi scale ---
    quantum_scaler = MinMaxScaler(feature_range=quantum_encoding_range)
    quantum_scaler.fit(train_components)
    quantum_df = reduced.copy()
    quantum_df[component_cols] = quantum_scaler.transform(components_all)

    # Subsample vì quantum simulator không scale nổi với full data — CHỈ subsample
    # trong nội bộ từng split (không trộn split), giữ tỷ lệ fraud gốc.
    if LABEL_COL in quantum_df.columns:
        parts = []
        for s in SPLITS:
            part = quantum_df[quantum_df["split"] == s]
            if len(part) > quantum_max_samples:
                fraud = part[part[LABEL_COL] == 1]
                normal = part[part[LABEL_COL] == 0]
                frac = quantum_max_samples / len(part)
                sampled = pd.concat(
                    [
                        fraud.sample(frac=frac, random_state=random_state),
                        normal.sample(frac=frac, random_state=random_state),
                    ]
                ).sample(frac=1, random_state=random_state)
                logger.info(f"[quantum] split={s}: subsample {len(part)} -> {len(sampled)}")
            else:
                sampled = part
            parts.append(sampled)
        quantum_df = pd.concat(parts, ignore_index=True)

    quantum_out_dir = output_dir / f"quantum_{n_components}q"
    save_view_by_split(quantum_df, quantum_out_dir, with_normal_only=True)

    with open(quantum_out_dir / "scaling_metadata.json", "w") as f:
        json.dump(
            {
                "method": "MinMaxScaler",
                "range": list(quantum_encoding_range),
                "n_components": n_components,
                "fitted_on": "train split only",
                "derived_from": f"classical_kernel_{n_components}f (cùng PCA, chỉ khác scale cuối)",
                "max_samples_per_split": quantum_max_samples,
                "note": "Xác nhận lại encoding_range, n_components (=số qubit) với "
                        "team Quantum 1/2 trước khi dùng cho production run.",
            },
            f,
            indent=2,
        )

    # --- Lưu artifact để tái sử dụng / transform dữ liệu mới sau này ---
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(imputer, artifacts_dir / "imputer.joblib")
    joblib.dump(pca, artifacts_dir / f"pca_{n_components}.joblib")
    joblib.dump(kernel_scaler, artifacts_dir / f"kernel_scaler_{n_components}f.joblib")
    joblib.dump(quantum_scaler, artifacts_dir / f"quantum_scaler_{n_components}q.joblib")
    logger.info(f"Đã lưu artifact (imputer/pca/scaler) vào {artifacts_dir}")


# ---------------------------------------------------------------------------
def main(
    input_path: Path,
    manifest_path: Path,
    output_dir: Path,
    artifacts_dir: Path,
    n_components: int,
    quantum_encoding_range: tuple[float, float],
    quantum_max_samples: int,
    random_state: int = 42,
) -> None:
    df = load_canonical_with_split(input_path, manifest_path)
    df = engineer_base_features(df)

    build_classical_tree(df, output_dir)
    build_kernel_and_quantum_views(
        df, output_dir, artifacts_dir, n_components, quantum_encoding_range,
        quantum_max_samples, random_state=random_state,
    )

    logger.info("Hoàn tất build_features v1 — 3 view cùng chung split_manifest + PCA fit trên train.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("data/cleaned/merged_cleaned.parquet"))
    parser.add_argument("--manifest", type=Path, default=Path("data/manifests/split_manifest.parquet"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/views"))
    parser.add_argument("--artifacts-dir", type=Path, default=Path("data/artifacts"))
    parser.add_argument("--n-components", type=int, default=8)
    parser.add_argument("--quantum-encoding-min", type=float, default=0.0)
    parser.add_argument("--quantum-encoding-max", type=float, default=np.pi)
    parser.add_argument("--quantum-max-samples", type=int, default=3000)
    parser.add_argument(
        "--random-seed", type=int, default=42,
        help="Random seed for PCA and quantum subsampling. Must match params.yaml."
    )
    args = parser.parse_args()

    main(
        input_path=args.input,
        manifest_path=args.manifest,
        output_dir=args.output_dir,
        artifacts_dir=args.artifacts_dir,
        n_components=args.n_components,
        quantum_encoding_range=(args.quantum_encoding_min, args.quantum_encoding_max),
        quantum_max_samples=args.quantum_max_samples,
        random_state=args.random_seed,
    )
