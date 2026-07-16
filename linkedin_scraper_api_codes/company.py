"""
LinkedIn Company - Chocodata LinkedIn Scraper API

Company profile by vanity slug: employee count, industry, headquarters, specialties.

    pip install requests
    export CHOCODATA_API_KEY="your_key"      # free: 1,000 requests, one-time
    python linkedin_scraper_api_codes/company.py microsoft

Docs: https://chocodata.com/docs
"""
import json
import os
import sys

import requests

API = "https://api.chocodata.com/api/v1/linkedin/company"
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


def company(slug: str) -> dict:
    """Fetch a LinkedIn company profile by its vanity slug (linkedin.com/company/<slug>)."""
    r = requests.get(API, params={"api_key": KEY, "company": slug}, timeout=90)
    _check(r)
    return r.json()


if __name__ == "__main__":
    slug = sys.argv[1] if len(sys.argv) > 1 else "microsoft"
    data = company(slug)
    print(json.dumps(data, indent=2)[:1400])
    print()
    print(f"{data['name']} | {data['industry']} | {data['headquarters']}")
    print(f"{data['employee_count']:,} employees on LinkedIn | {data['followers']:,} followers")
