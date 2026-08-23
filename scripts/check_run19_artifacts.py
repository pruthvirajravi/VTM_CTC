import urllib.request
import json

headers = {'User-Agent': 'Mozilla/5.0'}
url = 'https://api.github.com/repos/pruthvirajravi/VTM_CTC/actions/runs/32612648362/artifacts'

req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())

artifacts = data.get('artifacts', [])
total_count = data.get('total_count', len(artifacts))
print(f"Total Artifacts in Run #19: {total_count}")
print(f"Retrieved in this page: {len(artifacts)}")

for i, a in enumerate(artifacts):
    print(f"{i+1:2d}. {a['name']:<30} | {a['size_in_bytes']:>8} bytes | ID: {a['id']}")
