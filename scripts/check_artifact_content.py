import urllib.request
import json
import zipfile
import io
import tarfile
import os

headers = {'User-Agent': 'Mozilla/5.0'}
url = 'https://api.github.com/repos/pruthvirajravi/VTM_CTC/actions/runs/32612648362/artifacts'

req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())

artifacts = data.get('artifacts', [])
print(f"Total artifacts: {len(artifacts)}")

# Find BQMall_RA or Johnny_RA or FourPeople_AI
target = None
for a in artifacts:
    if "BQMall_RA" in a['name'] or "FourPeople_AI" in a['name'] or "Johnny_RA" in a['name']:
        target = a
        break

if target:
    print(f"Target artifact: {target['name']} (ID: {target['id']}, size: {target['size_in_bytes']} bytes)")
    print(f"Download URL: {target['archive_download_url']}")
