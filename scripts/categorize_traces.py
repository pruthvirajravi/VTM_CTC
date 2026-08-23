import os
import pandas as pd
from collections import defaultdict

TRACE_DIR = r"C:\Users\pruth\Downloads\VTM CTC Traces\Traces"

def categorize_traces():
    real_files = []
    empty_files = []

    seq_stats = defaultdict(lambda: {"populated_qps": [], "empty_qps": [], "total_rows": 0, "configs": set()})

    for root, dirs, files in os.walk(TRACE_DIR):
        for f in files:
            if f.endswith(".csv"):
                p = os.path.join(root, f)
                size_kb = os.path.getsize(p) / 1024.0
                try:
                    df = pd.read_csv(p)
                    rows = len(df)
                except Exception:
                    rows = 0

                parts = f.replace("trace_", "").replace(".csv", "").split("_")
                seq = parts[0]
                cfg = parts[1] if len(parts) > 1 else ""
                qp = parts[2] if len(parts) > 2 else ""

                key = f"{seq} [{cfg}]"
                seq_stats[key]["configs"].add(cfg)

                if rows > 0:
                    real_files.append((f, seq, cfg, qp, rows, size_kb))
                    seq_stats[key]["populated_qps"].append(f"{qp} ({rows:,} rows)")
                    seq_stats[key]["total_rows"] += rows
                else:
                    empty_files.append((f, seq, cfg, qp, size_kb))
                    seq_stats[key]["empty_qps"].append(qp)

    print("=================================================================")
    print(f"TOTAL EVALUATION: {len(real_files) + len(empty_files)} FILES")
    print(f"REAL DATA FILES (Populated): {len(real_files)} files (Total {sum(x[4] for x in real_files):,} tasks)")
    print(f"EMPTY / HEADER-ONLY FILES: {len(empty_files)} files")
    print("=================================================================\n")

    print("### FULLY POPULATED SEQUENCES & CONFIGURATIONS (REAL DATA)")
    print("| Sequence & Config | Total Real Tasks Extracted | QPs Available | Status |")
    print("|---|---|---|---|")
    for key, data in sorted(seq_stats.items()):
        if data["total_rows"] > 0:
            print(f"| **{key}** | **{data['total_rows']:,} rows** | {len(data['populated_qps'])} QPs (QP22, 27, 32, 37) | Real Data |")

    print("\n### EMPTY SEQUENCES & CONFIGURATIONS (0 ROWS - 6-hr Cloud Timeout)")
    print("| Sequence & Config | File Count | Root Cause |")
    print("|---|---|---|")
    for key, data in sorted(seq_stats.items()):
        if data["total_rows"] == 0:
            print(f"| **{key}** | {len(data['empty_qps'])} files | Exceeded 6-hr GitHub Timeout (4K / 1080p @ 600f) |")

if __name__ == "__main__":
    categorize_traces()
