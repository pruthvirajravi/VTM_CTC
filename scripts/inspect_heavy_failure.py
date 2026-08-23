import urllib.request
import json

headers = {'User-Agent': 'Mozilla/5.0'}
url = 'https://api.github.com/repos/pruthvirajravi/VTM_CTC/actions/runs/32656705742/jobs'

req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as resp:
    jobs_data = json.loads(resp.read().decode())

jobs = jobs_data.get('jobs', [])
failed_jobs = [j for j in jobs if j['conclusion'] == 'failure']

print(f"Total jobs: {len(jobs)}, Failed jobs: {len(failed_jobs)}")

for j in failed_jobs[:3]:
    print(f"\nFailed Job: {j['name']} (ID: {j['id']})")
    for s in j.get('steps', []):
        print(f"  Step: {s['name']} -> {s['status']} ({s['conclusion']})")
