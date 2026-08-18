from playwright.sync_api import Page
import re


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
        search = self.page.locator('input[data-fs-element="Global Search - Form | Basic Search Field"]')
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

    def _result_text(self, result):
        pieces = []
        for getter in (
            lambda: result.inner_text(),
            lambda: result.get_attribute("title"),
            lambda: result.get_attribute("aria-label"),
            lambda: result.get_attribute("href"),
        ):
            try:
                value = getter()
                if value:
                    pieces.append(" ".join(str(value).split()))
            except Exception:
                pass
        try:
            container = result.locator("xpath=ancestor::*[self::li or self::div][1]")
            if container.count():
                value = container.inner_text()
                if value:
                    pieces.append(" ".join(value.split()))
        except Exception:
            pass
        return " | ".join(dict.fromkeys(pieces))

    def _result_key(self, result, index):
        """Identify the actual customer behind a rendered search result.

        ServiceTitan can render the same customer more than once in Global Search.
        Two DOM rows for the same customer must count as ONE candidate, not as an
        ambiguous customer match.
        """
        try:
            href = (result.get_attribute("href") or "").strip()
            match = re.search(r"/#/customer/(\d+)|/customer/(\d+)", href)
            if match:
                return "customer:" + next(x for x in match.groups() if x)
            if href:
                return "href:" + href
        except Exception:
            pass
        return f"dom:{index}"

    def open_customer(self, legacy_id: str) -> bool:
        legacy_id = str(legacy_id).strip()
        print(f"\nSearching for customer {legacy_id}...")
        self._search(legacy_id)
        customers = self.page.locator('a[data-fs-entity-type="Customer"]')
        count = customers.count()
        print(f"Customer results: {count}")
        pattern = re.compile(rf"(?<!\d){re.escape(legacy_id)}(?!\d)")
        exact = {}
        for i in range(count):
            result = customers.nth(i)
            try:
                combined = self._result_text(result)
                print(f"Candidate customer: {combined}")
                if pattern.search(combined):
                    exact.setdefault(self._result_key(result, i), result)
            except Exception as exc:
                print(f"Could not inspect customer result {i}: {exc}")
        if len(exact) == 1:
            print(f"Exact Legacy ID {legacy_id} customer found.")
            return self._open_result(next(iter(exact.values())))
        self.page.keyboard.press("Escape")
        if not exact:
            print(f"No customer result explicitly matched Legacy ID {legacy_id}.")
        else:
            print(f"Ambiguous Legacy ID match: {len(exact)} distinct customers explicitly contain {legacy_id}; not choosing automatically.")
        return False

    def open_customer_by_name(self, customer_name: str) -> bool:
        wanted = " ".join(str(customer_name).casefold().split())
        print(f"\nLegacy ID lookup failed. Searching customer by name: {customer_name}...")
        self._search(customer_name)
        customers = self.page.locator('a[data-fs-entity-type="Customer"]')
        count = customers.count()
        print(f"Name-search customer results: {count}")

        exact = {}
        for i in range(count):
            result = customers.nth(i)
            try:
                combined = self._result_text(result)
                normalized = " ".join(combined.casefold().split())
                print(f"Candidate customer: {combined}")
                if wanted and wanted in normalized:
                    exact.setdefault(self._result_key(result, i), result)
            except Exception as exc:
                print(f"Could not inspect name-search result {i}: {exc}")

        if len(exact) == 1:
            print(f"Unique matching customer found after deduplicating repeated search rows: {customer_name}")
            return self._open_result(next(iter(exact.values())))

        self.page.keyboard.press("Escape")
        if not exact:
            print(f"No result actually contained customer name '{customer_name}'.")
        else:
            print(f"Name search is ambiguous ({len(exact)} DISTINCT customers contain '{customer_name}'); not choosing automatically.")
        return False
