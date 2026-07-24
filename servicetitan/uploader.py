from pathlib import Path
from playwright.sync_api import Page


class Uploader:

    def __init__(self, page: Page):
        self.page = page

    def attachment_exists(self, filename: str) -> bool:

        titles = self.page.locator(".qa-title")

        #print(f"Found {titles.count()} attachment titles")

        target = Path(filename).stem.lower()

        for i in range(titles.count()):

            existing = (
                titles.nth(i)
                .inner_text()
                .strip()
                .lower()
            )

            #print(f"Existing: {existing}")

            if target in existing:
                return True

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
        filename: str,
        timeout: int = 30000
    ):

        end = self.page.evaluate("Date.now()") + timeout

        while self.page.evaluate("Date.now()") < end:

            #
            # Refresh the page so the attachment list updates.
            #
            self.page.reload(wait_until="domcontentloaded")

            self.page.wait_for_timeout(1500)

            if self.attachment_exists(filename):

                print("Attachment found.")

                return True

            self.page.wait_for_timeout(1000)

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

                    if not upload.is_enabled():
                        raise Exception(
                            "Upload input is disabled."
                        )

                    #
                    # Upload the file
                    #
                    print("Uploading...")

                    with self.page.expect_response(
                        lambda r: (
                            "AddAttachment" in r.url
                            and r.ok
                        ),
                        timeout=30000
                    ) as response_info:

                        upload.set_input_files(file_path)

                    response = response_info.value

                    print(f"Upload response: {response.status} {response.url}")

                    try:
                        print(response.text()[:500])
                    except:
                        pass

                    print(f"Upload response: {response.status}")

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