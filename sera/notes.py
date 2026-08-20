import re

SERA_JOB_URL = "https://grmetro.sera.tech/jobs/{job_id}"
SERA_RECYCLE_EVERY = 100
SERA_LOAD_RETRIES = 3
_load_count = 0


def get_or_open_sera_page(context):
    for page in context.pages:
        if "grmetro.sera.tech" in page.url.lower():
            return page
    return context.new_page()


def extract_customer(page):
    link = page.locator('a[data-cy="customer-header-link"]').first
    link.wait_for(state="visible", timeout=15000)
    href = (link.get_attribute("href") or "").strip()
    name = link.inner_text().strip()
    match = re.search(r"/customers/(\d+)", href)
    if not match:
        raise RuntimeError(f"Could not extract Sera customer ID from href: {href!r}")
    return {"sera_customer_id": match.group(1), "customer_name": name, "href": href}


def expand_all_comments(page):
    for _ in range(20):
        buttons = page.get_by_text(re.compile(r"^\s*see more\s*$", re.I), exact=False)
        visible = []
        for i in range(buttons.count()):
            item = buttons.nth(i)
            try:
                if item.is_visible(): visible.append(item)
            except Exception:
                pass
        if not visible: return
        clicked = 0
        for item in reversed(visible):
            try:
                item.scroll_into_view_if_needed(); item.click(timeout=3000); clicked += 1; page.wait_for_timeout(100)
            except Exception:
                pass
        if clicked == 0:
            raise RuntimeError("Sera has visible 'See more' comment controls but none could be expanded")
    remaining = page.get_by_text(re.compile(r"^\s*see more\s*$", re.I), exact=False)
    for i in range(remaining.count()):
        try:
            if remaining.nth(i).is_visible():
                raise RuntimeError("Sera comments still contain visible 'See more' controls after expansion")
        except RuntimeError:
            raise
        except Exception:
            pass


def extract_comments(page):
    expand_all_comments(page)
    comments = []
    groups = page.locator(".comment-group")
    for group_index in range(groups.count()):
        group = groups.nth(group_index)
        date_parts = group.locator(".comment-group-timestamp span")
        date_text = " ".join(date_parts.nth(i).inner_text().strip() for i in range(date_parts.count()) if date_parts.nth(i).inner_text().strip())
        group_comments = group.locator(".comment")
        for comment_index in range(group_comments.count()):
            comment = group_comments.nth(comment_index)
            content = comment.locator(".comment-content span")
            text = content.first.inner_text().strip() if content.count() else ""
            if not text: continue
            author_el = comment.locator(".comment-header b")
            author = author_el.first.inner_text().strip() if author_el.count() else ""
            time_el = comment.locator(".comment-header .timestamp")
            time_text = time_el.first.inner_text().strip() if time_el.count() else ""
            timestamp_title = time_el.first.get_attribute("data-tippy-content") if time_el.count() else ""
            comments.append({"date": date_text, "time": time_text, "timestamp": timestamp_title or "", "author": author, "text": text})
    return comments


def _hard_reset_sera_page(page):
    """Unload the Sera SPA so accumulated frontend state is discarded while keeping the browser login session."""
    print("Recycling Sera frontend (100-job preventative reset)...")
    try:
        page.goto("about:blank", wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(500)
    except Exception as exc:
        print(f"Sera reset warning: {exc}")


def load_job_data(page, job_id):
    global _load_count
    _load_count += 1

    # Sera has been observed to become unstable after ~150 navigations. Unload the
    # entire SPA every 100 jobs before navigating to the next job, preserving cookies/session.
    if _load_count > 1 and (_load_count - 1) % SERA_RECYCLE_EVERY == 0:
        _hard_reset_sera_page(page)

    last_error = None
    for attempt in range(1, SERA_LOAD_RETRIES + 1):
        try:
            page.goto(SERA_JOB_URL.format(job_id=job_id), wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2500)
            customer = extract_customer(page)
            comments = extract_comments(page)
            return {"job_id": str(job_id), **customer, "comments": comments}
        except Exception as exc:
            last_error = exc
            print(f"Sera load failed for job {job_id} ({attempt}/{SERA_LOAD_RETRIES}): {exc}")
            if attempt < SERA_LOAD_RETRIES:
                print(f"Resetting Sera frontend and retrying SAME job {job_id}...")
                _hard_reset_sera_page(page)
                page.wait_for_timeout(1000)

    raise RuntimeError(f"Sera failed to load job {job_id} after {SERA_LOAD_RETRIES} fresh attempts: {last_error}")


def load_job_comments(page, job_id):
    return load_job_data(page, job_id)["comments"]
