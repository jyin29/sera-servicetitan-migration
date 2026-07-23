import csv
from pathlib import Path


class MigrationLogger:

    def __init__(self):

        self.path = Path("migration_log.csv")

        if not self.path.exists():

            with open(
                self.path,
                "w",
                newline="",
                encoding="utf-8"
            ) as f:

                writer = csv.writer(f)

                writer.writerow([
                    "Legacy ID",
                    "Job Number",
                    "File",
                    "Status",
                    "Destination",
                    "Reason"
                ])

    def log(
        self,
        legacy_id,
        job_number,
        file_name,
        status,
        destination,
        reason=""
    ):

        with open(
            self.path,
            "a",
            newline="",
            encoding="utf-8"
        ) as f:

            csv.writer(f).writerow([
                legacy_id,
                job_number,
                file_name,
                status,
                destination,
                reason
            ])