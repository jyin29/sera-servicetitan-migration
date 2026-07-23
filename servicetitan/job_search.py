from playwright.sync_api import Page, TimeoutError


class JobSearcher:

    def __init__(self, page: Page):
        self.page = page

    def open_job(self, job_number: str) -> bool:

        print(f"\nSearching for job {job_number}...")

        # Click the global search
        self.page.locator("input[placeholder*='Search']").click()

        # Clear anything already in the search box
        self.page.keyboard.press("Control+A")
        self.page.keyboard.press("Backspace")

        # Type the job number
        self.page.keyboard.type(str(job_number), delay=20)

        # Wait for search results
        self.page.wait_for_timeout(1200)

        # If there is a Jobs tab/filter, click it if it exists.
        jobs_filter = self.page.locator("text=Jobs")

        if jobs_filter.count() > 0:
            jobs_filter.first.click()
            self.page.wait_for_timeout(500)

        results = self.page.locator("[role='option'], .search-result")

        if results.count() == 0:
            print("No search results.")
            return False

        first = results.first

        text = first.inner_text()

        if str(job_number) not in text:
            print("First result isn't the requested job.")
            print(text)
            return False

        first.click()

        try:
            self.page.wait_for_load_state("networkidle")
        except TimeoutError:
            pass

        print("Opened job.")

        return True