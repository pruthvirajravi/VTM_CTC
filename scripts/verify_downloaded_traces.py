import os
import glob
import pandas as pd
import numpy as np

TRACE_DIR = r"C:\Users\pruth\Downloads\VTM CTC Traces\Traces"

def analyze_traces():
    if not os.path.exists(TRACE_DIR):
        print(f"Directory not found: {TRACE_DIR}")
        # Search in parent directory
        parent = r"C:\Users\pruth\Downloads\VTM CTC Traces"
        if os.path.exists(parent):
            print(f"Parent directory contents: {os.listdir(parent)}")
        return

    csv_files = []
    for root, dirs, files in os.walk(TRACE_DIR):
        for f in files:
            if f.endswith(".csv"):
                csv_files.append(os.path.join(root, f))

    print(f"Found {len(csv_files)} CSV files in {TRACE_DIR}\n")

    if not csv_files:
        # Check parent folder as well
        for root, dirs, files in os.walk(r"C:\Users\pruth\Downloads\VTM CTC Traces"):
            for f in files:
                if f.endswith(".csv"):
                    csv_files.append(os.path.join(root, f))
        print(f"Found {len(csv_files)} CSV files across entire parent folder\n")

    if not csv_files:
        print("No CSV files found.")
        return

    summary = []
    total_records = 0
    tr_types = {}
    cbf_dist = {0: 0, 1: 0}
    direction_dist = {}
    stage_dist = {}
    size_dist = {}
    eff_diff_count = 0

    expected_cols = [
        "task_id", "poc", "slice_type", "ctu_addr", "tu_x", "tu_y", "tu_w", "tu_h",
        "tr_eff_w", "tr_eff_h", "comp", "tr_type_hor", "tr_type_ver", "direction",
        "stage", "cbf", "bit_depth", "tree_type", "pred_mode"
    ]

    for fpath in csv_files:
        fname = os.path.basename(fpath)
        try:
            df = pd.read_csv(fpath)
            num_rows = len(df)
            total_records += num_rows

            # Verify columns
            missing_cols = [c for c in expected_cols if c not in df.columns]

            if num_rows > 0:
                # Accumulate distributions
                for col in ["tr_type_hor", "tr_type_ver"]:
                    for val, cnt in df[col].value_counts().items():
                        tr_types[val] = tr_types.get(val, 0) + cnt

                for val, cnt in df["cbf"].value_counts().items():
                    cbf_dist[val] = cbf_dist.get(val, 0) + cnt

                for val, cnt in df["direction"].value_counts().items():
                    direction_dist[val] = direction_dist.get(val, 0) + cnt

                for val, cnt in df["stage"].value_counts().items():
                    stage_dist[val] = stage_dist.get(val, 0) + cnt

                # TU sizes
                sizes = df["tu_w"].astype(str) + "x" + df["tu_h"].astype(str)
                for val, cnt in sizes.value_counts().items():
                    size_dist[val] = size_dist.get(val, 0) + cnt

                # Effective size differences
                eff_diff = (df["tu_w"] != df["tr_eff_w"]) | (df["tu_h"] != df["tr_eff_h"])
                eff_diff_count += eff_diff.sum()

            summary.append({
                "file": fname,
                "rows": num_rows,
                "missing_cols": len(missing_cols),
                "pocs": df["poc"].nunique() if num_rows > 0 else 0,
                "cbf_1_count": (df["cbf"] == 1).sum() if num_rows > 0 else 0,
                "has_mts": any(t in ["DST7", "DCT8", "TS"] for t in df["tr_type_hor"].unique()) if num_rows > 0 else False
            })
        except Exception as e:
            summary.append({
                "file": fname,
                "rows": -1,
                "error": str(e)
            })

    sum_df = pd.DataFrame(summary)
    print("=== SUMMARY OVERVIEW ===")
    print(f"Total CSV Files Evaluated: {len(sum_df)}")
    print(f"Total Rows Extracted: {total_records:,}")
    print(f"Non-empty Files: {(sum_df['rows'] > 0).sum()} / {len(sum_df)}")
    print(f"Files with Valid 19-column Schema: {(sum_df.get('missing_cols', 0) == 0).sum()} / {len(sum_df)}")
    print(f"Tasks with tr_eff != tu_size (HF Zeroing active): {eff_diff_count:,}")
    print(f"CBF Distribution: CBF=0: {cbf_dist.get(0, 0):,}, CBF=1: {cbf_dist.get(1, 0):,}")
    print(f"Direction Distribution: {direction_dist}")
    print(f"Stage Distribution: {stage_dist}")
    print(f"Transform Type Distribution (1D components): {tr_types}")
    print(f"Top TU Geometries: {dict(sorted(size_dist.items(), key=lambda x: x[1], reverse=True)[:10])}")

    print("\nSample of individual files:")
    print(sum_df.head(20).to_string())

if __name__ == "__main__":
    analyze_traces()
