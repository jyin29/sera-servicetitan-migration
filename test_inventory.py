from inventory import Inventory

inventory = Inventory()

jobs = inventory.build("sera_media")

print()

print(f"Found {len(jobs)} jobs")

print()

for job in jobs:
    print(
        f"Job {job.job_number} | "
        f"Legacy {job.legacy_id} | "
        f"{job.file_count} files"
    )