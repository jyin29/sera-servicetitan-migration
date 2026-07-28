class MigrationStats:

    def __init__(self):

        self.jobs = 0
        self.uploaded = 0
        self.skipped = 0
        self.failed = 0

    def job(self):

        self.jobs += 1

    def uploaded_files(self, count):

        self.uploaded += count

    def skipped_files(self, count):

        self.skipped += count

    def failed_files(self, count):

        self.failed += count

    def print_summary(self):

        print()
        print("=" * 70)
        print("Migration Summary")
        print("=" * 70)
        print(f"Jobs Processed : {self.jobs}")
        print(f"Uploaded Files : {self.uploaded}")
        print(f"Skipped Files  : {self.skipped}")
        print(f"Failed Files   : {self.failed}")
        print("=" * 70)