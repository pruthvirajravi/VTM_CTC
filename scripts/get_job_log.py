import urllib.request
import json

headers = {'User-Agent': 'Mozilla/5.0'}
url = 'https://api.github.com/repos/pruthvirajravi/VTM_CTC/actions/jobs/97239806804/logs'

try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        log_content = resp.read().decode('utf-8', errors='ignore')
    print("--- LOG CONTENT FROM JOB 97239806804 ---")
    print(log_content[-2000:])
except Exception as e:
    print(f"Error fetching log: {e}")
