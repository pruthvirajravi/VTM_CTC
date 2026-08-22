import urllib.request
import json
import sys

headers = {'User-Agent': 'Mozilla/5.0'}
url = 'https://api.github.com/repos/pruthvirajravi/VTM_CTC/actions/runs'

try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
    
    runs = data.get('workflow_runs', [])
    if not runs:
        print("No workflow runs found.")
        sys.exit(0)
    
    latest_run = runs[0]
    print(f"Latest Run ID: {latest_run['id']}")
    print(f"Title: {latest_run['name']}")
    print(f"Status: {latest_run['status']}")
    print(f"Conclusion: {latest_run['conclusion']}")
    print(f"URL: {latest_run['html_url']}")
    
    # Fetch jobs for latest run
    jobs_url = latest_run['jobs_url']
    req_jobs = urllib.request.Request(jobs_url, headers=headers)
    with urllib.request.urlopen(req_jobs) as resp_jobs:
        jobs_data = json.loads(resp_jobs.read().decode())
    
    for job in jobs_data.get('jobs', [])[:5]:
        print(f"\n--- Job: {job['name']} ({job['status']}, {job['conclusion']}) ---")
        for step in job.get('steps', []):
            print(f"  Step: {step['name']} -> {step['status']} ({step['conclusion']})")

except Exception as e:
    print(f"Error fetching runs: {e}")
