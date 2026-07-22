from pathlib import Path

from playwright.sync_api import sync_playwright


class SeraDownloader:

    def __init__(
        self,
        excel_file,
        output_folder,
        logger,
        test_mode=False,
        test_limit=5,
    ):

        self.excel_file = Path(excel_file)

        self.output_folder = Path(output_folder)

        self.logger = logger

        self.test_mode = test_mode

        self.test_limit = test_limit

        self.playwright = None

        self.context = None

        self.page = None

    def log(self, text):

        print(text)

        if self.logger:
            self.logger(text)

    def start(self):

        self.playwright = sync_playwright().start()

        self.context = (
            self.playwright.chromium.launch_persistent_context(
                "sera_browser_profile",
                headless=False,
            )
        )

        if self.context.pages:
            self.page = self.context.pages[0]
        else:
            self.page = self.context.new_page()

    def stop(self):

        if self.context:
            self.context.close()

        if self.playwright:
            self.playwright.stop()

    def run(self):

        self.start()

        self.log("Browser started.")

        #
        # THIS IS WHERE YOUR EXISTING
        # test_sera.py LOGIC
        # IS GOING TO GO.
        #

        self.stop()

        self.log("Finished.")