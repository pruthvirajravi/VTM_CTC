import urllib.request
import json
import zipfile
import io
import os
import tarfile

headers = {'User-Agent': 'Mozilla/5.0'}
url = 'https://api.github.com/repos/pruthvirajravi/VTM_CTC/actions/artifacts'

req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())

artifacts = data.get('artifacts', [])
print(f"Total Artifacts available: {len(artifacts)}")
for a in artifacts[:10]:
    print(f"Artifact: {a['name']} | Size: {a['size_in_bytes']} bytes | Created: {a['created_at']}")
