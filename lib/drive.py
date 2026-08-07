"""
lib/drive.py — Upload screenshots to Google Drive.

Folder structure:
  GOOGLE_DRIVE_FOLDER_ID (root)
  └── "2026 August" (auto-created monthly subfolder)
      ├── wave_G9A001_1234567890.jpg
      └── nug_G9A001_1234567891.jpg
"""
import io
from datetime import datetime, timezone
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
from lib import config

_SCOPES = ["https://www.googleapis.com/auth/drive.file"]
_drive_service = None

# Cache: "2026 August" → folder_id
_monthly_folder_cache: dict[str, str] = {}


def _get_service():
    global _drive_service
    if _drive_service is None:
        creds = service_account.Credentials.from_service_account_info(
            config.SERVICE_ACCOUNT_INFO, scopes=_SCOPES
        )
        _drive_service = build("drive", "v3", credentials=creds, cache_discovery=False)
    return _drive_service


def _get_monthly_folder_name(dt: datetime | None = None) -> str:
    """Returns e.g. '2026 August'"""
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt.strftime("%Y %B")  # e.g. "2026 August"


def _get_or_create_monthly_folder(folder_name: str) -> str:
    """
    Finds or creates a subfolder named folder_name inside GOOGLE_DRIVE_FOLDER_ID.
    Returns the subfolder's Drive file ID.
    """
    if folder_name in _monthly_folder_cache:
        return _monthly_folder_cache[folder_name]

    service = _get_service()
    parent_id = config.GOOGLE_DRIVE_FOLDER_ID

    # Search for existing folder
    query = (
        f"name='{folder_name}' and "
        f"'{parent_id}' in parents and "
        f"mimeType='application/vnd.google-apps.folder' and "
        f"trashed=false"
    )
    results = service.files().list(
        q=query, fields="files(id, name)"
    ).execute()
    files = results.get("files", [])

    if files:
        folder_id = files[0]["id"]
    else:
        # Create it
        metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id],
        }
        folder = service.files().create(body=metadata, fields="id").execute()
        folder_id = folder["id"]
        print(f"[drive] Created monthly folder: {folder_name} ({folder_id})")

    _monthly_folder_cache[folder_name] = folder_id
    return folder_id


def upload_screenshot(
    image_bytes: bytes,
    filename: str,
) -> str:
    """
    Upload image_bytes to the correct monthly subfolder in Google Drive.

    Args:
        image_bytes: Raw image bytes (JPEG/PNG)
        filename:    e.g. "wave_G9A001_1691234567.jpg"

    Returns:
        Shareable view URL or empty string on failure.
    """
    try:
        service = _get_service()
        folder_name = _get_monthly_folder_name()
        folder_id = _get_or_create_monthly_folder(folder_name)

        file_metadata = {
            "name": filename,
            "parents": [folder_id],
        }
        media = MediaIoBaseUpload(
            io.BytesIO(image_bytes),
            mimetype="image/jpeg",
            resumable=False,
        )
        uploaded = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id",
        ).execute()
        file_id = uploaded.get("id")

        # Make publicly viewable
        service.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
        ).execute()

        return f"https://drive.google.com/file/d/{file_id}/view"

    except Exception as e:
        print(f"[drive] Upload failed: {e}")
        return ""
