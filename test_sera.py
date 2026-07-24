from live_migration import LiveMigration
from playwright.sync_api import sync_playwright
from pathlib import Path
from openpyxl import load_workbook
from resume_tracker import ResumeTracker
import csv
import time
import re


print("Starting test_sera...")


# ============================================================
# SETTINGS
# ============================================================

EXCEL_FILE = Path("exports") / "CustomerContactReport-2026-07-22-58a68e.xlsx"

BASE_URL = "https://grmetro.sera.tech/customers"

DOWNLOAD_FOLDER = Path("sera_media")

DOWNLOAD_FOLDER.mkdir(exist_ok=True)

UPLOADED_FOLDER = Path("uploaded_media")

UPLOADED_FOLDER.mkdir(exist_ok=True)

LOG_FILE = Path("download_log.csv")

# TEST FIRST
#TEST_MODE = True

#TEST_CUSTOMER_COUNT = 1

RUNTIME_EXCEL_FILE = None

GUI = None


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clean_filename(filename):

    if not filename:
        return None

    filename = str(filename).strip()

    filename = re.sub(
        r'[<>:"/\\|?*]',
        '-',
        filename
    )

    filename = filename.rstrip(" .")

    return filename


def get_extension(content_type):

    if not content_type:
        return ""

    content_type = content_type.split(";")[0].strip()

    extensions = {

        "image/jpeg": ".jpg",

        "image/jpg": ".jpg",

        "image/png": ".png",

        "image/gif": ".gif",

        "image/webp": ".webp",

        "application/pdf": ".pdf",

        "application/msword": ".doc",

        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",

        "application/vnd.ms-excel": ".xls",

        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",

    }

    return extensions.get(content_type, "")


def get_job_number(image):

    """
    Finds the Job # associated with this media item.
    """

    # Start with the image's nearest reasonable container.
    # We walk upward through parent elements and look for text
    # containing "Job #".
    for level in range(1, 7):

        try:

            container = image.locator(
                ".." * level
            )

            text = container.inner_text(
                timeout=1000
            )

            match = re.search(
                r'Job\s*#\s*(\d+)',
                text,
                re.IGNORECASE
            )

            if match:

                return match.group(1)

        except:

            pass


    # If no job number is found, place it in an
    # Unassigned folder instead of guessing.

    return "Unassigned"


def initialize_log():

    if not LOG_FILE.exists():

        with open(
            LOG_FILE,
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.writer(file)

            writer.writerow([

                "customer_id",

                "job_number",

                "filename",

                "saved_path",

                "status",

                "error"

            ])


def write_log(
    customer_id,
    job_number,
    filename,
    saved_path,
    status,
    error=""
):

    with open(
        LOG_FILE,
        "a",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        writer.writerow([

            customer_id,

            job_number,

            filename,

            saved_path,

            status,

            error

        ])


# ============================================================
# READ SERA CUSTOMER IDS
# ============================================================

def run(
    workbook=None,
    limit=0
):
    completed = False

    print("Entered run()")

    global RUNTIME_EXCEL_FILE

    RUNTIME_EXCEL_FILE = workbook

    print("Reading customer list...")

    print("Workbook:", RUNTIME_EXCEL_FILE or EXCEL_FILE)

    #from pathlib import Path

    print("Absolute:", Path(RUNTIME_EXCEL_FILE or EXCEL_FILE).resolve())

    print("Exists:", Path(RUNTIME_EXCEL_FILE or EXCEL_FILE).exists())

    workbook = load_workbook(

        RUNTIME_EXCEL_FILE or EXCEL_FILE,

        read_only=True

    )

    sheet = workbook.active

    customer_ids = []

    tracker = ResumeTracker()

    last_customer = tracker.load()

    if last_customer:

        print(
            f"Resuming after customer "
            f"{last_customer}"
        )

    resume = last_customer is None

    skip_current = last_customer is not None

    # Column A = Id

    for row in sheet.iter_rows(

        min_row=2,

        max_col=1,

        values_only=True

    ):

        customer_id = row[0]

        if customer_id:

            customer_ids.append(
                str(customer_id).strip()
            )


    print(
        f"Found {len(customer_ids)} customers."
    )


    if limit > 0:

        customer_ids = customer_ids[:limit]

        print(
            f"TEST MODE: Processing "
            f"{len(customer_ids)} customers."
        )

    else:

        print(
            f"FULL MODE: Processing "
            f"{len(customer_ids)} customers."
        )


    initialize_log()


    # ============================================================
    # OPEN SERA
    # ============================================================

    with sync_playwright() as p:

        context = p.chromium.launch_persistent_context(

            "sera_browser_profile",

            headless=False

        )


        page = (

            context.pages[0]

            if context.pages

            else context.new_page()

        )


        # ========================================================
        # PROCESS CUSTOMERS
        # ========================================================

        migration = LiveMigration(p)

        print("Connected to Sera")

        for customer_number, customer_id in enumerate(

            customer_ids,

            start=1

        ):
            if GUI is not None:
                GUI.set_progress(
                    customer_number,
                    len(customer_ids)
                )

            #
            # Resume support
            #
            if not resume:

                if str(customer_id) == last_customer:
                    resume = True

                continue

            #
            # Skip the customer we already completed
            #

            if skip_current:

                skip_current = False

                continue

            print("\n" + "=" * 60)

            print(

                f"[{customer_number}/"
                f"{len(customer_ids)}] "
                f"Customer {customer_id}"

            )

            print("=" * 60)


            customer_folder = (

                DOWNLOAD_FOLDER /

                f"Customer_{customer_id}"

            )

            customer_folder.mkdir(

                exist_ok=True

            )


            url = (

                f"{BASE_URL}/"

                f"{customer_id}"

                f"?tab=c_Media+and+Documents"

            )


            try:

                page.goto(

                    url,

                    wait_until="domcontentloaded",

                    timeout=60000

                )


                page.wait_for_timeout(1500)


                images = page.locator("img")


                image_count = images.count()


                print(

                    f"Found {image_count} "
                    f"image elements"

                )


                real_media_number = 0


                for image_number in range(image_count):

                    filename = ""


                    try:

                        image = images.nth(

                            image_number

                        )


                        filename = (

                            image.get_attribute(

                                "alt"

                            )

                        )


                        # Skip fake UI image

                        if (

                            filename

                            and

                            filename.strip().lower()

                            == "membership icon"

                        ):

                            print(

                                "  Skipping "
                                "Membership Icon"

                            )

                            continue


                        real_media_number += 1


                        # ------------------------------------------------
                        # FIND JOB NUMBER
                        # ------------------------------------------------

                        job_number = get_job_number(

                            image

                        )


                        print(

                            f"  Job: #{job_number}"

                        )


                        # ------------------------------------------------
                        # CREATE JOB FOLDER
                        # ------------------------------------------------

                        job_folder = (

                            customer_folder /

                            f"Job_{job_number}"

                        )


                        job_folder.mkdir(

                            exist_ok=True

                        )


                        # ------------------------------------------------
                        # OPEN MEDIA
                        # ------------------------------------------------

                        image.click()


                        page.wait_for_timeout(

                            700

                        )


                        download_link = (

                            page.get_by_role(

                                "link",

                                name="Download"

                            )

                        )


                        if (

                            download_link.count()

                            == 0

                        ):

                            print(

                                "  Could not find "
                                "Download link"

                            )


                            write_log(

                                customer_id,

                                job_number,

                                filename,

                                "",

                                "Skipped",

                                "Download link not found"

                            )


                            page.keyboard.press(

                                "Escape"

                            )


                            continue


                        href = (

                            download_link

                            .first

                            .get_attribute(

                                "href"

                            )

                        )


                        if not href:

                            print(

                                "  Download link had "
                                "no URL"

                            )

                            continue


                        # ------------------------------------------------
                        # DOWNLOAD FILE
                        # ------------------------------------------------

                        response = (

                            page.request.get(

                                href,

                                timeout=60000

                            )

                        )


                        if response.status != 200:

                            print(

                                f"  Download failed: "
                                f"HTTP {response.status}"

                            )

                            write_log(

                                customer_id,

                                job_number,

                                filename,

                                "",

                                "Failed",

                                f"HTTP {response.status}"

                            )

                            continue


                        # ------------------------------------------------
                        # FILENAME
                        # ------------------------------------------------

                        filename = clean_filename(

                            filename

                        )


                        if not filename:

                            filename = (

                                f"media_"

                                f"{real_media_number}"

                            )


                        # Add extension if needed

                        if not Path(

                            filename

                        ).suffix:

                            extension = get_extension(

                                response.headers.get(

                                    "content-type",

                                    ""

                                )

                            )

                            filename += extension


                        # ------------------------------------------------
                        # SAVE FILE
                        # ------------------------------------------------

                        file_path = (

                            job_folder /

                            filename

                        )

                        uploaded_path = (
                            UPLOADED_FOLDER
                            / file_path.relative_to(DOWNLOAD_FOLDER)
                        )

                        #
                        # Already migrated?
                        #

                        if uploaded_path.exists():

                            print(f"✓ Already migrated: {filename}")

                            page.keyboard.press("Escape")

                            page.wait_for_timeout(400)

                            continue


                        # Avoid overwriting

                        #
                        # Already downloaded?
                        #
                        if file_path.exists():

                            print(f"Already downloaded: {filename}")

                            success = migration.migrate_file(
                                customer_id,
                                job_number,
                                file_path
                            )

                            if success:

                                destination = (
                                    UPLOADED_FOLDER
                                    / file_path.relative_to(DOWNLOAD_FOLDER)
                                )

                                destination.parent.mkdir(
                                    parents=True,
                                    exist_ok=True
                                )

                                file_path.rename(destination)

                                print(f"✓ Uploaded → {destination}")

                            else:

                                print("✗ Upload failed")

                            page.keyboard.press("Escape")

                            page.wait_for_timeout(400)

                            continue


                        file_path.write_bytes(

                            response.body()

                        )

                        success = migration.migrate_file(
                            customer_id,
                            job_number,
                            file_path
                        )

                        if success:

                            destination = (
                                UPLOADED_FOLDER
                                / file_path.relative_to(DOWNLOAD_FOLDER)
                            )

                            destination.parent.mkdir(
                                parents=True,
                                exist_ok=True
                            )

                            file_path.rename(destination)

                            print(f"✓ Uploaded → {destination}")

                        else:

                            print("✗ Upload failed")


                        print(

                            f"  SAVED: {file_path}"

                        )


                        write_log(

                            customer_id,

                            job_number,

                            filename,

                            str(file_path),

                            "Downloaded"

                        )


                        # Close viewer

                        page.keyboard.press(

                            "Escape"

                        )


                        page.wait_for_timeout(

                            400

                        )


                    except Exception as error:

                        print(

                            f"  ERROR: {error}"

                        )


                        write_log(

                            customer_id,

                            "Unknown",

                            filename,

                            "",

                            "Error",

                            str(error)

                        )


                        try:

                            page.keyboard.press(

                                "Escape"

                            )

                        except:

                            pass


                time.sleep(1)

                tracker.save(customer_id)

            except Exception as error:

                print(

                    f"ERROR processing customer "
                    f"{customer_id}: {error}"

                )

        completed = True

        print("\n" + "=" * 60)

        print("TEST COMPLETE")

        print("=" * 60)

        print(

            f"Files saved in: "

            f"{DOWNLOAD_FOLDER.absolute()}"

        )

        print(

            f"Log saved in: "

            f"{LOG_FILE.absolute()}"

        )

        if completed:
            tracker.clear()

        #migration.close()

        context.close()

if __name__ == "__main__":
    run()