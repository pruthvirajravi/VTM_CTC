#!/usr/bin/env python3
"""
Python script to upload workflow artifacts (.tar.gz packages) to Google Drive.
Supports Service Account JSON authentication and falls back gracefully.
"""

import os
import sys

def upload_artifact_to_gdrive(tar_path, folder_id):
    if not os.path.exists(tar_path):
        print(f"Warning: File {tar_path} not found.")
        return

    key_json = os.environ.get("GDRIVE_CREDENTIALS")
    if not key_json:
        print("Notice: GDRIVE_CREDENTIALS secret not set. Skipping Drive API upload.")
        return

    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from google.oauth2 import service_account

        with open("sa_key.json", "w") as f:
            f.write(key_json)

        creds = service_account.Credentials.from_service_account_file("sa_key.json")
        service = build("drive", "v3", credentials=creds)

        filename = os.path.basename(tar_path)
        file_metadata = {
            "name": filename,
            "parents": [folder_id]
        }
        media = MediaFileUpload(tar_path, mimetype="application/gzip", resumable=True)
        file_obj = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        file_id = file_obj.get("id")
        print(f"Uploaded successfully to Google Drive: {filename} (ID: {file_id})")

    except Exception as e:
        print(f"Google Drive Upload Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: upload_to_gdrive.py <tar_file_path> <gdrive_folder_id>")
        sys.exit(0)

    tar_file = sys.argv[1]
    folder_id = sys.argv[2]
    upload_artifact_to_gdrive(tar_file, folder_id)
