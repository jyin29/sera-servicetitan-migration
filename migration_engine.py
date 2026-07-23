from sera.media_inventory import MediaInventory
from database.customer_lookup import CustomerLookup
from pathlib import Path


class MigrationEngine:

    def __init__(self):

        self.inventory = MediaInventory(
            "sera_media"
        )

        self.lookup = CustomerLookup(
            Path("exports") / "ServiceTitanJobsExport.xlsx"
        )

    def run(self):

        customers = self.inventory.load()

        print("=" * 60)
        print("Migration")
        print("=" * 60)

        for customer in customers:

            print()
            print(f"Customer {customer['legacy_id']}")

            matches = self.lookup.find(
                customer["legacy_id"]
            )

            if not matches:

                print("No ServiceTitan customer.")
                continue

            print(
                f"{len(matches)} matching jobs"
            )

            for job in customer["jobs"]:

                print()

                print(
                    f"Job {job['job_number']}"
                )

                found = False

                for st_job in matches:

                    if (
                        st_job["job_number"]
                        ==
                        job["job_number"]
                    ):

                        found = True

                        print(
                            "Matched ServiceTitan Job"
                        )

                        print(
                            st_job["customer_name"]
                        )

                        print(
                            f"{len(job['files'])} files"
                        )

                        break

                if not found:

                    print(
                        "No matching ServiceTitan job."
                    )