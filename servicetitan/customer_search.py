from playwright.sync_api import Page


class CustomerSearcher:

    def __init__(self, page: Page):
        self.page = page

    def open_customer(self, legacy_id: str):

        print(f"\nSearching for customer {legacy_id}...")

        # Open Global Search
        self.page.keyboard.press("Control+/")
        self.page.wait_for_timeout(600)

        # Search box receives focus automatically
        self.page.keyboard.press("Control+A")
        self.page.keyboard.press("Backspace")

        self.page.keyboard.type(str(legacy_id), delay=30)

        self.page.wait_for_timeout(1500)

        customers = self.page.locator(
            'a[data-fs-entity-type="Customer"]'
        )

        print("Customer results:", customers.count())

        if customers.count() == 0:
            raise Exception("Customer not found.")
            return False

        customers.first.click()

        try:
            self.page.wait_for_url("**/customer/**", timeout=10000)
        except:
            self.page.wait_for_timeout(1500)

        print("Customer opened.")

        return True