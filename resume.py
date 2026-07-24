from pathlib import Path


class ResumeTracker:

    def __init__(self):
        self.file = Path("resume.txt")

    def load(self):

        if not self.file.exists():
            return None

        return self.file.read_text().strip()

    def save(self, job_number):

        self.file.write_text(str(job_number))

    def clear(self):

        if self.file.exists():
            self.file.unlink()