def connect(playwright):

    browser = playwright.chromium.connect_over_cdp(
        "http://127.0.0.1:9222"
    )

    if not browser.contexts:
        raise Exception("No Edge contexts found.")

    return browser, browser.contexts[0]