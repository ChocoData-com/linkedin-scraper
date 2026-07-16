"""
LinkedIn job monitor - a real, runnable use case on the Chocodata LinkedIn Scraper API.

Polls a LinkedIn job search, stores every posting it has ever seen in a local SQLite
dataset, and prints what is NEW since the previous run. Tracking new postings for a
keyword is the single most common reason people scrape LinkedIn (recruiting, hiring
intelligence, competitor headcount signals), so it is here end to end rather than as a
snippet.

    pip install requests
    export CHOCODATA_API_KEY="your_key"     # free key (1,000 requests, one-time): https://chocodata.com
    python linkedin_scraper_api_codes/job_monitor.py "python developer" "United States"
    # ... run it again later to see only what appeared since

Export the dataset to CSV whenever you want:
    sqlite3 -header -csv linkedin_jobs.db "SELECT * FROM postings;" > jobs.csv

Cost: 1 request (5 credits) per run per query, plus 1 per new job if you enrich (--enrich).
Docs: https://chocodata.com/docs
"""
import os
import sqlite3
import sys
import time

import requests

BASE = "https://api.chocodata.com/api/v1/linkedin"
KEY = os.environ.get("CHOCODATA_API_KEY")
DB = "linkedin_jobs.db"

if not KEY:
    sys.exit("Set CHOCODATA_API_KEY first. Free key: https://chocodata.com")


def _check(r) -> None:
    """Map the API's documented errors onto actionable messages instead of a traceback."""
    if r.status_code == 400:
        sys.exit(f"400 invalid_params: {r.text[:200]}")
    if r.status_code == 401:
        sys.exit("401 INVALID_API_KEY: key missing or not recognised. Get one: https://chocodata.com")
    if r.status_code == 402:
        sys.exit("402 INSUFFICIENT_CREDITS: balance exhausted. Top up or upgrade: https://chocodata.com/pricing")
    if r.status_code == 429:
        sys.exit("429 RATE_LIMITED: over your plan's concurrency. Back off and retry.")
    if r.status_code == 404:
        sys.exit(f"404 item_not_found: {r.json().get('message', 'does not exist')} (not retryable, not charged)")
    if r.status_code == 502:
        sys.exit("502 target_unreachable: LinkedIn refused every attempt for this request. Retryable, and you were not charged.")
    r.raise_for_status()


def fetch(keywords: str, location: str, start: int = 0) -> list[dict]:
    """One API call -> the current page of job listings for this query."""
    r = requests.get(f"{BASE}/jobsearch",
                     params={"api_key": KEY, "keywords": keywords, "location": location,
                             "start": start, "limit": 10},
                     timeout=90)
    _check(r)
    return r.json().get("results", [])


def enrich(job_id: str) -> dict:
    """Optional second call -> the full posting (seniority, employment type, description).

    A monitoring run should not die because one posting was closed or transiently
    unreachable, so those two cases skip the job instead of exiting. Everything else
    (bad key, no credits) still fails loudly via _check.
    """
    r = requests.get(f"{BASE}/job", params={"api_key": KEY, "job_id": job_id}, timeout=90)
    if r.status_code == 404:
        return {}          # posting closed between the search and the fetch. Normal.
    if r.status_code == 502:
        return {}          # documented as retryable and not charged. Skip it this run.
    _check(r)
    return r.json()


def setup(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS postings (
               job_id TEXT PRIMARY KEY, query TEXT, title TEXT, company TEXT,
               location TEXT, posted_date TEXT, url TEXT,
               seniority TEXT, employment_type TEXT,
               first_seen INTEGER
           )"""
    )


def main(keywords: str, location: str, pages: int = 2, do_enrich: bool = False) -> None:
    conn = sqlite3.connect(DB)
    setup(conn)
    now = int(time.time())

    seen_before = {r[0] for r in conn.execute("SELECT job_id FROM postings").fetchall()}
    listings = []
    for p in range(pages):
        listings += fetch(keywords, location, start=p * 10)

    new = [j for j in listings if j["job_id"] not in seen_before]

    for j in new:
        extra = enrich(j["job_id"]) if do_enrich else {}
        conn.execute(
            "INSERT OR REPLACE INTO postings VALUES (?,?,?,?,?,?,?,?,?,?)",
            (j["job_id"], keywords, j.get("title"), j.get("company"), j.get("location"),
             j.get("posted_date"), j.get("url"),
             extra.get("seniority"), extra.get("employment_type"), now),
        )
        line = f"NEW  {(j.get('title') or '')[:42]:42} {(j.get('company') or '')[:22]:22} {j.get('location') or ''}"
        if extra:
            line += f"  [{extra.get('seniority')} / {extra.get('employment_type')}]"
        print(line)

    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM postings").fetchone()[0]
    conn.close()

    print(f"\n{len(listings)} listings this run | {len(new)} new | {total} tracked in {DB}")
    if not new and seen_before:
        print("Nothing new since the last run. Schedule it (cron / GitHub Actions) and you have a feed.")
    elif not seen_before:
        print("First run, so everything is new: this seeded the database. Run it again later for the diff.")


if __name__ == "__main__":
    kw = sys.argv[1] if len(sys.argv) > 1 else "python developer"
    loc = sys.argv[2] if len(sys.argv) > 2 else "United States"
    main(kw, loc, do_enrich="--enrich" in sys.argv)
