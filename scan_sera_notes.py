import csv
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

from servicetitan.browser import connect

APP_DATA = Path(os.getenv("LOCALAPPDATA")) / "Sera ServiceTitan Migration"
MIGRATION_LOG = APP_DATA / "migration_log.csv"
SERA_JOB_URL = "https://grmetro.sera.tech/jobs/{job_id}"

# Safe first test. This script is READ ONLY and writes nothing to ServiceTitan.
TEST_JOB_IDS = ["6505724"]


def get_or_open_sera_page(context):
    for page in context.pages:
        if "grmetro.sera.tech" in page.url.lower():
            return page
    return context.new_page()


def extract_comments(page):
    comments = []
    groups = page.locator(".comment-group")

    for group_index in range(groups.count()):
        group = groups.nth(group_index)
        date_parts = group.locator(".comment-group-timestamp span")
        date_text = " ".join(
            date_parts.nth(i).inner_text().strip()
            for i in range(date_parts.count())
            if date_parts.nth(i).inner_text().strip()
        )

        group_comments = group.locator(".comment")
        for comment_index in range(group_comments.count()):
            comment = group_comments.nth(comment_index)

            content = comment.locator(".comment-content span")
            text = content.first.inner_text().strip() if content.count() else ""
            if not text:
                continue

            author_el = comment.locator(".comment-header b")
            author = author_el.first.inner_text().strip() if author_el.count() else ""

            time_el = comment.locator(".comment-header .timestamp")
            time_text = time_el.first.inner_text().strip() if time_el.count() else ""
            timestamp_title = time_el.first.get_attribute("data-tippy-content") if time_el.count() else ""

            comments.append({
                "date": date_text,
                "time": time_text,
                "timestamp": timestamp_title or "",
                "author": author,
                "text": text,
            })

    return comments


def load_job_to_customer_map():
    mapping = {}
    if not MIGRATION_LOG.exists():
        return mapping

    with MIGRATION_LOG.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            job_id = (row.get("Job Number") or "").strip()
            legacy_id = (row.get("Legacy ID") or "").strip()
            if job_id and legacy_id:
                mapping.setdefault(job_id, legacy_id)
    return mapping


def main():
    job_to_customer = load_job_to_customer_map()

    with sync_playwright() as p:
        browser, context = connect(p)
        sera_page = get_or_open_sera_page(context)

        for job_id in TEST_JOB_IDS:
            print("=" * 80)
            print(f"SERA NOTE SCAN: job {job_id}")
            print(f"Legacy ID: {job_to_customer.get(job_id, 'not found in migration log')}")
            print("=" * 80)

            sera_page.goto(SERA_JOB_URL.format(job_id=job_id), wait_until="domcontentloaded")
            sera_page.wait_for_timeout(2500)

            try:
                sera_page.locator(".comment-group").first.wait_for(state="visible", timeout=15000)
            except Exception:
                print("No visible .comment-group found. If Sera opened a login page, log in in this Edge profile and rerun.")
                continue

            comments = extract_comments(sera_page)
            print(f"Found {len(comments)} comments")

            for number, comment in enumerate(comments, start=1):
                print("-" * 80)
                print(f"COMMENT {number}")
                print(f"Author: {comment['author']}")
                print(f"Date: {comment['date']}")
                print(f"Time: {comment['time']}")
                print(f"Timestamp: {comment['timestamp']}")
                print("Text:")
                print(comment["text"])

        print("=" * 80)
        print("READ-ONLY SERA NOTE SCAN COMPLETE")
        print("Nothing was written to ServiceTitan.")
        print("=" * 80)
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()
