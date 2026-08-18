SERA_JOB_URL = "https://grmetro.sera.tech/jobs/{job_id}"


def get_or_open_sera_page(context):
    for page in context.pages:
        if "grmetro.sera.tech" in page.url.lower():
            return page
    return context.new_page()


def extract_comments(page):
    comments = []
    groups = page.locator(".comment-group")

    for group_index in range(groups.count()):
        group = groups.nth(group_index)

        date_parts = group.locator(".comment-group-timestamp span")
        date_text = " ".join(
            date_parts.nth(i).inner_text().strip()
            for i in range(date_parts.count())
            if date_parts.nth(i).inner_text().strip()
        )

        group_comments = group.locator(".comment")
        for comment_index in range(group_comments.count()):
            comment = group_comments.nth(comment_index)

            content = comment.locator(".comment-content span")
            text = content.first.inner_text().strip() if content.count() else ""
            if not text:
                continue

            author_el = comment.locator(".comment-header b")
            author = author_el.first.inner_text().strip() if author_el.count() else ""

            time_el = comment.locator(".comment-header .timestamp")
            time_text = time_el.first.inner_text().strip() if time_el.count() else ""
            timestamp_title = (
                time_el.first.get_attribute("data-tippy-content")
                if time_el.count()
                else ""
            )

            comments.append(
                {
                    "date": date_text,
                    "time": time_text,
                    "timestamp": timestamp_title or "",
                    "author": author,
                    "text": text,
                }
            )

    return comments


def load_job_comments(page, job_id):
    page.goto(SERA_JOB_URL.format(job_id=job_id), wait_until="domcontentloaded")
    page.wait_for_timeout(2500)

    try:
        page.locator(".comment-group").first.wait_for(state="visible", timeout=15000)
    except Exception:
        return []

    return extract_comments(page)
