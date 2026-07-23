from playwright.sync_api import Page, TimeoutError


class CustomerSearcher:

    def __init__(self, page: Page):
        self.page = page

    def open_customer(self, legacy_id: str) -> bool:

        print(f"\nSearching for customer {legacy_id}...")

        search = self.page.locator(
            "input[placeholder*='Search']"
        )

        search.click()

        self.page.keyboard.press("Control+A")
        self.page.keyboard.press("Backspace")

        self.page.keyboard.type(
            str(legacy_id),
            delay=20
        )

        self.page.wait_for_timeout(1200)

        customers = self.page.locator(
            "a[data-fs-entity-type='Customer']"
        )

        count = customers.count()

        print(f"Found {count} customer results.")

        for i in range(count):

            customer = customers.nth(i)

            card = customer.locator("xpath=ancestor::div[contains(@class,'_grid')]")

            text = card.inner_text()

            if f"Legacy ID\n{legacy_id}" in text or legacy_id in text:

                print("Customer found.")

                customer.click()

                try:
                    self.page.wait_for_load_state(
                        "networkidle"
                    )
                except TimeoutError:
                    pass

                return True

        print("Customer not found.")

        return False