from inventory import Inventory
from logger import MigrationLogger
from stats import MigrationStats
from resume import ResumeTracker
from progress import progress
from datetime import datetime, timedelta
from cancel import cancel

from servicetitan.browser import connect
from servicetitan.job_search import JobSearcher
from servicetitan.customer_search import CustomerSearcher
from servicetitan.uploader import Uploader

from sera.downloader import SeraDownloader

import time

class MigrationEngine:

    def __init__(self):

        self.logger = MigrationLogger()
        self.stats = MigrationStats()
        self.current_job = None
        self.current_customer = None
        self.uploaded = 0
        self.skipped = 0
        self.failed = 0

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
                self.current_customer = None
            else:
                self.current_job = None

        if self.current_job == job.job_number:

            print("Uploading to job...")

            uploaded, skipped, failed = self.uploader.upload_to_job(job.files)

            self.stats.uploaded_files(len(uploaded))
            self.stats.skipped_files(len(skipped))
            self.stats.failed_files(len(failed))

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

            for file in failed:

                self.stats.failed_files(1)

                self.logger.log(
                    job.legacy_id,
                    job.job_number,
                    file.name,
                    "FAILED",
                    "JOB",
                    "Upload failed"
                )

            return

        #
        # Job not found -> try customer
        #
        print("Job not found.")

        if self.current_customer != job.legacy_id:

            if self.customer_search.open_customer(job.legacy_id):
                self.current_customer = job.legacy_id
                self.current_job = None
                from progress import progress
            else:
                self.current_customer = None

        if self.current_customer == job.legacy_id:

            print("Uploading to customer...")

            uploaded, skipped, failed = self.uploader.upload_to_customer(job.files)

            self.stats.uploaded_files(len(uploaded))
            self.stats.skipped_files(len(skipped))
            self.stats.failed_files(len(failed))

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

            for file in failed:

                self.stats.failed_files(1)

                self.logger.log(
                    job.legacy_id,
                    job.job_number,
                    file.name,
                    "FAILED",
                    "CUSTOMER",
                    "Upload failed"
                )

            return

        #
        # Neither job nor customer found
        #
        print("FAILED")
        print("Moving files to failed_media...")

        self.stats.failed_files(len(job.files))

        for file in job.files:
            self.uploader.move_to_failed(
                file,
                "Customer Not Found"
            )
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

        start_time = time.time()

        tracker = ResumeTracker()

        last_job = tracker.load()

        resume = last_job is None

        print(f"Found {len(jobs)} jobs.")

        print("Connecting to Edge...")
        from playwright.sync_api import sync_playwright

        p = sync_playwright().start()

        browser, context = connect(p)

        print("=" * 70)
        print("CONNECTED TO EDGE")
        print("=" * 70)

        for i, ctx in enumerate(browser.contexts):

            print(f"\nContext {i}")

            for j, page in enumerate(ctx.pages):

                print(f"  Page {j}: {page.url}")

        print("Connected.")

        try:

            page = None

            print("\nSearching for ServiceTitan tab...")

            for st_page in context.pages:

                print("Found:", st_page.url)

                url = st_page.url.lower()

                if (
                    "servicetitan" in url
                    or
                    "st-app" in url
                ):

                    page = st_page

                    break

            if page is None:

                raise Exception(
                    "No ServiceTitan tab found.\n"
                    "Open ServiceTitan in the browser connected to port 9222."
                )

            print("Using:")
            print(page.url)

            page.bring_to_front()

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

                    if cancel.is_cancelled():

                        print()
                        print("=" * 70)
                        print("Migration cancelled by user.")
                        print("=" * 70)

                        break

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
                    print(f"Job Number: {job.job_number}")
                    print(f"Legacy ID: {job.legacy_id}")
                    print(f"Files: {len(job.files)}")
                    print("=" * 70)

                    try:

                        self.migrate_job(job)

                    except Exception as e:

                        print()
                        print("=" * 70)
                        print("UNEXPECTED JOB ERROR")
                        print("=" * 70)
                        print(f"Customer : {job.legacy_id}")
                        print(f"Job      : {job.job_number}")
                        print(f"Error    : {e}")

                        self.stats.failed_files(len(job.files))

                        for file in job.files:

                            self.uploader.move_to_failed(
                                file,
                                "Unexpected Error"
                            )

                            self.logger.log(
                                job.legacy_id,
                                job.job_number,
                                file.name,
                                "FAILED",
                                "",
                                f"Unexpected Error: {e}"
                            )

                        completed_jobs += 1

                        progress.progress(
                            completed_jobs,
                            total_jobs
                        )

                        continue

                    completed_jobs += 1

                    progress.progress(completed_jobs, total_jobs)

                    elapsed = time.time() - start_time

                    #progress.elapsed(
                    #    str(timedelta(seconds=int(elapsed)))
                    #)

                    average = elapsed / completed_jobs

                    remaining = total_jobs - completed_jobs

                    eta = datetime.now() + timedelta(
                        seconds=average * remaining
                    )

                    progress.eta(
                        eta.strftime("%I:%M %p")
                    )

                    progress.progress(completed_jobs, total_jobs)

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