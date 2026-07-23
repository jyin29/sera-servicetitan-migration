from pathlib import Path
import hashlib


def file_hash(path: Path):

    h = hashlib.sha256()

    with open(path, "rb") as f:

        while True:

            chunk = f.read(65536)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


class MediaInventory:

    def __init__(self, media_root):

        self.media_root = Path(media_root)

    def load(self):

        customers = []

        if not self.media_root.exists():
            return customers

        for customer_folder in sorted(self.media_root.iterdir()):

            if not customer_folder.is_dir():
                continue

            customer = {
                "legacy_id": customer_folder.name.replace("Customer_", ""),
                "folder": customer_folder,
                "jobs": []
            }

            for job_folder in sorted(customer_folder.iterdir()):

                if not job_folder.is_dir():
                    continue

                seen_hashes = set()

                files = []

                for file in sorted(job_folder.iterdir()):

                    if not file.is_file():
                        continue

                    h = file_hash(file)

                    if h in seen_hashes:

                        print(
                            f"Duplicate skipped: {file.name}"
                        )

                        continue

                    seen_hashes.add(h)

                    files.append(file)

                customer["jobs"].append({

                    "job_number":
                        job_folder.name.replace("Job_", ""),

                    "folder":
                        job_folder,

                    "files":
                        files

                })

            customers.append(customer)

        return customers