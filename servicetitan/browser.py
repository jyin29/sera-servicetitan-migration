import shutil
import socket
import subprocess
import time
import os
from pathlib import Path


DEBUG_PORT = 9222
APP_DATA = Path(os.getenv("LOCALAPPDATA")) / "Sera ServiceTitan Migration"
APP_DATA.mkdir(parents=True, exist_ok=True)

PROFILE_DIR = str(APP_DATA / "app_profile")


def _port_open(port):

    try:

        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True

    except OSError:

        return False


def _launch_edge():

    candidates = [
        shutil.which("msedge"),
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ]

    edge = None

    for path in candidates:
        if path and shutil.os.path.exists(path):
            edge = path
            break

    if edge is None:
        raise FileNotFoundError(
            "Microsoft Edge could not be found."
        )

    print(f"Launching Edge from: {edge}")

    subprocess.Popen(
        [
            edge,
            f"--remote-debugging-port={DEBUG_PORT}",
            f"--user-data-dir={PROFILE_DIR}"
        ]
    )


def connect(playwright):

    if not _port_open(DEBUG_PORT):

        _launch_edge()

        timeout = time.time() + 20

        while time.time() < timeout:

            if _port_open(DEBUG_PORT):

                break

            time.sleep(0.5)

        else:

            raise Exception(
                "Edge failed to start."
            )

    browser = playwright.chromium.connect_over_cdp(
        f"http://127.0.0.1:{DEBUG_PORT}"
    )

    if browser.contexts:

        context = browser.contexts[0]

    else:

        context = browser.new_context()

    return browser, context

def wait_for_servicetitan(context, timeout=300):
    """
    Wait until a ServiceTitan tab is available.
    timeout is in seconds (default: 5 minutes).
    """

    end = time.time() + timeout

    while time.time() < end:

        for page in context.pages:

            url = page.url.lower()

            if (
                "servicetitan" in url
                or
                "st-app" in url
            ):
                return page

        time.sleep(1)

    raise TimeoutError(
        "Timed out waiting for a ServiceTitan tab."
    )

def ensure_servicetitan_tab(context):

    for page in context.pages:

        url = page.url.lower()

        if (
            "servicetitan" in url
            or
            "st-app" in url
        ):
            return page

    page = context.new_page()

    page.goto(
        "https://go.servicetitan.com/"
    )

    return page