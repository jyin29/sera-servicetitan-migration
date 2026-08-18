import csv
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

from sera.notes import get_or_open_sera_page, load_job_comments
from servicetitan.browser import connect, wait_for_servicetitan
from servicetitan.job_search import JobSearcher
from servicetitan.customer_search import CustomerSearcher

APP_DATA = Path(os.getenv("LOCALAPPDATA")) / "Sera ServiceTitan Migration"
MIGRATION_LOG = APP_DATA / "migration_log.csv"
SERA_MEDIA = APP_DATA / "sera_media"

# First end-to-end test. Keep this to one job until verified.
JOB_IDS = ["6505724"]

# Set False only after the dry-run output looks correct.
DRY_RUN = True


def load_job_to_customer_map():
    mapping = {}

    if MIGRATION_LOG.exists():
        with MIGRATION_LOG.open("r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                job_id = (row.get("Job Number") or "").strip()
                legacy_id = (row.get("Legacy ID") or "").strip()
                if job_id and legacy_id:
                    mapping.setdefault(job_id, legacy_id)

    # Fallback to the original downloaded folder structure. This does not require
    # files to still exist inside the Job_* folder.
    if SERA_MEDIA.exists():
        for customer_dir in SERA_MEDIA.glob("Customer_*"):
            if not customer_dir.is_dir():
                continue
            legacy_id = customer_dir.name.replace("Customer_", "", 1).strip()
            for job_dir in customer_dir.glob("Job_*"):
                if not job_dir.is_dir():
                    continue
                job_id = job_dir.name.replace("Job_", "", 1).strip()
                if job_id and legacy_id:
                    mapping.setdefault(job_id, legacy_id)

    return mapping


def format_note(job_id, comment):
    stamp = comment.get("timestamp") or " ".join(
        part for part in [comment.get("date", ""), comment.get("time", "")] if part
    )
    author = comment.get("author") or "Unknown"
    marker = f"[Migrated from Sera | Job {job_id} | {stamp} | {author}]"
    body = comment["text"].strip()
    return marker, f"{marker}\n\n{body}"


def page_contains_marker(page, marker):
    try:
        return page.get_by_text(marker, exact=False).count() > 0
    except Exception:
        return marker in page.locator("body").inner_text()


def find_single_visible_editor(page):
    candidates = page.locator(
        "textarea:visible, [contenteditable='true']:visible, "
        "input[type='text']:visible"
    )

    usable = []
    for i in range(candidates.count()):
        item = candidates.nth(i)
        try:
            if item.is_enabled() and item.is_visible():
                usable.append(item)
        except Exception:
            pass

    if len(usable) != 1:
        raise RuntimeError(
            f"Expected exactly one visible note editor after clicking Add, found {len(usable)}"
        )

    return usable[0]


def fill_editor(editor, text):
    tag = editor.evaluate("el => el.tagName.toLowerCase()")
    if tag in {"textarea", "input"}:
        editor.fill(text)
    else:
        editor.click()
        editor.evaluate(
            "(el, value) => { el.innerText = value; "
            "el.dispatchEvent(new InputEvent('input', {bubbles:true, inputType:'insertText', data:value})); }",
            text,
        )


def click_single_save_button(page):
    # Restrict to visible enabled buttons whose text strongly indicates submit/save.
    buttons = page.locator("button:visible")
    matches = []

    for i in range(buttons.count()):
        button = buttons.nth(i)
        try:
            if not button.is_enabled():
                continue
            text = " ".join(button.inner_text().split()).strip().lower()
            if text in {"save", "add", "add note", "add summary", "submit"}:
                matches.append(button)
        except Exception:
            pass

    if len(matches) != 1:
        labels = []
        for button in matches:
            try:
                labels.append(" ".join(button.inner_text().split()))
            except Exception:
                labels.append("?")
        raise RuntimeError(
            f"Expected exactly one visible Save/Add button, found {len(matches)}: {labels}"
        )

    matches[0].click()


def add_job_summary(page, note_text, marker):
    if page_contains_marker(page, marker):
        print("Already present on job; skipping duplicate.")
        return "SKIPPED"

    add_button = page.locator('button[data-tracking-id="jpm-job-add-button"]')
    add_button.wait_for(state="visible", timeout=10000)

    if DRY_RUN:
        print("DRY RUN: would click + Add Summary and add:")
        print(note_text)
        return "DRY_RUN"

    before_editors = page.locator(
        "textarea:visible, [contenteditable='true']:visible, input[type='text']:visible"
    ).count()

    add_button.click()
    page.wait_for_timeout(500)

    editor = find_single_visible_editor(page)
    after_editors = page.locator(
        "textarea:visible, [contenteditable='true']:visible, input[type='text']:visible"
    ).count()

    print(f"Visible editors before/after Add Summary: {before_editors}/{after_editors}")
    fill_editor(editor, note_text)
    click_single_save_button(page)
    page.wait_for_timeout(1200)

    if not page_contains_marker(page, marker):
        raise RuntimeError("Job summary save was clicked, but migrated note marker is not visible")

    return "SUCCESS"


def add_customer_note(page, note_text, marker):
    if page_contains_marker(page, marker):
        print("Already present on customer; skipping duplicate.")
        return "SKIPPED"

    add_button = page.locator('button[data-tracking-id="crm-notes-add-note-button"]')
    add_button.wait_for(state="visible", timeout=10000)

    if DRY_RUN:
        print("DRY RUN: would click Add Note and add:")
        print(note_text)
        return "DRY_RUN"

    add_button.click()
    page.wait_for_timeout(500)
    editor = find_single_visible_editor(page)
    fill_editor(editor, note_text)
    click_single_save_button(page)
    page.wait_for_timeout(1200)

    if not page_contains_marker(page, marker):
        raise RuntimeError("Customer note save was clicked, but migrated note marker is not visible")

    return "SUCCESS"


def main():
    job_to_customer = load_job_to_customer_map()

    with sync_playwright() as p:
        browser, context = connect(p)
        st_page = wait_for_servicetitan(context)
        sera_page = get_or_open_sera_page(context)

        st_page.bring_to_front()
        job_search = JobSearcher(st_page)
        customer_search = CustomerSearcher(st_page)

        total_notes = 0
        completed = 0
        skipped = 0
        failures = []

        for job_id in JOB_IDS:
            print("=" * 80)
            print(f"SERA NOTE MIGRATION: job {job_id}")
            legacy_id = job_to_customer.get(job_id)
            print(f"Legacy ID: {legacy_id or 'not found'}")
            print(f"Mode: {'DRY RUN' if DRY_RUN else 'WRITE'}")
            print("=" * 80)

            comments = load_job_comments(sera_page, job_id)
            print(f"Found {len(comments)} Sera comment(s)")
            total_notes += len(comments)

            if not comments:
                continue

            st_page.bring_to_front()

            try:
                job_found = job_search.open_job(job_id)
            except Exception as exc:
                print(f"Job search error: {exc}")
                job_found = False

            destination = "JOB" if job_found else None

            if not job_found:
                if not legacy_id:
                    failures.append((job_id, "Job not found and Legacy ID unavailable for customer fallback"))
                    print("Cannot fall back to customer because Legacy ID is unavailable.")
                    continue

                try:
                    if customer_search.open_customer(legacy_id):
                        destination = "CUSTOMER"
                    else:
                        failures.append((job_id, "Neither job nor customer found"))
                        continue
                except Exception as exc:
                    failures.append((job_id, f"Customer search error: {exc}"))
                    continue

            for number, comment in enumerate(comments, start=1):
                marker, note_text = format_note(job_id, comment)
                print("-" * 80)
                print(f"Comment {number}/{len(comments)} -> {destination}")
                print(marker)

                try:
                    if destination == "JOB":
                        result = add_job_summary(st_page, note_text, marker)
                    else:
                        result = add_customer_note(st_page, note_text, marker)

                    if result == "SKIPPED":
                        skipped += 1
                    else:
                        completed += 1
                except Exception as exc:
                    print(f"FAILED comment {number}: {exc}")
                    failures.append((job_id, f"Comment {number}: {exc}"))
                    break

        print("=" * 80)
        print("NOTE MIGRATION COMPLETE")
        print(f"Sera comments found: {total_notes}")
        print(f"Completed/would complete: {completed}")
        print(f"Already present/skipped: {skipped}")
        print(f"Failures: {len(failures)}")
        for job_id, reason in failures:
            print(f"- {job_id}: {reason}")
        print("=" * 80)
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()
