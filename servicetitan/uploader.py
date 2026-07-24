from pathlib import Path
from playwright.sync_api import Page


class Uploader:

    def __init__(self, page: Page):
        self.page = page

    def attachment_exists(self, filename: str) -> bool:

        try:

            titles = self.page.locator(
                ".qa-attachments-table-column-Title"
            )

            target = filename.lower()

            for i in range(titles.count()):

                existing = titles.nth(i).inner_text().strip().lower()

                if existing == target:
                    return True

        except Exception:
            return False

        return False

    def attachment_count(self) -> int:

        try:
            return self.page.locator(
                ".qa-attachments-table-row"
            ).count()

        except Exception:
            return 0

    def wait_for_new_attachment(
        self,
        previous_count: int,
        timeout: int = 30000
    ) -> bool:

        end_time = self.page.evaluate("Date.now()") + timeout

        while self.page.evaluate("Date.now()") < end_time:

            if self.attachment_count() > previous_count:
                return True

            self.page.wait_for_timeout(500)

        return False

    def _upload_files(self, upload_selector: str, files):

        uploaded = []
        skipped = []
        failed = []

        for file in files:

            #
            # Recreate upload input every upload.
            #
            upload = self.page.locator(upload_selector)

            upload.wait_for(
                state="attached",
                timeout=10000
            )

            print("Upload input found.")

            if self.attachment_exists(file.name):

                print(f"Skipping existing file: {file.name}")

                skipped.append(file)

                continue

            file_path = str(Path(file).resolve())

            print(f"\nUploading:\n{file_path}")

            success = False

            for attempt in range(2):

                try:

                    if attempt:
                        print("Retrying upload...")

                    before = self.attachment_count()

                    if not upload.is_enabled():
                        raise Exception(
                            "Upload input is disabled."
                        )

                    upload.set_input_files(file_path)

                    print("Waiting for upload...")

                    if self.wait_for_new_attachment(before):

                        url = self.page.url.lower()

                        if (
                            "job" not in url
                            and
                            "customer" not in url
                        ):
                            raise Exception(
                                f"Unexpected page: {self.page.url}"
                            )

                        print("Upload complete.")

                        uploaded.append(file)

                        success = True

                        break

                    print("Upload timed out.")

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

                print(f"FAILED: {file.name}")

                print("Current page:", self.page.url)

        return uploaded, skipped, failed

    def upload_to_job(self, files):

        print("Locating job upload input...")

        return self._upload_files(
            "#job-upload-attachment-btn input[type=file]",
            files
        )

    def upload_to_customer(self, files):

        print("Locating customer upload input...")

        return self._upload_files(
            '[data-tracking-id="crm-customer-add-attachment-button"] + input[type=file]',
            files
        )