from playwright.sync_api import Page, TimeoutError


class JobSearcher:

    def __init__(self, page: Page):
        self.page = page

    def open_job(self, job_number: str) -> bool:

        print(f"\nSearching for job {job_number}...")

        #
        # Open global search
        #
        self.page.keyboard.press("Control+/")

        #
        # Wait for the search box
        #
        search = self.page.locator(
            'input[data-fs-element="Global Search - Form | Basic Search Field"]'
        )

        search.wait_for(state="visible", timeout=10000)

        #
        # Search
        #
        search.click()
        search.fill(str(job_number))

        #
        # Wait for results
        #
        try:

            self.page.wait_for_function(
                """
                () => document.querySelectorAll(
                    'a[data-fs-entity-type="Job"]'
                ).length > 0
                """,
                timeout=5000
            )

        except TimeoutError:

            print("No job results.")

            self.page.keyboard.press("Escape")

            return False

        jobs = self.page.locator(
            'a[data-fs-entity-type="Job"]'
        )

        print(f"Job results: {jobs.count()}")

        for i in range(jobs.count()):

            job = jobs.nth(i)

            text = job.inner_text().strip()

            print("Candidate:", text)

            if text == f"Job #{job_number}":

                print("Exact match found.")

                job.click()

                try:
                    self.page.wait_for_url(
                        "**/Job/**",
                        timeout=10000
                    )
                except TimeoutError:
                    self.page.wait_for_timeout(1000)

                #
                # Close the search overlay if it's still open
                #
                self.page.keyboard.press("Escape")

                return True

        print("Exact job not found.")

        self.page.keyboard.press("Escape")

        return False