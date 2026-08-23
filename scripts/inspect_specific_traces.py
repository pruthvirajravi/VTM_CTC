import os
import pandas as pd

TRACE_DIR = r"C:\Users\pruth\Downloads\VTM CTC Traces\Traces"

def inspect_file_sizes():
    files = []
    for root, dirs, fnames in os.walk(TRACE_DIR):
        for f in fnames:
            if f.endswith(".csv"):
                p = os.path.join(root, f)
                size_kb = os.path.getsize(p) / 1024.0
                files.append((f, p, size_kb))

    files.sort(key=lambda x: x[2])
    print(f"Total CSV files found: {len(files)}\n")

    print("=== CATEGORY 1: FILES WITH 0 ROWS (~0.15 - 1.5 KB) ===")
    zero_row_files = [x for x in files if x[2] < 2.0]
    print(f"Count of empty/header-only files: {len(zero_row_files)} / {len(files)}")
    print(f"Examples: {[x[0] for x in zero_row_files[:6]]}")
    print("Why? 4K UHD (Tango2, Campfire) & 1080p (MarketPlace, RitualDance) timed out after 6 hours on 2-core runners.\n")

    print("=== CATEGORY 2: MEDIUM FILES (~100 - 200 KB) ===")
    med_files = [x for x in files if 100 <= x[2] <= 200]
    print(f"Count of medium files: {len(med_files)}")
    for fname, path, sz in med_files[:4]:
        df = pd.read_csv(path)
        print(f"-> {fname} ({sz:.1f} KB): {len(df):,} Real Transform Tasks (POCs: {df['poc'].nunique()}, Tasks {df['task_id'].min()} to {df['task_id'].max()})")
        print(f"   First task sample: POC {df.iloc[0]['poc']}, Size {df.iloc[0]['tu_w']}x{df.iloc[0]['tu_h']} ({df.iloc[0]['comp']}), Type {df.iloc[0]['tr_type_hor']}/{df.iloc[0]['tr_type_ver']}")

    print("\n=== CATEGORY 3: LARGE FILES (> 300 KB) ===")
    large_files = [x for x in files if x[2] > 300]
    print(f"Count of large files: {len(large_files)}")
    for fname, path, sz in large_files[:4]:
        df = pd.read_csv(path)
        print(f"-> {fname} ({sz:.1f} KB): {len(df):,} Real Transform Tasks (POCs: {df['poc'].nunique()})")

if __name__ == "__main__":
    inspect_file_sizes()
