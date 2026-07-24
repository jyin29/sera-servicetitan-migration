from pathlib import Path

from models import SeraMedia


class SeraDownloader:

    def __init__(self, download_folder):

        self.download_folder = Path(download_folder)

    def download(self, media: SeraMedia):

        """
        Downloads ONE file.

        Returns the updated media object.
        """

        #
        # We'll put your existing Playwright
        # download logic here next.
        #

        return media