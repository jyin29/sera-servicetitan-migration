from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MigrationJob:

    legacy_id: str
    job_number: str
    files: list[Path] = field(default_factory=list)

    @property
    def file_count(self):
        return len(self.files)