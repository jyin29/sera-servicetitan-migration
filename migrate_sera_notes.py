import csv
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

from sera.notes import get_or_open_sera_page, load_job_data
from servicetitan.browser import connect, wait_for_servicetitan
from servicetitan.job_search import JobSearcher
from servicetitan.customer_search import CustomerSearcher

APP_DATA = Path(os.getenv("LOCALAPPDATA")) / "Sera ServiceTitan Migration"
MIGRATION_LOG = APP_DATA / "migration_log.csv"
FAILED_DIR = APP_DATA / "failed_notes"
PROGRESS_LOG = APP_DATA / "note_migration_progress.csv"
MEDIA_ROOTS = [APP_DATA / "sera_media", Path(__file__).resolve().parent / "sera_media"]
MIGRATION_DATABASES = [APP_DATA / "migration.db", Path(__file__).resolve().parent / "database" / "migration.db"]

# Bulk mode. Start with 10 real jobs; after checking them, change MAX_JOBS to None.
MAX_JOBS = 10
DRY_RUN = False


def clean_id(value):
    value = str(value or "").strip()
    if value.endswith(".0") and value[:-2].isdigit():
        value = value[:-2]
    return value


def add_mapping(mapping, sources, job_id, legacy_id, source):
    job_id, legacy_id = clean_id(job_id), clean_id(legacy_id)
    if not job_id or not legacy_id or legacy_id.lower() == "none":
        return
    if job_id not in mapping:
        mapping[job_id] = legacy_id
        sources[job_id] = source


def load_job_to_customer_map():
    mapping, sources = {}, {}
    for db_path in MIGRATION_DATABASES:
        if not db_path.exists():
            continue
        try:
            connection = sqlite3.connect(str(db_path))
            cursor = connection.cursor()
            cursor.execute("SELECT jobs.sera_job_number, customers.legacy_id FROM jobs JOIN customers ON customers.id = jobs.customer_id WHERE jobs.sera_job_number IS NOT NULL AND customers.legacy_id IS NOT NULL")
            for job_id, legacy_id in cursor.fetchall():
                add_mapping(mapping, sources, job_id, legacy_id, f"database {db_path}")
            connection.close()
        except Exception as exc:
            print(f"Could not read {db_path}: {exc}")
    if MIGRATION_LOG.exists():
        with MIGRATION_LOG.open("r", newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                add_mapping(mapping, sources, row.get("Job Number"), row.get("Legacy ID"), f"migration log {MIGRATION_LOG}")
    for media_root in MEDIA_ROOTS:
        if not media_root.exists():
            continue
        for customer_dir in media_root.glob("Customer_*"):
            legacy_id = customer_dir.name.replace("Customer_", "", 1).strip()
            for job_dir in customer_dir.glob("Job_*"):
                add_mapping(mapping, sources, job_dir.name.replace("Job_", "", 1), legacy_id, f"media folder {job_dir}")
    return mapping, sources


def load_all_job_ids():
    """Load every known Sera job number from all local migration sources."""
    found = set()

    for db_path in MIGRATION_DATABASES:
        if not db_path.exists():
            continue
        try:
            connection = sqlite3.connect(str(db_path))
            cursor = connection.cursor()
            cursor.execute("SELECT sera_job_number FROM jobs WHERE sera_job_number IS NOT NULL")
            for (job_id,) in cursor.fetchall():
                job_id = clean_id(job_id)
                if job_id.isdigit():
                    found.add(job_id)
            connection.close()
        except Exception as exc:
            print(f"Could not load job IDs from {db_path}: {exc}")

    if MIGRATION_LOG.exists():
        with MIGRATION_LOG.open("r", newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                job_id = clean_id(row.get("Job Number"))
                if job_id.isdigit():
                    found.add(job_id)

    for media_root in MEDIA_ROOTS:
        if not media_root.exists():
            continue
        for job_dir in media_root.glob("Customer_*/Job_*"):
            job_id = clean_id(job_dir.name.replace("Job_", "", 1))
            if job_id.isdigit():
                found.add(job_id)

    # Highest/newest-looking IDs first. The exact order is not important because
    # progress is persistent and every job is independently resumable.
    return sorted(found, key=int, reverse=True)


def load_completed_jobs():
    completed = set()
    if not PROGRESS_LOG.exists():
        return completed
    try:
        with PROGRESS_LOG.open("r", newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                if row.get("status") in {"COMPLETE", "NO_COMMENTS"}:
                    completed.add(clean_id(row.get("job_id")))
    except Exception as exc:
        print(f"WARNING: could not read progress log: {exc}")
    return completed


def record_progress(job_id, status, destination="", note_count=0, detail=""):
    PROGRESS_LOG.parent.mkdir(parents=True, exist_ok=True)
    exists = PROGRESS_LOG.exists()
    with PROGRESS_LOG.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "job_id", "status", "destination", "note_count", "detail"])
        if not exists:
            writer.writeheader()
        writer.writerow({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "job_id": job_id,
            "status": status,
            "destination": destination,
            "note_count": note_count,
            "detail": detail,
        })


def format_note(job_id, comment):
    stamp = comment.get("timestamp") or " ".join(part for part in [comment.get("date", ""), comment.get("time", "")] if part)
    author = comment.get("author") or "Unknown"
    marker = f"[Migrated from Sera | Job {job_id} | {stamp} | {author}]"
    return marker, f"{marker}\n\n{comment['text'].strip()}"


def save_failed_job(job_id, job_data, reason):
    FAILED_DIR.mkdir(parents=True, exist_ok=True)
    path = FAILED_DIR / f"Job_{job_id}.txt"
    lines = [f"Sera Job: {job_id}", f"Sera Customer: {job_data.get('customer_name', '')}", f"Sera Customer ID / ServiceTitan Legacy ID: {job_data.get('sera_customer_id', '')}", f"Reason: {reason}", "", "COMMENTS", "=" * 80]
    for number, comment in enumerate(job_data.get("comments", []), start=1):
        marker, note_text = format_note(job_id, comment)
        lines.extend([f"Comment {number}", note_text, "", "-" * 80])
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved unresolved note(s) to: {path}")


def page_contains_marker(page, marker):
    try:
        return page.get_by_text(marker, exact=False).count() > 0
    except Exception:
        return marker in page.locator("body").inner_text()


def find_single_visible_editor(page):
    note_box = page.locator('textarea[placeholder="Leave a note..."][data-anvil-component="TextArea"]:visible')
    try:
        note_box.first.wait_for(state="visible", timeout=5000)
    except Exception:
        pass
    if note_box.count() == 1:
        editor = note_box.first
        editor.scroll_into_view_if_needed()
        editor.click()
        editor.focus()
        return editor
    candidates = page.locator("textarea:visible, [contenteditable='true']:visible, input[type='text']:visible")
    usable = []
    for i in range(candidates.count()):
        item = candidates.nth(i)
        try:
            if item.is_enabled() and item.is_visible():
                usable.append(item)
        except Exception:
            pass
    if len(usable) != 1:
        raise RuntimeError(f"Expected exactly one visible note editor after clicking Add, found {len(usable)}")
    usable[0].scroll_into_view_if_needed()
    usable[0].click()
    usable[0].focus()
    return usable[0]


def fill_editor(editor, text):
    tag = editor.evaluate("el => el.tagName.toLowerCase()")
    editor.scroll_into_view_if_needed()
    editor.click()
    editor.focus()
    if tag in {"textarea", "input"}:
        editor.fill(text)
    else:
        editor.evaluate("(el, value) => { el.innerText = value; el.dispatchEvent(new InputEvent('input', {bubbles:true, inputType:'insertText', data:value})); }", text)


def click_single_save_button(page):
    buttons = page.locator("button:visible")
    matches = []
    for i in range(buttons.count()):
        button = buttons.nth(i)
        try:
            if button.is_enabled() and " ".join(button.inner_text().split()).strip().lower() in {"save", "add", "add note", "add summary", "submit"}:
                matches.append(button)
        except Exception:
            pass
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one visible Save/Add button, found {len(matches)}")
    matches[0].click()


def add_job_summary(page, note_text, marker):
    if page_contains_marker(page, marker):
        print("Already present on job; skipping duplicate.")
        return "SKIPPED"
    add_button = page.locator('button[data-tracking-id="jpm-job-add-button"]')
    add_button.wait_for(state="visible", timeout=10000)
    if DRY_RUN:
        return "DRY_RUN"
    add_button.click()
    page.wait_for_timeout(500)
    fill_editor(find_single_visible_editor(page), note_text)
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
    if not page_contains_marker(page, marker):
        raise RuntimeError("Customer Add Note was clicked, but migrated note marker is not visible")
    return "SUCCESS"


def main():
    old_job_map, _ = load_job_to_customer_map()
    all_jobs = load_all_job_ids()
    completed_jobs = load_completed_jobs()
    pending = [job_id for job_id in all_jobs if job_id not in completed_jobs]
    selected = pending[:MAX_JOBS] if MAX_JOBS is not None else pending

    print("=" * 80)
    print("BULK SERA NOTE MIGRATION")
    print(f"Known jobs: {len(all_jobs)}")
    print(f"Previously completed/no-comments: {len(completed_jobs)}")
    print(f"Pending: {len(pending)}")
    print(f"This run: {len(selected)}{' (safety limit)' if MAX_JOBS is not None else ''}")
    print(f"Mode: {'DRY RUN' if DRY_RUN else 'WRITE'}")
    print(f"Progress log: {PROGRESS_LOG}")
    print("=" * 80)

    if not selected:
        print("Nothing left to process.")
        return

    with sync_playwright() as p:
        browser, context = connect(p)
        st_page = wait_for_servicetitan(context)
        sera_page = get_or_open_sera_page(context)
        job_search = JobSearcher(st_page)
        customer_search = CustomerSearcher(st_page)
        total_notes = completed_notes = skipped_notes = 0
        failures = []

        for position, job_id in enumerate(selected, start=1):
            print("\n" + "=" * 80)
            print(f"[{position}/{len(selected)}] SERA JOB {job_id}")
            print("=" * 80)
            job_data = None
            try:
                job_data = load_job_data(sera_page, job_id)
                sera_customer_id = clean_id(job_data["sera_customer_id"])
                sera_customer_name = job_data["customer_name"]
                comments = job_data["comments"]
                total_notes += len(comments)
                print(f"Sera customer: {sera_customer_name} ({sera_customer_id})")
                print(f"Comments: {len(comments)}")

                if not comments:
                    record_progress(job_id, "NO_COMMENTS", note_count=0)
                    print("No comments; marked complete.")
                    continue

                legacy_id = sera_customer_id
                old_legacy_id = old_job_map.get(job_id)
                if old_legacy_id and old_legacy_id != legacy_id:
                    print(f"WARNING: old mapping says {old_legacy_id}; Sera page says {legacy_id}. Using Sera page.")

                st_page.bring_to_front()
                try:
                    job_found = job_search.open_job(job_id)
                except Exception as exc:
                    print(f"Job search error: {exc}")
                    job_found = False

                destination = "JOB" if job_found else None
                if not job_found:
                    customer_found = False
                    try:
                        customer_found = customer_search.open_customer(legacy_id)
                        if not customer_found:
                            customer_found = customer_search.open_customer_by_name(sera_customer_name)
                    except Exception as exc:
                        print(f"Customer search error: {exc}")
                    if customer_found:
                        destination = "CUSTOMER"
                    else:
                        reason = f"No safe ServiceTitan match by Legacy ID {legacy_id} or customer name {sera_customer_name}"
                        failures.append((job_id, reason))
                        save_failed_job(job_id, job_data, reason)
                        record_progress(job_id, "FAILED", note_count=len(comments), detail=reason)
                        continue

                job_failed = False
                for number, comment in enumerate(comments, start=1):
                    marker, note_text = format_note(job_id, comment)
                    print(f"Comment {number}/{len(comments)} -> {destination}")
                    try:
                        result = add_job_summary(st_page, note_text, marker) if destination == "JOB" else add_customer_note(st_page, note_text, marker)
                        if result == "SKIPPED":
                            skipped_notes += 1
                        else:
                            completed_notes += 1
                    except Exception as exc:
                        reason = f"Comment {number}: {exc}"
                        print(f"FAILED: {reason}")
                        failures.append((job_id, reason))
                        save_failed_job(job_id, job_data, reason)
                        record_progress(job_id, "FAILED", destination, len(comments), reason)
                        job_failed = True
                        break

                if not job_failed:
                    # Only mark the whole job complete after every comment either
                    # wrote successfully or was already present in ServiceTitan.
                    record_progress(job_id, "COMPLETE", destination, len(comments))
                    print(f"JOB {job_id} COMPLETE")

            except Exception as exc:
                reason = f"Unhandled job error: {exc}"
                print(f"FAILED {job_id}: {reason}")
                failures.append((job_id, reason))
                if job_data:
                    save_failed_job(job_id, job_data, reason)
                record_progress(job_id, "FAILED", note_count=len(job_data.get('comments', [])) if job_data else 0, detail=reason)

        print("\n" + "=" * 80)
        print("BULK NOTE MIGRATION RUN COMPLETE")
        print(f"Jobs attempted: {len(selected)}")
        print(f"Comments encountered: {total_notes}")
        print(f"Written/would write: {completed_notes}")
        print(f"Already present/skipped: {skipped_notes}")
        print(f"Failures this run: {len(failures)}")
        print(f"Progress log: {PROGRESS_LOG}")
        print(f"Failed-note folder: {FAILED_DIR}")
        print("=" * 80)
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()
