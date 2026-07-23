from pathlib import Path
from playwright.sync_api import Page


class Uploader:

    def __init__(self, page: Page):
        self.page = page

    def upload(self, file_path):

        file_path = str(Path(file_path).resolve())

        print(f"\nUploading {file_path}")

        upload = self.page.locator(
            "#job-upload-attachment-btn input[type=file]"
        )

        upload.set_input_files(file_path)

        print("File selected.")

        # Give ServiceTitan time to upload
        self.page.wait_for_timeout(5000)

        print("Upload complete (hopefully 😄)")