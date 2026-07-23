from playwright.sync_api import Page, TimeoutError


class CustomerSearcher:

    def __init__(self, page: Page):
        self.page = page

    def open_customer(self, legacy_id: str) -> bool:

        print(f"\nSearching for customer {legacy_id}...")

        self.page.keyboard.press("Control+/")

        search = self.page.locator(
            'input[data-fs-element="Global Search - Form | Basic Search Field"]'
        )

        search.wait_for(state="visible", timeout=10000)

        search.click()

        #
        # fill() clears automatically
        #
        search.fill(str(legacy_id))

        try:

            self.page.wait_for_function(
                """
                () => document.querySelectorAll(
                    'a[data-fs-entity-type="Customer"]'
                ).length > 0
                """,
                timeout=5000
            )

        except TimeoutError:

            print("No customer results.")

            self.page.keyboard.press("Escape")

            return False

        customers = self.page.locator(
            'a[data-fs-entity-type="Customer"]'
        )

        print("Customer results:", customers.count())

        if customers.count() == 0:

            self.page.keyboard.press("Escape")

            return False

        customers.first.click()

        try:
            self.page.wait_for_url("**/customer/**", timeout=10000)
        except TimeoutError:
            self.page.wait_for_timeout(1000)

        self.page.keyboard.press("Escape")

        return True