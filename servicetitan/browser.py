from playwright.sync_api import sync_playwright


def launch():

    p = sync_playwright().start()

    browser = p.chromium.connect_over_cdp(
        "http://127.0.0.1:9222"
    )

    context = browser.contexts[0]

    return p, browser, context        