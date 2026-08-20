"""Run Sera note migration from an exported Sera Jobs Report.

Usage:
  python migrate_sera_notes_fixed.py
  python migrate_sera_notes_fixed.py --last 4000

--last N deliberately reruns the last N rows/jobs from the Jobs Report regardless of
progress status. Existing marker/exact-message duplicate protection still applies.
"""
import argparse
from pathlib import Path

from openpyxl import load_workbook

import migrate_sera_notes as migration

migration.MAX_JOBS = None
RERUN_LAST = None


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--last", type=int, default=None, metavar="N", help="rerun only the last N jobs in Jobs Report order, ignoring progress-complete filtering")
    args = parser.parse_args()
    if args.last is not None and args.last <= 0:
        parser.error("--last must be greater than 0")
    return args


def find_jobs_report():
    roots = [Path.cwd(), Path(__file__).resolve().parent, Path.home() / "Downloads", migration.APP_DATA]
    candidates, seen = [], set()
    for root in roots:
        if not root.exists(): continue
        for path in root.glob("JobsReport*.xlsx"):
            try: resolved = path.resolve()
            except Exception: resolved = path
            if resolved in seen: continue
            seen.add(resolved); candidates.append(path)
    if not candidates:
        raise RuntimeError("No Sera JobsReport*.xlsx found. Put the Sera Jobs Report in Downloads or beside this script.")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def load_jobs_report_ids(path):
    """Read unique numeric Job IDs while PRESERVING spreadsheet row order."""
    print(f"Using Sera Jobs Report: {path}")
    workbook = load_workbook(path, read_only=True, data_only=True)
    sheet = workbook.active; rows = sheet.iter_rows(values_only=True)
    try: headers = [str(value or "").strip() for value in next(rows)]
    except StopIteration:
        workbook.close(); raise RuntimeError("Jobs Report is empty.")
    if "Job" not in headers:
        workbook.close(); raise RuntimeError(f"Jobs Report does not contain the expected 'Job' column. Columns: {headers}")
    job_index = headers.index("Job"); found = []; seen = set(); invalid = 0
    for row in rows:
        if job_index >= len(row): continue
        job_id = migration.clean_id(row[job_index])
        if not job_id: continue
        if job_id.isdigit():
            if job_id not in seen:
                seen.add(job_id); found.append(job_id)
        else: invalid += 1
    workbook.close()
    if not found: raise RuntimeError("Jobs Report contained zero usable numeric job IDs.")
    print(f"Sera Jobs Report contains {len(found)} unique job IDs.")
    if invalid: print(f"WARNING: ignored {invalid} non-numeric Job value(s).")
    return found


def install_job_discovery(last_n=None):
    report_path = find_jobs_report(); report_ids = load_jobs_report_ids(report_path)
    if len(report_ids) < 1000:
        raise RuntimeError(f"Jobs Report yielded only {len(report_ids)} jobs. Expected the full export; refusing bulk WRITE run.")

    if last_n is not None:
        selected = report_ids[-last_n:] if last_n < len(report_ids) else list(report_ids)
        print(f"RERUN RANGE MODE: selecting last {len(selected)} jobs from Jobs Report order.")
        print("Progress COMPLETE/NO_COMMENTS status will be ignored for this selected range.")

        # main() normally removes COMPLETE/NO_COMMENTS IDs. For an explicit rerun range,
        # expose only this range and report nothing as previously complete. Duplicate checks
        # at the destination remain the final protection against duplicate writes.
        migration.load_all_job_ids = lambda: list(selected)
        migration.load_completed_jobs = lambda: set()
        return

    local_loader = migration.load_all_job_ids
    def load_complete_job_ids():
        local = set(local_loader()); report_set = set(report_ids); combined = report_set | local; extra_local = local - report_set
        print(f"Job discovery: {len(report_ids)} from Jobs Report + {len(extra_local)} extra local-only = {len(combined)} unique jobs.")
        return sorted(combined, key=int, reverse=True)
    migration.load_all_job_ids = load_complete_job_ids


def comment_body(note_text):
    parts = note_text.split("\n\n", 1)
    return parts[1] if len(parts) == 2 else note_text


def page_contains_exact_manual_duplicate(page, note_text):
    body = comment_body(note_text)
    if not body: return False
    try: visible = page.locator("body").inner_text()
    except Exception: return False
    return body in visible


def already_present(page, note_text, marker, destination):
    if migration.page_contains_marker(page, marker):
        print(f"Duplicate detected on {destination}: migration marker already exists; skipping."); return True
    if page_contains_exact_manual_duplicate(page, note_text):
        print(f"Duplicate detected on {destination}: EXACT Sera message already exists; skipping."); return True
    return False


def add_job_summary_exact(page, note_text, marker):
    if already_present(page, note_text, marker, "job"): return "SKIPPED"
    add_button = page.locator('button[data-tracking-id="jpm-job-add-button"]'); add_button.wait_for(state="visible", timeout=10000)
    if migration.DRY_RUN: return "DRY_RUN"
    add_button.click()
    editor = page.locator('div[contenteditable="true"][class*="wysiwyg-editor"]:visible'); editor.first.wait_for(state="visible", timeout=10000)
    if editor.count() != 1: raise RuntimeError(f"Expected exactly one job Summary editor, found {editor.count()}")
    editor = editor.first; editor.scroll_into_view_if_needed(); editor.click(); editor.focus()
    editor.evaluate("(el, value) => { el.innerText = value; el.dispatchEvent(new InputEvent('input', {bubbles:true, inputType:'insertText', data:value})); }", note_text)
    print("Filled ServiceTitan job Summary editor.")
    submit = page.locator('button[data-tracking-id="jpm-job-summary-tab-content-button"]:visible'); submit.wait_for(state="visible", timeout=10000)
    if submit.count() != 1: raise RuntimeError(f"Expected exactly one job Summary save button, found {submit.count()}")
    submit.click(); print("Clicked ServiceTitan job Summary save button."); page.wait_for_timeout(1500)
    if not migration.page_contains_marker(page, marker): raise RuntimeError("Job Summary save was clicked, but migrated note marker is not visible")
    return "SUCCESS"


def add_customer_note_safe(page, note_text, marker):
    if already_present(page, note_text, marker, "customer"): return "SKIPPED"
    add_button = page.locator('button[data-tracking-id="crm-notes-add-note-button"]'); add_button.wait_for(state="visible", timeout=10000)
    if migration.DRY_RUN: return "DRY_RUN"
    add_button.click()
    note_box = page.locator('textarea[placeholder="Leave a note..."][data-anvil-component="TextArea"]:visible').first; note_box.wait_for(state="visible", timeout=10000)
    note_box.scroll_into_view_if_needed(); note_box.click(); note_box.focus(); note_box.fill(note_text)
    submit = page.locator('button[data-tracking-id="add-note-button"]:visible'); submit.wait_for(state="visible", timeout=10000)
    if submit.count() != 1: raise RuntimeError(f"Expected exactly one Add Note submit button, found {submit.count()}")
    submit.click(); page.wait_for_timeout(1500)
    if not migration.page_contains_marker(page, marker): raise RuntimeError("Customer Add Note was clicked, but migrated note marker is not visible")
    return "SUCCESS"


migration.add_job_summary = add_job_summary_exact
migration.add_customer_note = add_customer_note_safe

if __name__ == "__main__":
    args = parse_args()
    install_job_discovery(args.last)
    migration.main()
