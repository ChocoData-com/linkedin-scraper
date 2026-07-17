"""
Free LinkedIn scraper - no API, no key, no cost.

LinkedIn renders its logged-out job search through a guest endpoint that returns plain
HTML job cards, so when a request gets through you can extract job listings without a
headless browser, a login, or JavaScript rendering.

    pip install requests
    python free_scraper/linkedin_free_scraper.py "python developer" "United States"

Fetches the guest job-search endpoint with plain requests and parses what comes back.
Run against linkedin.com on 2026-07-16 from a clean residential IP it returned 10 job
cards on 20 of 20 sequential attempts. What it will not do is scale: 40 calls at 8
concurrent from the same IP produced 8 x HTTP 429. See "Avoid getting blocked when
scraping LinkedIn" in the README for the full measurement.

Note before you point it at anything: LinkedIn's robots.txt disallows /jobs-guest/, the
path this script calls. That is your call to make, and you should make it knowingly.

It parses FIRST and only reports a block when the job cards are genuinely absent, so it
does not false-positive on anti-bot strings that appear in normal page JavaScript. When
it is blocked it says why, instead of silently returning an empty list.
"""
import json
import re
import sys

import requests

GUEST = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

# These are here to be a polite, realistic client, not because they unlock anything.
# Measured 2026-07-16: the guest endpoint served 10 job cards to a bare
# "python-requests/2.31.0" UA and to "curl/8.4.0" just as happily as to a browser UA.
# The User-Agent is not what gates this endpoint. Request volume is.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Only treat these as a block if no job cards parsed out. Scoped to the top of the
# document so page JavaScript cannot false-positive the check.
BLOCK_MARKERS = ("authwall", "checkpoint/challenge", "Sign in to continue",
                 "captcha", "Join LinkedIn")


def extract_jobs(html: str) -> list[dict]:
    """Pull job cards out of the guest job-search HTML fragment."""
    out = []
    for card in re.split(r'<li>\s*(?=<div[^>]*base-card)', html):
        jid = re.search(r'data-entity-urn="urn:li:jobPosting:(\d+)"', card)
        if not jid:
            continue
        title = re.search(r'<h3[^>]*base-search-card__title[^>]*>(.*?)</h3>', card, re.S)
        company = re.search(r'<h4[^>]*base-search-card__subtitle[^>]*>.*?<a[^>]*>(.*?)</a>', card, re.S)
        loc = re.search(r'<span[^>]*job-search-card__location[^>]*>(.*?)</span>', card, re.S)
        date = re.search(r'<time[^>]*datetime="([^"]+)"', card)
        url = re.search(r'<a[^>]*base-card__full-link[^>]*href="([^"?]+)', card)

        def clean(m):
            return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else None

        out.append({
            "job_id": jid.group(1),
            "title": clean(title),
            "company": clean(company),
            "location": clean(loc),
            "posted_date": date.group(1) if date else None,
            "url": url.group(1) if url else None,
        })
    return out


def scrape(keywords: str, location: str = "United States", start: int = 0) -> list[dict]:
    r = requests.get(
        GUEST,
        params={"keywords": keywords, "location": location, "start": start},
        headers=HEADERS,
        timeout=30,
    )

    if r.status_code != 200:
        raise SystemExit(
            f"BLOCKED: HTTP {r.status_code}. LinkedIn refused the request outright.\n"
            f"429 means rate-limited, 999 is LinkedIn's own anti-bot status code.\n"
            f"This is the normal outcome from a datacenter/cloud IP. See the README:\n"
            f"  https://github.com/ChocoData-com/linkedin-scraper#avoid-getting-blocked-when-scraping-linkedin"
        )

    # Parse FIRST. If cards are there, it worked, whatever strings live in the markup.
    jobs = extract_jobs(r.text)
    if jobs:
        return jobs

    # No cards. NOW decide: bot wall, or markup change?
    head = r.text[:4096].lower()
    if any(m.lower() in head for m in BLOCK_MARKERS):
        raise SystemExit(
            "BLOCKED: got the LinkedIn auth wall / challenge instead of job cards (HTTP 200).\n"
            "A 200 does not mean success. Check for the wall before parsing.\n"
            "  https://github.com/ChocoData-com/linkedin-scraper#avoid-getting-blocked-when-scraping-linkedin"
        )

    raise SystemExit(
        f"No job cards and no block marker. LinkedIn changed the guest markup, or this\n"
        f"query genuinely has no results (got {len(r.text)} bytes).\n"
        f"Update extract_jobs(). This is the maintenance tax the README quantifies."
    )


if __name__ == "__main__":
    kw = sys.argv[1] if len(sys.argv) > 1 else "python developer"
    loc = sys.argv[2] if len(sys.argv) > 2 else "United States"
    items = scrape(kw, loc)
    print(json.dumps(items[:3], indent=2))
    print(f"\n{len(items)} jobs for '{kw}' in '{loc}' (showing 3)")
