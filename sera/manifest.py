from pathlib import Path
import json
import pandas as pd

from sqlalchemy.orm import Session

from database.models import Customer

from config.settings import MANIFEST_FOLDER


def build_manifest(db: Session):

    rows = []

    customers = db.query(Customer).all()

    for customer in customers:

        for job in customer.jobs:

            for media in job.media:

                rows.append({

                    "Customer Name": customer.name,
                    "Sera Customer ID": customer.sera_id,
                    "ServiceTitan ID": customer.servicetitan_id,

                    "Sera Job": job.sera_job_number,
                    "ServiceTitan Job": job.servicetitan_job_number,

                    "Filename": media.filename,
                    "Original Filename": media.original_filename,

                    "Quote": media.quote_number,
                    "Invoice": media.invoice_number,

                    "Date": media.file_date,

                    "Downloaded": media.downloaded,
                    "Uploaded": media.uploaded,
                    "Verified": media.verified,

                    "Path": media.local_path

                })

    df = pd.DataFrame(rows)

    MANIFEST_FOLDER.mkdir(exist_ok=True)

    csv_file = MANIFEST_FOLDER / "migration_manifest.csv"
    excel_file = MANIFEST_FOLDER / "migration_manifest.xlsx"
    json_file = MANIFEST_FOLDER / "migration_manifest.json"

    df.to_csv(csv_file, index=False)

    df.to_excel(excel_file, index=False)

    with open(json_file, "w", encoding="utf8") as f:
        json.dump(rows, f, indent=4)

    return csv_file, excel_file, json_file