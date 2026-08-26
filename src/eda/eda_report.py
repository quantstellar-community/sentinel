"""
EDA Report — Fraud Detection Pipeline

Sinh báo cáo EDA tự động sau bước build_features, gồm:
  1. Dataset overview (shape, dtypes, missing ratio)
  2. Fraud rate per split (sanity check split_manifest)
  3. Feature missing heatmap summary (classical_tree)
  4. PCA explained variance (classical_kernel)
  5. Quantum view size check

Output: data/eda/eda_report.json  (machine-readable, CI-friendly)
        data/eda/eda_summary.md   (human-readable, dán vào wiki/PR)

Cach chay:
    python src/eda/eda_report.py
    python src/eda/eda_report.py --output-dir data/eda
"""
import argparse
import json
import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

ID_COL = "TransactionID"
LABEL_COL = "isFraud"
TIME_COL = "TransactionDT"
SPLITS = ["train", "val", "cal", "test"]


# ---------------------------------------------------------------------------
# 1. Dataset overview
# ---------------------------------------------------------------------------
def analyze_cleaned(cleaned_path: Path) -> dict:
    logger.info(f"Reading canonical cleaned data: {cleaned_path}")
    df = pd.read_parquet(cleaned_path)
    n_rows, n_cols = df.shape
    missing_ratio = df.isna().mean()
    top_missing = (
        missing_ratio[missing_ratio > 0]
        .sort_values(ascending=False)
        .head(20)
        .to_dict()
    )
    dtypes_count = df.dtypes.astype(str).value_counts().to_dict()
    return {
        "n_rows": n_rows,
        "n_cols": n_cols,
        "dtypes_count": dtypes_count,
        "top_missing_cols": {k: round(v, 4) for k, v in top_missing.items()},
        "overall_missing_ratio": round(missing_ratio.mean(), 4),
        "fraud_rate_overall": round(df[LABEL_COL].mean(), 6) if LABEL_COL in df.columns else None,
    }


# ---------------------------------------------------------------------------
# 2. Fraud rate + row count per split
# ---------------------------------------------------------------------------
def analyze_manifest(manifest_path: Path) -> dict:
    logger.info(f"Reading split_manifest: {manifest_path}")
    manifest = pd.read_parquet(manifest_path)
    stats = {}
    for s in SPLITS:
        part = manifest[manifest["split"] == s]
        fraud_rate = float(part["label"].mean()) if "label" in part.columns else None
        stats[s] = {
            "n_rows": int(len(part)),
            "fraud_rate": round(fraud_rate, 6) if fraud_rate is not None else None,
            "n_fraud": int(part["label"].sum()) if "label" in part.columns else None,
        }
    return stats


# ---------------------------------------------------------------------------
# 3. Classical tree view — missing summary per split
# ---------------------------------------------------------------------------
def analyze_classical_tree(views_dir: Path) -> dict:
    tree_dir = views_dir / "classical_tree"
    result = {}
    for s in SPLITS:
        f = tree_dir / f"{s}.parquet"
        if not f.exists():
            result[s] = {"error": "file not found"}
            continue
        df = pd.read_parquet(f)
        result[s] = {
            "shape": list(df.shape),
            "missing_ratio_mean": round(float(df.isna().mean().mean()), 4),
            "n_cols_with_missing": int((df.isna().sum() > 0).sum()),
        }
    return result


# ---------------------------------------------------------------------------
# 4. Classical kernel view + PCA artifact
# ---------------------------------------------------------------------------
def analyze_kernel_and_pca(views_dir: Path, artifacts_dir: Path, n_components: int) -> dict:
    kernel_dir = views_dir / f"classical_kernel_{n_components}f"
    result = {"splits": {}}

    for s in SPLITS:
        f = kernel_dir / f"{s}.parquet"
        if not f.exists():
            result["splits"][s] = {"error": "file not found"}
            continue
        df = pd.read_parquet(f)
        pc_cols = [c for c in df.columns if c.startswith("pc_")]
        result["splits"][s] = {
            "shape": list(df.shape),
            "n_pc_cols": len(pc_cols),
            "pc_value_range": {
                "min": round(float(df[pc_cols].min().min()), 6),
                "max": round(float(df[pc_cols].max().max()), 6),
            },
        }

    # PCA artifact
    pca_path = artifacts_dir / f"pca_{n_components}.joblib"
    if pca_path.exists():
        pca = joblib.load(pca_path)
        evr = pca.explained_variance_ratio_
        result["pca"] = {
            "n_components": int(n_components),
            "explained_variance_ratio": [round(float(v), 6) for v in evr],
            "cumulative_explained_variance": round(float(evr.sum()), 6),
            "note": "PENDING confirmation of n_components (=n_qubits) from Quantum team",
        }

    return result


# ---------------------------------------------------------------------------
# 5. Quantum view sanity check
# ---------------------------------------------------------------------------
def analyze_quantum(views_dir: Path, n_components: int) -> dict:
    q_dir = views_dir / f"quantum_{n_components}q"
    result = {}
    for s in SPLITS + ["train_normal_only"]:
        f = q_dir / f"{s}.parquet"
        if not f.exists():
            result[s] = {"error": "file not found"}
            continue
        df = pd.read_parquet(f)
        pc_cols = [c for c in df.columns if c.startswith("pc_")]
        result[s] = {
            "shape": list(df.shape),
            "pc_value_range": {
                "min": round(float(df[pc_cols].min().min()), 6),
                "max": round(float(df[pc_cols].max().max()), 6),
            },
        }
    return result


# ---------------------------------------------------------------------------
# Tao markdown summary
# ---------------------------------------------------------------------------
def build_markdown(report: dict) -> str:
    d = report
    ov = d["dataset_overview"]
    sp = d["split_stats"]

    lines = [
        "# EDA Report — Fraud Detection Pipeline",
        "",
        f"> Generated: {d['generated_at']}  ",
        f"> Canonical data: {d['input_paths']['cleaned']}",
        "",
        "## 1. Dataset Overview",
        "",
        f"| Item | Value |",
        f"|---|---|",
        f"| Rows | {ov['n_rows']:,} |",
        f"| Columns | {ov['n_cols']:,} |",
        f"| Overall missing ratio | {ov['overall_missing_ratio']:.1%} |",
        f"| Overall fraud rate | {ov['fraud_rate_overall']:.2%} |",
        "",
        "## 2. Split Stats (from split_manifest)",
        "",
        "| Split | Rows | Fraud | Fraud Rate |",
        "|---|---|---|---|",
    ]
    for s in SPLITS:
        st = sp[s]
        lines.append(f"| {s} | {st['n_rows']:,} | {st['n_fraud']:,} | {st['fraud_rate']:.2%} |")

    lines += [
        "",
        "## 3. Classical Tree View — Missing Summary",
        "",
        "| Split | Shape | Mean Missing | Cols w/ Missing |",
        "|---|---|---|---|",
    ]
    for s in SPLITS:
        ct = d["classical_tree"][s]
        if "error" in ct:
            lines.append(f"| {s} | ERROR | — | — |")
        else:
            lines.append(
                f"| {s} | {ct['shape'][0]:,} × {ct['shape'][1]} "
                f"| {ct['missing_ratio_mean']:.1%} | {ct['n_cols_with_missing']} |"
            )

    pca = d["classical_kernel_and_pca"].get("pca", {})
    evr = pca.get("explained_variance_ratio", [])
    lines += [
        "",
        "## 4. PCA (classical_kernel + quantum shared)",
        "",
        f"- n_components: **{pca.get('n_components', '?')}** (pending Quantum team confirmation)",
        f"- Cumulative explained variance: **{pca.get('cumulative_explained_variance', '?'):.1%}**",
        "",
        "| PC | Explained Variance |",
        "|---|---|",
    ]
    for i, v in enumerate(evr):
        lines.append(f"| pc_{i} | {v:.4%} |")

    lines += [
        "",
        "## 5. Quantum View Size Check",
        "",
        "| Split | Shape | PC range [min, max] |",
        "|---|---|---|",
    ]
    for s in SPLITS + ["train_normal_only"]:
        qv = d["quantum_view"].get(s, {})
        if "error" in qv:
            lines.append(f"| {s} | ERROR | — |")
        else:
            r = qv["pc_value_range"]
            lines.append(
                f"| {s} | {qv['shape'][0]:,} × {qv['shape'][1]} "
                f"| [{r['min']:.3f}, {r['max']:.3f}] |"
            )

    lines += [
        "",
        "---",
        "> **Note:** quantum PC values should be in [0, π] ≈ [0, 3.14].",
        "> If range differs, verify `quantum_encoding_min/max` in `params.yaml`.",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
def main(
    cleaned_path: Path,
    manifest_path: Path,
    views_dir: Path,
    artifacts_dir: Path,
    output_dir: Path,
    n_components: int,
) -> None:
    import datetime
    output_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "generated_at": datetime.datetime.now().isoformat(),
        "input_paths": {
            "cleaned": str(cleaned_path),
            "manifest": str(manifest_path),
            "views_dir": str(views_dir),
            "artifacts_dir": str(artifacts_dir),
        },
        "n_components": n_components,
        "dataset_overview": analyze_cleaned(cleaned_path),
        "split_stats": analyze_manifest(manifest_path),
        "classical_tree": analyze_classical_tree(views_dir),
        "classical_kernel_and_pca": analyze_kernel_and_pca(views_dir, artifacts_dir, n_components),
        "quantum_view": analyze_quantum(views_dir, n_components),
    }

    json_path = output_dir / "eda_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved JSON report: {json_path}")

    md_path = output_dir / "eda_summary.md"
    md_path.write_text(build_markdown(report), encoding="utf-8")
    logger.info(f"Saved Markdown summary: {md_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cleaned", type=Path, default=Path("data/cleaned/merged_cleaned.parquet"))
    parser.add_argument("--manifest", type=Path, default=Path("data/manifests/split_manifest.parquet"))
    parser.add_argument("--views-dir", type=Path, default=Path("data/views"))
    parser.add_argument("--artifacts-dir", type=Path, default=Path("data/artifacts"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/eda"))
    parser.add_argument("--n-components", type=int, default=8)
    args = parser.parse_args()

    main(
        cleaned_path=args.cleaned,
        manifest_path=args.manifest,
        views_dir=args.views_dir,
        artifacts_dir=args.artifacts_dir,
        output_dir=args.output_dir,
        n_components=args.n_components,
    )
