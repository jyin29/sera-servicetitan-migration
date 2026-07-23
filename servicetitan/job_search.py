from playwright.sync_api import Page


class JobSearcher:

    def __init__(self, page: Page):
        self.page = page

    def open_job(self, job_number: str):

        print(f"\nSearching for job {job_number}...")

        self.page.keyboard.press("Control+/")
        self.page.wait_for_timeout(500)

        self.page.keyboard.press("Control+A")
        self.page.keyboard.press("Backspace")

        self.page.keyboard.type(str(job_number), delay=30)

        self.page.wait_for_timeout(1500)

        # Click the job number directly
        self.page.get_by_text(f"Job #{job_number}", exact=False).click()

        # Give the SPA a moment to navigate
        self.page.wait_for_timeout(1500)

        print("Opened job.")