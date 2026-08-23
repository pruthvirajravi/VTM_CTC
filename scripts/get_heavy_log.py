import urllib.request
import json
import zipfile
import io
import tarfile

headers = {'User-Agent': 'Mozilla/5.0'}
url = 'https://api.github.com/repos/pruthvirajravi/VTM_CTC/actions/runs/32657078873/artifacts'

req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())

artifacts = data.get('artifacts', [])
print(f"Artifacts in run: {len(artifacts)}")

# Find an artifact with a log file
for a in artifacts:
    if "Tango2" in a['name'] or "Campfire" in a['name'] or "MarketPlace" in a['name']:
        print(f"Found: {a['name']} (ID: {a['id']}, size: {a['size_in_bytes']} bytes)")
