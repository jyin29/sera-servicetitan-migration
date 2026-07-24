from servicetitan.browser import connect
from servicetitan.job_search import JobSearcher
from servicetitan.customer_search import CustomerSearcher
from servicetitan.uploader import Uploader


class LiveMigration:

    def __init__(self):

        self.p, self.browser, self.context = connect()

        #
        # Find the ServiceTitan tab
        #
        self.page = None

        for page in self.context.pages:

            if "servicetitan" in page.url.lower():
                self.page = page
                break

        if self.page is None:
            raise Exception(
                "Could not find an open ServiceTitan tab."
            )

        self.job_search = JobSearcher(self.page)
        self.customer_search = CustomerSearcher(self.page)
        self.uploader = Uploader(self.page)

    def migrate_file(
        self,
        customer_id: str,
        job_number: str,
        file_path
    ):

        print("=" * 60)
        print(f"Migrating: {file_path.name}")

        for attempt in range(2):

            try:

                if attempt:
                    print("\nRetrying migration...")

                #
                # Try Job first
                #
                if job_number != "Unassigned":

                    if self.job_search.open_job(job_number):

                        print("Uploading to job...")

                        uploaded, skipped, failed = self.uploader.upload_to_job([file_path])

                        if uploaded:
                            print(f"✓ {file_path.name} → Job")
                            return True

                        if skipped:
                            print(f"✓ {file_path.name} already exists on Job")
                            return True

                        print("Upload to Job failed.")

                        if uploaded:

                            print(f"✓ {file_path.name} → Job")

                            return True

                        if skipped:

                            print(f"✓ {file_path.name} already exists on Job")

                            return True

                        print("Upload to Job failed.")

                #
                # Customer fallback
                #
                print("Trying customer...")

                if self.customer_search.open_customer(customer_id):

                    print("Uploading to customer...")

                    uploaded, skipped, failed = self.uploader.upload_to_customer([file_path])

                    if uploaded:
                        print(f"✓ {file_path.name} → Customer")
                        return True

                    if skipped:
                        print(f"✓ {file_path.name} already exists on Customer")
                        return True

                    print("Upload to Customer failed.")

                    if uploaded:

                        print(f"✓ {file_path.name} → Customer")

                        return True

                    if skipped:

                        print(f"✓ {file_path.name} already exists on Customer")

                        return True

                    print("Upload to Customer failed.")

            except Exception as e:

                print(f"Migration error: {e}")

            print("Attempt failed.\n")

        print("=" * 60)
        print("MIGRATION FAILED")
        print(f"Customer : {customer_id}")
        print(f"Job      : {job_number}")
        print(f"File     : {file_path.name}")
        print("=" * 60)

        return False