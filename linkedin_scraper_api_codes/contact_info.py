"""
LinkedIn Contact Info - Chocodata LinkedIn Scraper API

Public contact fields for a company or member page.

Read this before you build on it: `email` is null on essentially every LinkedIn page.
Member emails live behind the logged-in "Contact info" modal and are not part of the
public page, so no public scrape returns them and this endpoint does not pretend to.
What it does reliably return is a company's external `website`. The API says so itself
in the `note` field, which is printed verbatim below.

    pip install requests
    export CHOCODATA_API_KEY="your_key"      # free: 1,000 requests, one-time
    python linkedin_scraper_api_codes/contact_info.py https://www.linkedin.com/company/microsoft

Docs: https://chocodata.com/docs
"""
import json
import os
import sys

import requests

API = "https://api.chocodata.com/api/v1/linkedin/email"
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


def contact_info(url: str) -> dict:
    """Fetch the public contact fields for a LinkedIn company or member URL."""
    r = requests.get(API, params={"api_key": KEY, "url": url}, timeout=90)
    _check(r)
    return r.json()


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.linkedin.com/company/microsoft"
    data = contact_info(url)
    print(json.dumps(data, indent=2))
    print()
    kind = "company" if data["is_company"] else "member"
    print(f"{kind} page | website: {data['website']} | email: {data['email']} | phone: {data['phone']}")
