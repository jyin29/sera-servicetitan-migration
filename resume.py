from pathlib import Path
from datetime import datetime
import os


class ResumeTracker:

    APP_DATA = Path(os.getenv("LOCALAPPDATA")) / "Sera ServiceTitan Migration"
    APP_DATA.mkdir(parents=True, exist_ok=True)

    FILE = APP_DATA / "resume.txt"

    def load(self):

        if not self.FILE.exists():
            return None

        return self.FILE.read_text().strip()

    def save(self, job_number):

        self.FILE.write_text(str(job_number))

    def clear(self):

        if self.FILE.exists():
            self.FILE.unlink()