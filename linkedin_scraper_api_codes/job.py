"""
LinkedIn Job - Chocodata LinkedIn Scraper API

Full job posting by job_id: description, seniority, employment type, job function.

    pip install requests
    export CHOCODATA_API_KEY="your_key"      # free: 1,000 requests, one-time
    python linkedin_scraper_api_codes/job.py 4437608828

Docs: https://chocodata.com/docs
"""
import json
import os
import sys

import requests

API = "https://api.chocodata.com/api/v1/linkedin/job"
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


def job(job_id: str) -> dict:
    """Fetch one LinkedIn job posting by its numeric job_id."""
    r = requests.get(API, params={"api_key": KEY, "job_id": job_id}, timeout=90)
    _check(r)
    return r.json()


if __name__ == "__main__":
    jid = sys.argv[1] if len(sys.argv) > 1 else "4437608828"
    data = job(jid)
    print(json.dumps(data, indent=2)[:1500])
    print()
    print(f"{data['title']} at {data['company']} | {data['location']}")
    print(f"{data['seniority']} | {data['employment_type']} | {data['job_function']} | {data['applicants']}")
