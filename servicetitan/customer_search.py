from playwright.sync_api import Page


class CustomerSearcher:

    def __init__(self, page: Page):
        self.page = page

    def _check_session(self):
        url = self.page.url.lower()
        if "login" in url:
            raise Exception("ServiceTitan session expired. Please log back in.")

    def _reset_search(self):
        for _ in range(3):
            self.page.keyboard.press("Escape")
            self.page.wait_for_timeout(200)

    def _search(self, value: str):
        self._check_session()
        self._reset_search()
        self.page.keyboard.press("Control+/")
        self.page.wait_for_timeout(300)

        search = self.page.locator(
            'input[data-fs-element="Global Search - Form | Basic Search Field"]'
        )
        search.wait_for(state="visible", timeout=10000)
        search.click()
        search.focus()
        self.page.wait_for_timeout(100)
        search.fill("")
        self.page.wait_for_timeout(200)
        search.type(str(value), delay=25)
        self.page.wait_for_timeout(1500)

    def _open_result(self, result):
        result.click()
        try:
            self.page.wait_for_url("**/customer/**", timeout=10000)
        except Exception:
            self.page.wait_for_timeout(1500)
        self.page.keyboard.press("Escape")
        self._reset_search()
        return True

    def open_customer(self, legacy_id: str) -> bool:
        print(f"\nSearching for customer {legacy_id}...")
        self._search(legacy_id)
        customers = self.page.locator('a[data-fs-entity-type="Customer"]')
        count = customers.count()
        print(f"Customer results: {count}")

        if count > 0:
            return self._open_result(customers.first)

        self.page.keyboard.press("Escape")
        print("Customer not found.")
        return False

    def open_customer_by_name(self, customer_name: str) -> bool:
        """Name fallback used only when the legacy-ID search finds nothing.

        For safety, automatically open a result only when exactly one customer
        search result contains the complete requested name. Ambiguous matches
        are left unresolved instead of risking a note on the wrong customer.
        """
        wanted = " ".join(str(customer_name).lower().split())
        print(f"\nLegacy ID lookup failed. Searching customer by name: {customer_name}...")
        self._search(customer_name)

        customers = self.page.locator('a[data-fs-entity-type="Customer"]')
        count = customers.count()
        print(f"Name-search customer results: {count}")

        exact = []
        for i in range(count):
            result = customers.nth(i)
            try:
                text = " ".join(result.inner_text().lower().split())
                print(f"Candidate customer: {result.inner_text().strip()}")
                if wanted and wanted in text:
                    exact.append(result)
            except Exception:
                pass

        if len(exact) == 1:
            print("Unique matching customer name found.")
            return self._open_result(exact[0])

        self.page.keyboard.press("Escape")
        if not exact:
            print("No matching customer name found.")
        else:
            print(f"Name search is ambiguous ({len(exact)} matching customers); not choosing automatically.")
        return False
