"""
LinkedIn Job Search - Chocodata LinkedIn Scraper API

Runnable example. It calls the LIVE API and prints the real JSON response.

    pip install requests
    export CHOCODATA_API_KEY="your_key"      # free: 1,000 requests, one-time
    python linkedin_scraper_api_codes/jobsearch.py

Docs: https://chocodata.com/docs
"""
import json
import os
import sys

import requests

API = "https://api.chocodata.com/api/v1/linkedin/jobsearch"
KEY = os.environ.get("CHOCODATA_API_KEY")

if not KEY:
    sys.exit("Set CHOCODATA_API_KEY first. Free key (1,000 requests, one-time): https://chocodata.com")


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


def job_search(keywords: str, location: str = "United States", start: int = 0,
               limit: int = 10) -> dict:
    """Search LinkedIn job listings and return them as structured JSON."""
    params = {"api_key": KEY, "keywords": keywords, "location": location,
              "start": start, "limit": limit}
    r = requests.get(API, params=params, timeout=90)
    _check(r)
    return r.json()


if __name__ == "__main__":
    data = job_search("python developer", "United States")
    print(json.dumps(data, indent=2)[:1800])
    print()
    top = data["results"][0]
    print(f"{len(data['results'])} jobs | #1: {top['title']} at {top['company']} "
          f"({top['location']}, posted {top['posted_date']})")
