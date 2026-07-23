from servicetitan.browser import connect
from servicetitan.customer_search import CustomerSearcher
from servicetitan.job_search import JobSearcher
from servicetitan.uploader import Uploader


print("Connecting to Edge...")

p, browser, context = connect()

try:

    page = context.pages[0]

    print("Connected!")
    print(page.url)

    CustomerSearcher(page).open_customer("843598")
    JobSearcher(page).open_job("1100786")

    Uploader(page).upload(
        r"C:\Users\melis\sera-migration\sera_media\Customer_843598\Job_1100786\invoice_1040003_signed_2022-02-17.pdf"
    )

    input("\nPress ENTER...")

finally:

    browser.close()

    p.stop()