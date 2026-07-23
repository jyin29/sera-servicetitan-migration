from pathlib import Path

from models import MigrationJob


class Inventory:

    def __init__(self):
        self.jobs = []

    def build(self, root):

        root = Path(root)

        self.jobs.clear()

        for customer in root.glob("Customer_*"):

            legacy = customer.name.replace(
                "Customer_",
                ""
            )

            for job_folder in customer.glob("Job_*"):

                job_number = job_folder.name.replace(
                    "Job_",
                    ""
                )

                job = MigrationJob(
                    legacy_id=legacy,
                    job_number=job_number
                )

                for file in job_folder.iterdir():

                    if file.is_file():

                        job.files.append(file)

                if job.files:
                    self.jobs.append(job)

        return self.jobs