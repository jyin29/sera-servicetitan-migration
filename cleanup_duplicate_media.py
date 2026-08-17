from collections import defaultdict
from playwright.sync_api import sync_playwright

from servicetitan.browser import connect, wait_for_servicetitan
from servicetitan.customer_search import CustomerSearcher

CUSTOMER_IDS = ["845113"]
DRY_RUN = False
MAX_DELETIONS_PER_CUSTOMER = 100


def scan_media(page):
    cards = page.locator(".qa-attachment-item")
    groups = defaultdict(list)

    for i in range(cards.count()):
        card = cards.nth(i)
        title = card.locator(".qa-title")
        if title.count() == 0:
            continue

        name = title.first.inner_text().strip().lower()
        if not name:
            continue

        created = card.locator(".qa-created-on")
        created_on = created.first.inner_text().strip() if created.count() else ""
        groups[name].append({"title": name, "created_on": created_on})

    return {name: items for name, items in groups.items() if len(items) > 1}


def delete_one_duplicate(page, title):
    cards = page.locator(".qa-attachment-item")
    matches = []

    for i in range(cards.count()):
        card = cards.nth(i)
        heading = card.locator(".qa-title")
        if heading.count() and heading.first.inner_text().strip().lower() == title:
            matches.append(i)

    if len(matches) <= 1:
        return False

    card = cards.nth(matches[0])
    delete_button = card.locator("button.qa-file-delete")

    if delete_button.count() == 0:
        raise RuntimeError(f"Delete button missing for {title}")

    before = len(matches)
    dialog_seen = {"value": False}

    def handle_dialog(dialog):
        dialog_seen["value"] = True
        print(f"Browser confirmation: {dialog.message}")
        dialog.accept()

    # Register before interacting with the card so the native confirm() cannot be missed.
    page.once("dialog", handle_dialog)

    # The action bar is hidden until hover in ServiceTitan. Recreate a human-like
    # interaction so its delete handler is actually activated.
    card.hover()
    page.wait_for_timeout(300)

    delete_button.first.hover()
    page.wait_for_timeout(200)

    delete_button.first.click(force=True)
    page.wait_for_timeout(1000)

    if not dialog_seen["value"]:
        raise RuntimeError(
            f"Clicked delete for '{title}', but ServiceTitan did not open "
            "the browser confirmation dialog"
        )

    # Wait for the media grid to rerender and verify exactly one copy disappeared.
    for _ in range(20):
        page.wait_for_timeout(500)
        now = 0
        current_cards = page.locator(".qa-attachment-item")

        for i in range(current_cards.count()):
            heading = current_cards.nth(i).locator(".qa-title")
            if heading.count() and heading.first.inner_text().strip().lower() == title:
                now += 1

        if now == before - 1:
            return True

    raise RuntimeError(f"Delete did not reduce '{title}' from {before} copies")


def clean_customer(page, customer_id):
    deleted = 0

    while True:
        duplicate_groups = scan_media(page)

        if not duplicate_groups:
            print(f"Customer {customer_id}: media clean")
            return deleted

        title = next(iter(duplicate_groups))
        copies = len(duplicate_groups[title])
        print(f"Customer {customer_id}: {title} has {copies} copies")

        if DRY_RUN:
            for other, items in duplicate_groups.items():
                print(f"  {other}: {len(items)} copies -> would keep 1")
            return sum(len(items) - 1 for items in duplicate_groups.values())

        if deleted >= MAX_DELETIONS_PER_CUSTOMER:
            raise RuntimeError("Per-customer media deletion safety limit reached")

        if not delete_one_duplicate(page, title):
            raise RuntimeError(f"Could not delete duplicate {title}")

        deleted += 1
        print(f"Deleted {deleted} duplicate media item(s) for customer {customer_id}")


def open_customer_with_retry(page, customer_id, attempts=3):
    for attempt in range(1, attempts + 1):
        print(f"Searching for customer {customer_id} ({attempt}/{attempts})...")

        try:
            if CustomerSearcher(page).open_customer(customer_id):
                page.wait_for_timeout(1500)
                return True
        except Exception as exc:
            print(f"Search attempt failed: {exc}")

        page.wait_for_timeout(2000)

    return False


with sync_playwright() as p:
    browser, context = connect(p)
    page = wait_for_servicetitan(context)
    page.bring_to_front()

    total_deleted = 0
    failures = []

    for customer_id in CUSTOMER_IDS:
        print("=" * 80)
        print(f"MEDIA CLEANUP: {customer_id}")
        print("=" * 80)

        if not open_customer_with_retry(page, customer_id):
            failures.append((customer_id, "customer not found"))
            continue

        try:
            total_deleted += clean_customer(page, customer_id)
        except Exception as exc:
            print(f"FAILED {customer_id}: {exc}")
            failures.append((customer_id, str(exc)))

    print("=" * 80)
    print("MEDIA CLEANUP COMPLETE")
    print(f"Deleted: {total_deleted}")
    print(f"Failures: {len(failures)}")

    for customer_id, reason in failures:
        print(f"- {customer_id}: {reason}")

    print("=" * 80)
    input("Press Enter to exit...")
