from pathlib import Path
from playwright.sync_api import Page
import shutil


class Uploader:

    def __init__(self, page: Page):
        self.page = page

    @staticmethod
    def _attachment_name(filename: str) -> str:
        """Normalize a local filename the same way ServiceTitan displays qa-title."""
        return Path(filename).stem.strip().lower()

    def attachment_exists(self, filename: str) -> bool:

        target = self._attachment_name(filename)
        items = self.page.locator(".qa-attachment-item")

        for i in range(items.count()):
            title = items.nth(i).locator(".qa-title")
            if title.count() == 0:
                continue

            existing = title.first.inner_text().strip().lower()
            if target == existing:
                return True

        return False

    def duplicate_attachment_count(self, filename: str) -> int:
        target = self._attachment_name(filename)
        items = self.page.locator(".qa-attachment-item")
        matches = 0

        for i in range(items.count()):
            title = items.nth(i).locator(".qa-title")
            if title.count() and title.first.inner_text().strip().lower() == target:
                matches += 1

        return matches

    def cleanup_duplicate_attachments(self, filename: str, dry_run: bool = True) -> int:
        """Keep the first matching attachment and remove later exact-title duplicates.

        Deletion is intentionally scoped to the matching .qa-attachment-item and its
        button.qa-file-delete. dry_run defaults to True so this can be verified on a
        known customer before destructive cleanup is enabled.
        """
        target = self._attachment_name(filename)
        removed = 0

        while True:
            items = self.page.locator(".qa-attachment-item")
            matching_indexes = []

            for i in range(items.count()):
                item = items.nth(i)
                title = item.locator(".qa-title")
                if title.count() and title.first.inner_text().strip().lower() == target:
                    matching_indexes.append(i)

            if len(matching_indexes) <= 1:
                return removed

            print(f"Duplicate attachment '{target}': {len(matching_indexes)} copies found")

            if dry_run:
                print(f"DRY RUN: would delete {len(matching_indexes) - 1} duplicate copy/copies")
                return len(matching_indexes) - 1

            # Delete from the end so the first matching item is always preserved.
            duplicate_index = matching_indexes[-1]
            duplicate_item = items.nth(duplicate_index)
            delete_button = duplicate_item.locator("button.qa-file-delete")

            if delete_button.count() == 0:
                raise RuntimeError(
                    f"Duplicate '{target}' found but its qa-file-delete button is missing"
                )

            before = len(matching_indexes)
            delete_button.first.click()
            self.page.wait_for_timeout(750)

            # ServiceTitan may require a confirmation dialog depending on tenant/UI.
            confirm = self.page.locator(
                'button:visible:has-text("Delete"), button:visible:has-text("Yes")'
            )
            if confirm.count():
                try:
                    confirm.last.click(timeout=1500)
                    self.page.wait_for_timeout(750)
                except Exception:
                    pass

            after = self.duplicate_attachment_count(filename)
            if after >= before:
                raise RuntimeError(
                    f"Delete was clicked for '{target}', but attachment count did not decrease"
                )

            removed += 1

    def attachment_count(self) -> int:

        try:
            return self.page.locator(".qa-attachment-item").count()
        except Exception:
            return 0

    def wait_for_new_attachment(self, filename: str, timeout: int = 30000):

        end = self.page.evaluate("Date.now()") + timeout

        while self.page.evaluate("Date.now()") < end:
            self.page.reload(wait_until="domcontentloaded")
            self.page.wait_for_timeout(1500)

            if self.attachment_exists(filename):
                print("Attachment found.")
                return True

            self.page.wait_for_timeout(1000)

        return False

    def _upload_files(self, upload_selector: str, files, check_duplicates=True):

        uploaded = []
        skipped = []
        failed = []

        for file in files:

            try:
                from cancel import cancel

                if cancel.is_cancelled():
                    print("Upload cancelled.")
                    break

                file_path = str(Path(file).resolve())
                upload = self.page.locator(upload_selector)

                print(self.page.url)
                print(self.page.title())

                if upload.count() == 0:
                    print("Upload input not found. Refreshing page...")
                    self.page.reload(wait_until="domcontentloaded")
                    self.page.wait_for_timeout(3000)
                    upload = self.page.locator(upload_selector)

                    if upload.count() == 0:
                        print("Upload input still not found.")
                        failed.append(file)
                        self.move_to_failed(file, "Upload failed")
                        continue

                print("Upload input found.")

                if check_duplicates and self.attachment_exists(file.name):
                    print(f"Skipping existing file: {file.name}")
                    skipped.append(file)
                    continue

                print(f"\nUploading:\n{file_path}")
                success = False

                for attempt in range(2):
                    try:
                        if attempt:
                            print("Retrying upload...")

                        if not upload.is_enabled():
                            print("Upload input is disabled.")
                            break

                        print("Uploading...")

                        with self.page.expect_response(
                            lambda r: ("AddAttachment" in r.url and r.ok),
                            timeout=30000
                        ) as response_info:
                            upload.set_input_files(file_path)

                        response = response_info.value
                        print(f"Upload response: {response.status} {response.url}")

                        try:
                            print(response.text()[:500])
                        except Exception:
                            pass

                        print("Upload complete.")
                        uploaded.append(file)
                        success = True
                        break

                    except Exception as e:
                        print("=" * 60)
                        print("UPLOAD ERROR")
                        print(file.name)
                        print(type(e).__name__)
                        print(e)
                        print("Current URL:", self.page.url)
                        print("=" * 60)

                    self.page.wait_for_timeout(2000)

                if not success:
                    failed.append(file)
                    self.move_to_failed(file, "Upload Failed")
                    print(f"FAILED: {file.name}")
                    print("Current page:", self.page.url)

            except Exception as e:
                print()
                print("=" * 60)
                print("UPLOAD FAILED")
                print(file)
                print(e)
                print("=" * 60)
                failed.append(file)
                self.move_to_failed(file, "Upload Failed")
                continue

        return uploaded, skipped, failed

    def upload_to_job(self, files):
        print("Locating job upload input...")
        return self._upload_files(
            "#job-upload-attachment-btn input[type=file]",
            files,
            check_duplicates=True
        )

    def upload_to_customer(self, files):
        print("Locating customer upload input...")
        return self._upload_files(
            '[data-tracking-id="crm-customer-add-attachment-button"] + input[type=file]',
            files,
            check_duplicates=False
        )

    def move_to_failed(self, file, reason):
        try:
            source = Path(str(file))
            failed_path = Path(
                str(source).replace("sera_media", f"failed_media/{reason}")
            )
            failed_path.parent.mkdir(parents=True, exist_ok=True)

            if not source.exists():
                print(f"Source file missing: {source}")
                return

            shutil.move(str(source), str(failed_path))
            print(f"Moved to {failed_path}")

        except Exception as e:
            print(f"Failed to move {file}: {e}")