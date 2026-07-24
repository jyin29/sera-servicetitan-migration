from inventory import Inventory
from logger import MigrationLogger
from stats import MigrationStats
from resume import ResumeTracker

from servicetitan.browser import connect
from servicetitan.job_search import JobSearcher
from servicetitan.customer_search import CustomerSearcher
from servicetitan.uploader import Uploader

from sera.downloader import SeraDownloader


class MigrationEngine:

    def __init__(self):

        self.logger = MigrationLogger()
        self.stats = MigrationStats()
        self.current_job = None
        self.current_customer = None

    def migrate_job(self, job):

        if not job.files:

            print("No files.")

            return

        self.stats.job()

        print()
        print("=" * 60)
        print(f"Job: {job.job_number}")
        print(f"Legacy ID: {job.legacy_id}")
        print(f"Files: {job.file_count}")

        #
        # Try opening the job first
        #
        if self.current_job != job.job_number:

            if self.job_search.open_job(job.job_number):
                self.current_job = job.job_number
            else:
                self.current_job = None

        if self.current_job == job.job_number:

            print("Uploading to job...")

            uploaded, skipped = self.uploader.upload_to_job(job.files)

            self.stats.uploaded_files(len(uploaded))
            self.stats.skipped_files(len(skipped))

            for file in uploaded:
                self.logger.log(
                    job.legacy_id,
                    job.job_number,
                    file.name,
                    "SUCCESS",
                    "JOB"
                )

            for file in skipped:
                self.logger.log(
                    job.legacy_id,
                    job.job_number,
                    file.name,
                    "SKIPPED",
                    "JOB",
                    "Already exists"
                )

            return

        #
        # Job not found -> try customer
        #
        print("Job not found.")

        if self.current_customer != job.legacy_id:

            if self.customer_search.open_customer(job.legacy_id):
                self.current_customer = job.legacy_id
            else:
                self.current_customer = None

        if self.current_customer == job.legacy_id:

            print("Uploading to customer...")

            uploaded, skipped = self.uploader.upload_to_customer(job.files)

            self.stats.uploaded_files(len(uploaded))
            self.stats.skipped_files(len(skipped))

            for file in uploaded:
                self.logger.log(
                    job.legacy_id,
                    job.job_number,
                    file.name,
                    "SUCCESS",
                    "CUSTOMER",
                    "Job not found"
                )

            for file in skipped:
                self.logger.log(
                    job.legacy_id,
                    job.job_number,
                    file.name,
                    "SKIPPED",
                    "CUSTOMER",
                    "Already exists"
                )

            return

        #
        # Neither job nor customer found
        #
        print("FAILED")

        self.stats.failed_files(len(job.files))

        for file in job.files:
            self.logger.log(
                job.legacy_id,
                job.job_number,
                file.name,
                "FAILED",
                "",
                "Customer not found"
            )

    def run(self, limit = 0):

        print("Building inventory...")

        inventory = Inventory()
        jobs = inventory.build("sera_media")

        total_jobs = len(jobs)
        completed_jobs = 0

        tracker = ResumeTracker()

        last_job = tracker.load()

        resume = last_job is None

        print(f"Found {len(jobs)} jobs.")

        print("Connecting to Edge...")
        p, browser, context = connect()
        print("Connected.")

        try:

            page = context.pages[0]
            print("Got page.")

            self.job_search = JobSearcher(page)
            self.customer_search = CustomerSearcher(page)
            self.uploader = Uploader(page)

            #
            # TEST MODE
            # Change [:1] to [:] when ready
            #
            tracker = ResumeTracker()

            last_job = tracker.load()

            resume = last_job is None
            skip_current = last_job is not None

            try:

                if limit:

                    jobs = jobs[:limit]

                for job in jobs:

                    #
                    # Skip until we reach the last completed job
                    #
                    if not resume:

                        if job.job_number == last_job:
                            resume = True

                        continue

                    #
                    # Skip the job we already finished
                    #
                    if skip_current:

                        skip_current = False

                        continue


                    print()
                    print("=" * 70)
                    print(f"Job {completed_jobs + 1} of {total_jobs}")
                    print(f"Job Number : {job.job_number}")
                    print(f"Legacy ID  : {job.legacy_id}")
                    print(f"Files      : {len(job.files)}")
                    print("=" * 70)

                    self.migrate_job(job)

                    completed_jobs += 1

                    percent = completed_jobs / total_jobs * 100

                    print(
                        f"Progress: {completed_jobs}/{total_jobs} "
                        f"({percent:.1f}%)"
                    )

                    tracker.save(job.job_number)

            except KeyboardInterrupt:
            
                print("/nMigration interrupted.")

            self.stats.print_summary()

            print()
            print("=" * 70)
            print("Migration Complete")
            print(f"Jobs Processed: {completed_jobs}")
            print(f"Total Jobs    : {total_jobs}")
            print("=" * 70)

        finally:
            tracker.clear()
            browser.close()
            p.stop()