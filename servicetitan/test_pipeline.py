from servicetitan.browser import connect
from servicetitan.customer_search import CustomerSearcher
from servicetitan.job_search import JobSearcher
from servicetitan.uploader import Uploader


FILE = r"C:\Users\melis\sera-migration\sera_media\Customer_843598\Job_1100786\invoice_1040003_signed_2022-02-17.pdf"


print("Connecting to Edge...")

p, browser, context = connect()

try:

    page = context.pages[0]

    print("Connected!")

    for customer in inventory:

        CustomerSearcher(page).open_customer(customer.legacy_id)

        for job in customer.jobs:

            JobSearcher(page).open_job(job.job_number)

            for file in job.files:

                Uploader(page).upload(file.path)

    input("\nFinished. Press ENTER.")

finally:

    browser.close()

    p.stop()