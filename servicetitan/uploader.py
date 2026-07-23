from pathlib import Path
from playwright.sync_api import Page


class Uploader:

    def __init__(self, page: Page):
        self.page = page

    def upload_to_customer(self, files):

        print("Locating upload input...")

        upload = self.page.locator(
            '[data-tracking-id="crm-customer-add-attachment-button"] + input[type=file]'
        )

        print("Matching inputs:", upload.count())

        upload.wait_for(
            state="attached",
            timeout=10000
        )

        print("Upload input found.")

        for file in files:

            file_path = str(Path(file).resolve())

            print(f"\nUploading:\n{file_path}")

            upload.set_input_files(file_path)

            print("Waiting 3 seconds...")

            self.page.wait_for_timeout(3000)

        print("Finished uploading customer.")