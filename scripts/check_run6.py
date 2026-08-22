import urllib.request
import json
import sys

headers = {'User-Agent': 'Mozilla/5.0'}
url = 'https://api.github.com/repos/pruthvirajravi/VTM_CTC/actions/runs/32589408524/jobs'
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as resp:
    jobs_data = json.loads(resp.read().decode())

failed_jobs = [j for j in jobs_data.get('jobs', []) if j['conclusion'] == 'failure']
print(f"Run #6: Total jobs = {len(jobs_data.get('jobs', []))}, Failed = {len(failed_jobs)}")

for job in failed_jobs[:2]:
    print(f"\nJob: {job['name']} (ID: {job['id']})")
    for step in job.get('steps', []):
        print(f"  Step: {step['name']} -> {step['conclusion']}")
