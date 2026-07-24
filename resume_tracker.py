from pathlib import Path
from datetime import datetime

class ResumeTracker:

    FILE = Path("resume_customer.txt")

    def load(self):

        if not self.FILE.exists():
            return None

        data = self.FILE.read_text().strip()

        customer_id = data.split("|")[0]

        return customer_id

    def save(self, customer_id):

        timestamp = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        self.FILE.write_text(
            f"{customer_id}|{timestamp}"
        )

    def clear(self):

        if self.FILE.exists():
            self.FILE.unlink()