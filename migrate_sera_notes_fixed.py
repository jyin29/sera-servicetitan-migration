"""Run the full Sera note migration with exact ServiceTitan selectors and duplicate protection.

This runner keeps the existing migration/search/fallback/progress logic, but:
- processes EVERY pending Sera job (no 10-job limit)
- uses the exact ServiceTitan Job Summary editor/save selectors
- skips notes already migrated with our marker
- also skips manually-added notes when the Sera comment body is already visible in ServiceTitan
"""
import re

import migrate_sera_notes as migration


# Full migration: process every pending job. Existing COMPLETE/NO_COMMENTS jobs are
# still skipped by migrate_sera_notes.main() via its persistent progress log.
migration.MAX_JOBS = None


def normalize_text(value):
    """Normalize whitespace/case so formatting differences do not defeat duplicate checks."""
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()


def comment_body(note_text):
    """Remove our migration marker and return the original Sera comment text."""
    parts = note_text.split("\n\n", 1)
    return parts[1].strip() if len(parts) == 2 else note_text.strip()


def page_contains_manual_duplicate(page, note_text):
    """Detect a pre-existing/manual copy of the Sera note from visible ST page text."""
    body = normalize_text(comment_body(note_text))
    # Avoid treating tiny/generic fragments as duplicates.
    if len(body) < 20:
        return False
    try:
        visible = normalize_text(page.locator("body").inner_text())
    except Exception:
        return False
    return body in visible


def already_present(page, note_text, marker, destination):
    if migration.page_contains_marker(page, marker):
        print(f"Duplicate detected on {destination}: migration marker already exists; skipping.")
        return True
    if page_contains_manual_duplicate(page, note_text):
        print(f"Duplicate detected on {destination}: same Sera note text already exists (possibly added manually); skipping.")
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
        "(el, value) => { el.innerText = value; "
        "el.dispatchEvent(new InputEvent('input', "
        "{bubbles:true, inputType:'insertText', data:value})); }",
        note_text,
    )
    print("Filled ServiceTitan job Summary editor.")

    submit = page.locator(
        'button[data-tracking-id="jpm-job-summary-tab-content-button"]:visible'
    )
    submit.wait_for(state="visible", timeout=10000)
    if submit.count() != 1:
        raise RuntimeError(
            f"Expected exactly one job Summary save button, found {submit.count()}"
        )

    submit.click()
    print("Clicked ServiceTitan job Summary save button.")
    page.wait_for_timeout(1500)

    if not migration.page_contains_marker(page, marker):
        raise RuntimeError(
            "Job Summary save was clicked, but migrated note marker is not visible"
        )
    return "SUCCESS"


def add_customer_note_safe(page, note_text, marker):
    if already_present(page, note_text, marker, "customer"):
        return "SKIPPED"

    add_button = page.locator('button[data-tracking-id="crm-notes-add-note-button"]')
    add_button.wait_for(state="visible", timeout=10000)
    if migration.DRY_RUN:
        return "DRY_RUN"

    add_button.click()
    note_box = page.locator(
        'textarea[placeholder="Leave a note..."][data-anvil-component="TextArea"]:visible'
    ).first
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
    migration.main()
