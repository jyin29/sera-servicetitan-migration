from playwright.sync_api import Page


class JobSearcher:

    def __init__(self, page: Page):
        self.page = page

    def _reset_search(self):

        #
        # Close anything that might be open
        #
        for _ in range(3):

            self.page.keyboard.press("Escape")

            self.page.wait_for_timeout(200)

    def _search(self, job_number: str):

        self._reset_search()

        # Open Global Search
        self.page.keyboard.press("Control+/")
        self.page.wait_for_timeout(300)

        search = self.page.locator(
            'input[data-fs-element="Global Search - Form | Basic Search Field"]'
        )

        search.wait_for(state="visible", timeout=10000)

        search.click()

        # Clear previous search
        search.fill("")
        self.page.wait_for_timeout(200)

        # Type the new job number
        search.type(str(job_number), delay=25)

        # Give ServiceTitan time to populate results
        self.page.wait_for_timeout(1500)

    def open_job(self, job_number: str) -> bool:

        print(f"\nSearching for job {job_number}...")

        self._search(job_number)

        jobs = self.page.locator(
            'a[data-fs-entity-type="Job"]'
        )

        count = jobs.count()

        print(f"Job results: {count}")

        for i in range(count):

            text = jobs.nth(i).inner_text().strip()

            print("Candidate:", text)

            if text.startswith(f"Job #{job_number}"):

                jobs.nth(i).click()

                try:
                    self.page.wait_for_url(
                        "**/Job/**",
                        timeout=10000
                    )
                except:
                    self.page.wait_for_timeout(1500)

                self.page.keyboard.press("Escape")

                self._reset_search()

                return True

        self.page.keyboard.press("Escape")

        print("Exact job not found.")

        return False