import urllib.request
import json

headers = {'User-Agent': 'Mozilla/5.0'}
url = 'https://api.github.com/repos/pruthvirajravi/VTM_CTC/actions/runs/32591485552/jobs'

req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as resp:
    jobs_data = json.loads(resp.read().decode())

jobs = jobs_data.get('jobs', [])
completed_jobs = [j for j in jobs if j['status'] == 'completed']

for j in completed_jobs[:5]:
    print(f"Completed Job: {j['name']} -> Conclusion: {j['conclusion']}")
    for s in j.get('steps', []):
        print(f"   Step: {s['name']} -> {s['conclusion']}")
