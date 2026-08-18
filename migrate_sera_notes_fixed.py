"""Run the full Sera note migration from an exported Sera Jobs Report.

The JobsReport Excel export is the source of truth for job discovery. This avoids
limiting the migration to jobs that happened to appear in the old media/database logs.

Duplicate rule:
- automated copies are caught by our migration marker
- old/manual copies are caught ONLY when the exact original Sera message text is
  present on the ServiceTitan destination page; no fuzzy/partial matching
"""
from pathlib import Path

from openpyxl import load_workbook

import migrate_sera_notes as migration


migration.MAX_JOBS = None


def find_jobs_report():
    """Find the newest Sera JobsReport .xlsx in the normal local locations."""
    roots = [
        Path.cwd(),
        Path(__file__).resolve().parent,
        Path.home() / "Downloads",
        migration.APP_DATA,
    ]
    candidates = []
    seen = set()
    for root in roots:
        if not root.exists():
            continue
        for path in root.glob("JobsReport*.xlsx"):
            try:
                resolved = path.resolve()
            except Exception:
                resolved = path
            if resolved in seen:
                continue
            seen.add(resolved)
            candidates.append(path)

    if not candidates:
        raise RuntimeError(
            "No Sera JobsReport*.xlsx found. Download/export the Sera Jobs Report "
            "and leave it in Downloads (or put it beside this script), then run again."
        )

    # If there are multiple exports, use the newest one.
    return max(candidates, key=lambda p: p.stat().st_mtime)


def load_jobs_report_ids(path):
    """Read every job ID from the exact 'Job' column in a Sera Jobs Report export."""
    print(f"Using Sera Jobs Report: {path}")
    workbook = load_workbook(path, read_only=True, data_only=True)
    sheet = workbook.active

    rows = sheet.iter_rows(values_only=True)
    try:
        headers = [str(value or "").strip() for value in next(rows)]
    except StopIteration:
        workbook.close()
        raise RuntimeError("Jobs Report is empty.")

    if "Job" not in headers:
        workbook.close()
        raise RuntimeError(
            f"Jobs Report does not contain the expected 'Job' column. Columns: {headers}"
        )

    job_index = headers.index("Job")
    found = set()
    invalid = 0

    for row in rows:
        if job_index >= len(row):
            continue
        value = row[job_index]
        job_id = migration.clean_id(value)
        if not job_id:
            continue
        if job_id.isdigit():
            found.add(job_id)
        else:
            invalid += 1

    workbook.close()

    if not found:
        raise RuntimeError("Jobs Report contained zero usable numeric job IDs; refusing to fall back to the old 335-job subset.")

    print(f"Sera Jobs Report contains {len(found)} unique job IDs.")
    if invalid:
        print(f"WARNING: ignored {invalid} non-numeric Job value(s).")
    return found


def install_complete_job_discovery():
    """Make the Jobs Report the master job list, with local IDs added only as a safety union."""
    report_path = find_jobs_report()
    report_ids = load_jobs_report_ids(report_path)
    local_loader = migration.load_all_job_ids

    def load_complete_job_ids():
        local = set(local_loader())
        combined = report_ids | local
        extra_local = local - report_ids
        print(
            f"Job discovery: {len(report_ids)} from Jobs Report + "
            f"{len(extra_local)} extra local-only = {len(combined)} unique jobs."
        )
        if len(report_ids) < 1000:
            raise RuntimeError(
                f"Jobs Report yielded only {len(report_ids)} jobs. Expected the full export; refusing bulk WRITE run."
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
