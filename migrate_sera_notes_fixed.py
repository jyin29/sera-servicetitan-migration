"""Run the full Sera note migration with exact ServiceTitan selectors and duplicate protection.

Before migrating, this runner discovers job IDs directly from Sera's All Jobs report so
note migration is not limited to jobs that happened to exist in the media/database logs.

Duplicate rule:
- automated copies are caught by our migration marker
- old/manual copies are caught ONLY when the exact original Sera message text is
  present on the ServiceTitan destination page; no fuzzy/partial matching
"""
import re

from playwright.sync_api import sync_playwright

import migrate_sera_notes as migration
from sera.notes import get_or_open_sera_page
from servicetitan.browser import connect


migration.MAX_JOBS = None
SERA_ALL_JOBS_URL = "https://grmetro.sera.tech/reports/jobs?all=true"


def discover_all_sera_job_ids():
    """Discover every job linked by Sera's All Jobs report using the logged-in browser."""
    found = set()
    print("Opening Sera All Jobs report to discover the complete job list...")

    with sync_playwright() as p:
        browser, context = connect(p)
        page = get_or_open_sera_page(context)
        page.goto(SERA_ALL_JOBS_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)

        # all=true normally renders the whole report. Scroll repeatedly anyway so lazy
        # rows/virtualized tables have a chance to materialize before extracting links.
        stable_rounds = 0
        previous_count = -1
        for _ in range(80):
            hrefs = page.locator('a[href*="/jobs/"]').evaluate_all(
                "els => els.map(el => el.getAttribute('href') || '')"
            )
            for href in hrefs:
                match = re.search(r"/jobs/(\d+)", href)
                if match:
                    found.add(match.group(1))

            # Also inspect rendered HTML in case the job URL is attached to a non-anchor
            # element or framework router metadata.
            try:
                html = page.locator("body").inner_html()
                found.update(re.findall(r"/jobs/(\d+)", html))
            except Exception:
                pass

            if len(found) == previous_count:
                stable_rounds += 1
            else:
                stable_rounds = 0
                previous_count = len(found)

            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(400)
            if stable_rounds >= 5:
                break

        print(f"Sera All Jobs discovery found {len(found)} job IDs.")
        if not found:
            print("WARNING: All Jobs report yielded no job IDs; retaining local-source fallback.")

        try:
            browser.close()
        except Exception:
            pass

    return found


def install_complete_job_discovery():
    """Merge Sera report IDs with the existing local sources used by the migrator."""
    local_loader = migration.load_all_job_ids
    discovered = discover_all_sera_job_ids()

    def load_complete_job_ids():
        local = set(local_loader())
        combined = local | discovered
        print(
            f"Job discovery: {len(discovered)} from Sera report + "
            f"{len(local)} from local sources = {len(combined)} unique jobs."
        )
        return sorted(combined, key=int, reverse=True)

    migration.load_all_job_ids = load_complete_job_ids


def comment_body(note_text):
    """Return exactly the original Sera message, excluding our added migration marker."""
    parts = note_text.split("\n\n", 1)
    return parts[1] if len(parts) == 2 else note_text


def page_contains_exact_manual_duplicate(page, note_text):
    """True only when the full, exact Sera message already exists in visible ST text."""
    body = comment_body(note_text)
    if not body:
        return False
    try:
        visible = page.locator("body").inner_text()
    except Exception:
        return False
    return body in visible


def already_present(page, note_text, marker, destination):
    if migration.page_contains_marker(page, marker):
        print(f"Duplicate detected on {destination}: migration marker already exists; skipping.")
        return True
    if page_contains_exact_manual_duplicate(page, note_text):
        print(f"Duplicate detected on {destination}: EXACT Sera message already exists; skipping.")
        return True
    return False


def add_job_summary_exact(page, note_text, marker):
    if already_present(page, note_text, marker, "job"):
        return "SKIPPED"

    add_button = page.locator('button[data-tracking-id="jpm-job-add-button"]')
    add_button.wait_for(state="visible", timeout=10000)
    if migration.DRY_RUN:
        return "DRY_RUN"
    add_button.click()

    editor = page.locator('div[contenteditable="true"][class*="wysiwyg-editor"]:visible')
    editor.first.wait_for(state="visible", timeout=10000)
    if editor.count() != 1:
        raise RuntimeError(f"Expected exactly one job Summary editor, found {editor.count()}")
    editor = editor.first
    editor.scroll_into_view_if_needed()
    editor.click()
    editor.focus()
    editor.evaluate(
        "(el, value) => { el.innerText = value; el.dispatchEvent(new InputEvent('input', {bubbles:true, inputType:'insertText', data:value})); }",
        note_text,
    )
    print("Filled ServiceTitan job Summary editor.")

    submit = page.locator('button[data-tracking-id="jpm-job-summary-tab-content-button"]:visible')
    submit.wait_for(state="visible", timeout=10000)
    if submit.count() != 1:
        raise RuntimeError(f"Expected exactly one job Summary save button, found {submit.count()}")
    submit.click()
    print("Clicked ServiceTitan job Summary save button.")
    page.wait_for_timeout(1500)
    if not migration.page_contains_marker(page, marker):
        raise RuntimeError("Job Summary save was clicked, but migrated note marker is not visible")
    return "SUCCESS"


def add_customer_note_safe(page, note_text, marker):
    if already_present(page, note_text, marker, "customer"):
        return "SKIPPED"

    add_button = page.locator('button[data-tracking-id="crm-notes-add-note-button"]')
    add_button.wait_for(state="visible", timeout=10000)
    if migration.DRY_RUN:
        return "DRY_RUN"
    add_button.click()

    note_box = page.locator('textarea[placeholder="Leave a note..."][data-anvil-component="TextArea"]:visible').first
    note_box.wait_for(state="visible", timeout=10000)
    note_box.scroll_into_view_if_needed()
    note_box.click()
    note_box.focus()
    note_box.fill(note_text)

    submit = page.locator('button[data-tracking-id="add-note-button"]:visible')
    submit.wait_for(state="visible", timeout=10000)
    if submit.count() != 1:
        raise RuntimeError(f"Expected exactly one Add Note submit button, found {submit.count()}")
    submit.click()
    page.wait_for_timeout(1500)
    if not migration.page_contains_marker(page, marker):
        raise RuntimeError("Customer Add Note was clicked, but migrated note marker is not visible")
    return "SUCCESS"


migration.add_job_summary = add_job_summary_exact
migration.add_customer_note = add_customer_note_safe

if __name__ == "__main__":
    install_complete_job_discovery()
    migration.main()
