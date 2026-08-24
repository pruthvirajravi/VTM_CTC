import os
import urllib.request
import json
import re

FOLDER_ID = "1CtXEkjIkd5G1Z-9xQvJgT7ICCtQAETez"
url = f"https://drive.google.com/drive/folders/{FOLDER_ID}"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

req = urllib.request.Request(url, headers=headers)
try:
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
    
    # Search for filenames in html
    matches = re.findall(r'\["([a-zA-Z0-9_\-\.\+]+(\.yuv|\.tar\.gz|\.zip|\.7z|\.mp4|\.cfg))"', html)
    print("Files found in Google Drive HTML:")
    for m in set(matches):
        print(f" - {m[0]}")
except Exception as e:
    print(f"Error reading Drive folder: {e}")
