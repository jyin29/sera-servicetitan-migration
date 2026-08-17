import csv
import os
from collections import defaultdict
from pathlib import Path

from playwright.sync_api import sync_playwright

from servicetitan.browser import connect, wait_for_servicetitan
from servicetitan.customer_search import CustomerSearcher

DRY_RUN = False
MAX_DELETIONS_PER_CUSTOMER = 100
APP_DATA = Path(os.getenv("LOCALAPPDATA")) / "Sera ServiceTitan Migration"
MIGRATION_LOG = APP_DATA / "migration_log.csv"


def normalize_title(filename):
    return Path(filename).stem.strip().lower()


def load_migration_targets():
    """Return only customer/title pairs that the migration log shows more than once.

    This is the safety guard: a repeated ServiceTitan title is not enough by itself.
    We only clean a title when migration_log.csv contains multiple successful/skipped
    migration records for that same Legacy ID + source filename.
    """
    if not MIGRATION_LOG.exists():
        raise FileNotFoundError(f"Migration log not found: {MIGRATION_LOG}")

    records = defaultdict(list)

    with MIGRATION_LOG.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        required = {"Legacy ID", "File", "Status"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise RuntimeError(f"Migration log is missing columns: {sorted(missing)}")

        for row in reader:
            status = (row.get("Status") or "").strip().upper()
            if status not in {"SUCCESS", "SKIPPED"}:
                continue

            customer_id = (row.get("Legacy ID") or "").strip()
            filename = (row.get("File") or "").strip()
            if not customer_id or not filename:
                continue

            title = normalize_title(filename)
            records[(customer_id, title)].append(row)

    targets = defaultdict(set)
    for (customer_id, title), rows in records.items():
        if len(rows) > 1:
            targets[customer_id].add(title)

    return {customer_id: titles for customer_id, titles in targets.items() if titles}


def count_title(page, title):
    cards = page.locator(".qa-attachment-item")
    count = 0
    for i in range(cards.count()):
        heading = cards.nth(i).locator(".qa-title")
        if heading.count() and heading.first.inner_text().strip().lower() == title:
            count += 1
    return count


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

    # ServiceTitan displayed the tested customer's media newest-first. Delete the
    # first/newest matching card and preserve the oldest matching copy at the end.
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

    page.once("dialog", handle_dialog)
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

    for _ in range(20):
        page.wait_for_timeout(500)
        now = count_title(page, title)
        if now == before - 1:
            return True

    raise RuntimeError(f"Delete did not reduce '{title}' from {before} copies")


def clean_customer(page, customer_id, allowed_titles):
    deleted = 0

    for title in sorted(allowed_titles):
        copies = count_title(page, title)

        if copies <= 1:
            print(f"Customer {customer_id}: {title} already has {copies} copy")
            continue

        print(f"Customer {customer_id}: {title} has {copies} copies; migration log confirms repeats")

        if DRY_RUN:
            print(f"DRY RUN: would remove {copies - 1} copy/copies of {title}")
            deleted += copies - 1
            continue

        while copies > 1:
            if deleted >= MAX_DELETIONS_PER_CUSTOMER:
                raise RuntimeError("Per-customer media deletion safety limit reached")

            if not delete_one_duplicate(page, title):
                raise RuntimeError(f"Could not delete duplicate {title}")

            deleted += 1
            copies = count_title(page, title)
            print(f"Deleted {deleted} duplicate media item(s) for customer {customer_id}; {title} now has {copies}")

    return deleted


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


def main():
    targets = load_migration_targets()

    print("=" * 80)
    print("SERVICE TITAN MEDIA DUPLICATE CLEANUP")
    print(f"Migration log: {MIGRATION_LOG}")
    print(f"Customers with log-confirmed repeated files: {len(targets)}")
    print(f"Mode: {'DRY RUN' if DRY_RUN else 'DELETE'}")
    print("=" * 80)

    if not targets:
        print("No log-confirmed duplicate migration records found. Nothing to do.")
        return

    with sync_playwright() as p:
        browser, context = connect(p)
        page = wait_for_servicetitan(context)
        page.bring_to_front()

        total_deleted = 0
        failures = []

        for number, (customer_id, titles) in enumerate(targets.items(), start=1):
            print("=" * 80)
            print(f"MEDIA CLEANUP {number}/{len(targets)}: {customer_id}")
            print(f"Log-confirmed titles: {len(titles)}")
            print("=" * 80)

            if not open_customer_with_retry(page, customer_id):
                failures.append((customer_id, "customer not found"))
                continue

            try:
                total_deleted += clean_customer(page, customer_id, titles)
            except Exception as exc:
                print(f"FAILED {customer_id}: {exc}")
                failures.append((customer_id, str(exc)))

        print("=" * 80)
        print("MEDIA CLEANUP COMPLETE")
        print(f"Deleted/would delete: {total_deleted}")
        print(f"Failures: {len(failures)}")
        for customer_id, reason in failures:
            print(f"- {customer_id}: {reason}")
        print("=" * 80)
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()
