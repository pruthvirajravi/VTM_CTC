import urllib.request
import json
import zipfile
import io

headers = {'User-Agent': 'Mozilla/5.0'}
# Get jobs
url = 'https://api.github.com/repos/pruthvirajravi/VTM_CTC/actions/runs/32588541480/jobs'
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as resp:
    jobs_data = json.loads(resp.read().decode())

failed_jobs = [j for j in jobs_data.get('jobs', []) if j['conclusion'] == 'failure']
if failed_jobs:
    job = failed_jobs[0]
    job_id = job['id']
    print(f"Fetching logs for job {job['name']} (ID: {job_id})")
    log_url = f"https://api.github.com/repos/pruthvirajravi/VTM_CTC/actions/jobs/{job_id}/logs"
    try:
        req_log = urllib.request.Request(log_url, headers=headers)
        with urllib.request.urlopen(req_log) as resp_log:
            log_text = resp_log.read().decode('utf-8', errors='ignore')
            lines = log_text.split('\n')
            print(f"Total log lines: {len(lines)}")
            print("--- Last 40 lines of log ---")
            for line in lines[-40:]:
                print(line)
    except Exception as e:
        print(f"Error fetching log: {e}")
