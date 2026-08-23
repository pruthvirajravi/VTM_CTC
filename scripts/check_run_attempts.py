import urllib.request
import json

headers = {'User-Agent': 'Mozilla/5.0'}
url = 'https://api.github.com/repos/pruthvirajravi/VTM_CTC/actions/runs/32612648362'
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as resp:
    run_data = json.loads(resp.read().decode())

print(f"Run ID: {run_data['id']}")
print(f"Run attempt: {run_data.get('run_attempt')}")

# Get all artifacts across the run
url_art = 'https://api.github.com/repos/pruthvirajravi/VTM_CTC/actions/runs/32612648362/artifacts?per_page=100'
req_art = urllib.request.Request(url_art, headers=headers)
with urllib.request.urlopen(req_art) as resp:
    art_data = json.loads(resp.read().decode())

artifacts = art_data.get('artifacts', [])
print(f"Total artifacts across run: {len(artifacts)}")
for i, a in enumerate(artifacts):
    print(f"{i+1:2d}. {a['name']:<30} ({a['size_in_bytes']} bytes)")
