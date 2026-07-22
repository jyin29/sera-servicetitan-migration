from pathlib import Path

# Root folder of the project
ROOT = Path(__file__).resolve().parent.parent

# Database
DATABASE = ROOT / "database" / "migration.db"

# Project folders
LOG_FOLDER = ROOT / "logs"
MEDIA_FOLDER = ROOT / "sera_media"
MANIFEST_FOLDER = ROOT / "manifests"
BROWSER_PROFILE = ROOT / "browser_profile"

# Files
DOWNLOAD_LOG = LOG_FOLDER / "download_log.csv"
SETTINGS_FILE = ROOT / "settings.json"

# Create folders automatically
for folder in (
    LOG_FOLDER,
    MEDIA_FOLDER,
    MANIFEST_FOLDER,
    BROWSER_PROFILE,
):
    folder.mkdir(parents=True, exist_ok=True)