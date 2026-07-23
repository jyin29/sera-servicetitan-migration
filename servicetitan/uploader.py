from pathlib import Path
from playwright.sync_api import Page


class Uploader:

    def __init__(self, page: Page):
        self.page = page

    def attachment_exists(self, filename: str) -> bool:

        titles = self.page.locator(
            ".qa-attachments-table-column-Title"
        )

        target = filename.lower()

        for i in range(titles.count()):

            existing = titles.nth(i).inner_text().strip().lower()

            if existing == target:
                return True

        return False

    def _upload_files(self, upload, files):

        upload.wait_for(
            state="attached",
            timeout=10000
        )

        print("Upload input found.")

        uploaded = []
        skipped = []

        for file in files:

            if self.attachment_exists(file.name):

                print(f"Skipping existing file: {file.name}")

                skipped.append(file)

                continue

            file_path = str(Path(file).resolve())

            print(f"\nUploading:\n{file_path}")

            upload.set_input_files(file_path)

            print("Waiting for upload...")

            self.page.wait_for_timeout(3000)

            uploaded.append(file)

        print("Finished uploading.")

        return uploaded, skipped

    def upload_to_job(self, files):

        print("Locating job upload input...")

        upload = self.page.locator(
            "#job-upload-attachment-btn input[type=file]"
        )

        print("Matching inputs:", upload.count())

        return self._upload_files(upload, files)

    def upload_to_customer(self, files):

        print("Locating customer upload input...")

        upload = self.page.locator(
            '[data-tracking-id="crm-customer-add-attachment-button"] + input[type=file]'
        )

        print("Matching inputs:", upload.count())

        return self._upload_files(upload, files)