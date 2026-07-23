from playwright.sync_api import sync_playwright

from servicetitan.job_search import JobSearcher


with sync_playwright() as p:

    browser = p.chromium.launch_persistent_context(
        user_data_dir="playwright_profile",
        headless=False
    )

    page = browser.new_page()

    page.goto("https://go.servicetitan.com")

    input("Navigate to the ServiceTitan dashboard then press ENTER...")

    searcher = JobSearcher(page)

    searcher.open_job("1809291")

    input("Press ENTER to close")

    browser.close()