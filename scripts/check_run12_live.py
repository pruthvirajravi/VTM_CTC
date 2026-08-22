import urllib.request
import json
import time

headers = {'User-Agent': 'Mozilla/5.0'}
url = 'https://api.github.com/repos/pruthvirajravi/VTM_CTC/actions/runs/32591485552/jobs'

req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as resp:
    jobs_data = json.loads(resp.read().decode())

jobs = jobs_data.get('jobs', [])
running_jobs = [j for j in jobs if j['status'] == 'in_progress']
completed_jobs = [j for j in jobs if j['status'] == 'completed']
queued_jobs = [j for j in jobs if j['status'] == 'queued']

print(f"Run #12 Live Progress:")
print(f"  Total Jobs: {len(jobs)}")
print(f"  Running Jobs: {len(running_jobs)}")
print(f"  Completed Jobs: {len(completed_jobs)}")
print(f"  Queued Jobs: {len(queued_jobs)}")

for j in running_jobs[:5]:
    print(f"  - Active: {j['name']}")
