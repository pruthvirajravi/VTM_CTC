import os
import glob

target_dir = r"C:\Users\pruth\Downloads\ALL_HEAVY_VTM_TRACES_MASTER\ALL_HEAVY_VTM_TRACES_MASTER"
if not os.path.exists(target_dir):
    target_dir = r"C:\Users\pruth\Downloads\ALL_HEAVY_VTM_TRACES_MASTER"

print(f"Checking directory: {target_dir}")
if os.path.exists(target_dir):
    files = os.listdir(target_dir)
    print(f"Total files in folder: {len(files)}")
    logs = [f for f in files if f.startswith("enc_") and f.endswith(".log")]
    print(f"Logs found: {len(logs)}")
    for log_name in logs[:3]:
        p = os.path.join(target_dir, log_name)
        print(f"\n=======================================================")
        print(f"LOG: {log_name} (Size: {os.path.getsize(p)} bytes)")
        print(f"=======================================================")
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            print(f.read())
else:
    print("Directory does not exist.")
