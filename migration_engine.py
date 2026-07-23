from inventory import Inventory
from logger import MigrationLogger

from servicetitan.browser import connect
from servicetitan.job_search import JobSearcher
from servicetitan.customer_search import CustomerSearcher
from servicetitan.uploader import Uploader


class MigrationEngine:

    def __init__(self):
        self.logger = MigrationLogger()

    def migrate_job(self, job):

        print()
        print("=" * 60)
        print(f"Job: {job.job_number}")
        print(f"Legacy ID: {job.legacy_id}")
        print(f"Files: {job.file_count}")

        #
        # TEMPORARY: Force customer upload for testing.
        # Once customer upload works, we'll change this back.
        #

        print("Job not found.")

        if self.customer_search.open_customer(job.legacy_id):

            print("Uploading to customer...")

            self.uploader.upload_to_customer(job.files)

            for file in job.files:
                self.logger.log(
                    job.legacy_id,
                    job.job_number,
                    file.name,
                    "SUCCESS",
                    "CUSTOMER",
                    "Job not found"
                )

            return

        print("FAILED")

        for file in job.files:
            self.logger.log(
                job.legacy_id,
                job.job_number,
                file.name,
                "FAILED",
                "",
                "Customer not found"
            )

    def run(self):

        print("Building inventory...")

        inventory = Inventory()
        jobs = inventory.build("sera_media")

        print(f"Found {len(jobs)} jobs.")

        print("Connecting to Edge...")
        p, browser, context = connect()
        print("Connected.")

        try:

            print("Getting page...")
            page = context.pages[0]
            print("Got page.")

            self.job_search = JobSearcher(page)
            self.customer_search = CustomerSearcher(page)
            self.uploader = Uploader(page)

            #
            # ONLY PROCESS THE FIRST JOB FOR NOW
            #

            for job in jobs[:1]:

                self.migrate_job(job)

        finally:

            browser.close()
            p.stop()