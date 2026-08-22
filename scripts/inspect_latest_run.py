import urllib.request
import json
import sys

headers = {'User-Agent': 'Mozilla/5.0'}
url = 'https://api.github.com/repos/pruthvirajravi/VTM_CTC/actions/runs'
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())

runs = data.get('workflow_runs', [])
for r in runs[:3]:
    print(f"Run #{r.get('run_number')} (ID: {r['id']}) | SHA: {r['head_sha'][:7]} | Status: {r['status']} | Conclusion: {r['conclusion']}")

latest_run = runs[0]
jobs_url = latest_run['jobs_url']
req_jobs = urllib.request.Request(jobs_url, headers=headers)
with urllib.request.urlopen(req_jobs) as resp_jobs:
    jobs_data = json.loads(resp_jobs.read().decode())

for job in jobs_data.get('jobs', [])[:3]:
    print(f"\nJob: {job['name']} ({job['status']}, {job['conclusion']})")
    for step in job.get('steps', []):
        print(f"  Step: {step['name']} -> {step['status']} ({step['conclusion']})")
