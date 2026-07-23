from servicetitan.browser import launch
from servicetitan.customer_search import CustomerSearcher


print("Connecting to Edge...")

p, browser, context = launch()

print("connected!")

try:

    if context.pages:

        page = context.pages[0]

    else:

        page = context.new_page()

    print("Current URL:", page.url)

    if page.url == "about:blank":

        page.goto("https://go.servicetitan.com")

    input(
        "When you're on the ServiceTitan dashboard, press ENTER..."
    )

    CustomerSearcher(page).open_customer("843598")

    input("Press ENTER to exit...")

finally:

    browser.close()

    p.stop()