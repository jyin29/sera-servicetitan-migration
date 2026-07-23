from playwright.sync_api import Page


class JobSearcher:

    def __init__(self, page: Page):
        self.page = page

    def open_job(self, job_number: str) -> bool:

        print(f"\nSearching for job {job_number}...")

        self.page.keyboard.press("Control+/")
        self.page.wait_for_timeout(500)

        self.page.keyboard.press("Control+A")
        self.page.keyboard.press("Backspace")

        self.page.keyboard.type(str(job_number), delay=25)

        self.page.wait_for_timeout(1500)

        jobs = self.page.locator(
            'a[data-fs-entity-type="Job"]'
        )

        print(f"Job results: {jobs.count()}")

        for i in range(jobs.count()):

            job = jobs.nth(i)

            text = job.inner_text()

            print("Candidate:", text)

            if f"Job #{job_number}" in text:

                print("Exact match found.")

                job.click()

                self.page.wait_for_timeout(1500)

                return True

        print("Exact job not found.")

        return False