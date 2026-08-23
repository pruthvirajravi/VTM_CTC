import urllib.request
import json

headers = {'User-Agent': 'Mozilla/5.0'}
url = 'https://api.github.com/repos/pruthvirajravi/VTM_CTC/actions/runs/32657078873/jobs'

req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as resp:
    jobs_data = json.loads(resp.read().decode())

jobs = jobs_data.get('jobs', [])
print(f"Total jobs: {len(jobs)}")

for j in jobs[:5]:
    print(f"\nJob: {j['name']} ({j['status']}, {j['conclusion']})")
    for s in j.get('steps', []):
        print(f"  Step: {s['name']} -> {s['status']} ({s['conclusion']})")
