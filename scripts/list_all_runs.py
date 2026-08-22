import urllib.request
import json

headers = {'User-Agent': 'Mozilla/5.0'}
url = 'https://api.github.com/repos/pruthvirajravi/VTM_CTC/actions/runs'
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())

print("All workflow runs in repository:")
for r in data.get('workflow_runs', []):
    print(f"Run #{r.get('run_number')} | ID: {r['id']} | Head SHA: {r['head_sha'][:7]} | Status: {r['status']} | Conclusion: {r['conclusion']}")
