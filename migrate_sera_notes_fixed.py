"""Run the bulk Sera note migration with exact ServiceTitan Job Summary selectors.

Temporary compatibility runner: imports the existing bulk migration unchanged, replaces
only the Job Summary writer, then runs the normal bulk main().
"""
import migrate_sera_notes as migration


def add_job_summary_exact(page, note_text, marker):
    if migration.page_contains_marker(page, marker):
        print("Already present on job; skipping duplicate.")
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


migration.add_job_summary = add_job_summary_exact

if __name__ == "__main__":
    migration.main()
