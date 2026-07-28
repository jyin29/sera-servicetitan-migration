from playwright.sync_api import Page


class CustomerSearcher:

    def __init__(self, page: Page):
        self.page = page

    def _check_session(self):

        url = self.page.url.lower()

        if "login" in url:

            raise Exception(
                "ServiceTitan session expired. Please log back in."
            )

    def _reset_search(self):

        #
        # Close anything that might be open
        #
        for _ in range(3):

            self.page.keyboard.press("Escape")

            self.page.wait_for_timeout(200)

    def _search(self, legacy_id: str):

        self._check_session()

        self._reset_search()

        # Open Global Search
        self.page.keyboard.press("Control+/")
        self.page.wait_for_timeout(300)

        search = self.page.locator(
            'input[data-fs-element="Global Search - Form | Basic Search Field"]'
        )

        search.wait_for(state="visible", timeout=10000)

        search.click()

        search.focus()

        self.page.wait_for_timeout(100)

        # Clear previous search
        search.fill("")
        self.page.wait_for_timeout(200)

        # Type the legacy ID
        search.type(str(legacy_id), delay=25)

        # Give ServiceTitan time to populate results
        self.page.wait_for_timeout(1500)

    def open_customer(self, legacy_id: str) -> bool:

        print(f"\nSearching for customer {legacy_id}...")

        self._search(legacy_id)

        customers = self.page.locator(
            'a[data-fs-entity-type="Customer"]'
        )

        count = customers.count()

        print(f"Customer results: {count}")

        if count > 0:

            customers.first.click()

            try:
                self.page.wait_for_url(
                    "**/customer/**",
                    timeout=10000
                )
            except:
                self.page.wait_for_timeout(1500)

            self.page.keyboard.press("Escape")

            self._reset_search()

            return True

        self.page.keyboard.press("Escape")

        print("Customer not found.")

        return False