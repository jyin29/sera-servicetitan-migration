from pathlib import Path


class ServiceTitanUploader:

    def __init__(self, page):

        self.page = page

    def upload_job(self, job_number, files):

        print()
        print("=" * 60)
        print(f"Uploading Job {job_number}")
        print("=" * 60)

        print(f"{len(files)} files")

        for file in files:

            print("   ", Path(file).name)

        #
        # Search job
        #
        # (We'll implement this after your ST login works.)
        #

        #
        # Upload files
        #
        # (We'll implement this after the search works.)
        #

        print("Finished.")