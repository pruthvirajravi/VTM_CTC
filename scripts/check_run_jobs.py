import urllib.request
import json
import sys

headers = {'User-Agent': 'Mozilla/5.0'}
url = 'https://api.github.com/repos/pruthvirajravi/VTM_CTC/actions/runs/32588433235/jobs'

req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as resp:
    jobs_data = json.loads(resp.read().decode())

print(f"Total jobs: {len(jobs_data.get('jobs', []))}")
for job in jobs_data.get('jobs', [])[:3]:
    print(f"\n==========================================")
    print(f"Job: {job['name']} | Conclusion: {job['conclusion']}")
    for step in job.get('steps', []):
        print(f"  Step: {step['name']} -> {step['conclusion']}")
