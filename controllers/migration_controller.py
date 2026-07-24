from migration_engine import MigrationEngine


class MigrationController:

    def __init__(self):
        self.engine = MigrationEngine()

    def run(
        self,
        customer_limit=0,
        job_limit=0,
        download=True,
        upload=True,
    ):

        print("=" * 60)
        print("Migration Controller")
        print("=" * 60)

        #
        # Sera download
        #
        if download:

            print("Downloading from Sera...")

            # TODO:
            # call downloader here

        #
        # ServiceTitan upload
        #
        if upload:

            print("Uploading to ServiceTitan...")

            self.engine.run(
                limit=job_limit
            )

        print("Migration complete.")