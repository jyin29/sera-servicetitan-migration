"""Run the full Sera note migration with exact ServiceTitan selectors and duplicate protection.

Duplicate rule:
- automated copies are caught by our migration marker
- old/manual copies are caught ONLY when the exact original Sera message text is
  present on the ServiceTitan destination page; no fuzzy/partial matching
"""
import migrate_sera_notes as migration


migration.MAX_JOBS = None


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
    migration.main()
