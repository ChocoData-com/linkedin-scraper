"""
Reproduce every measured number on this repo's README.

The README makes claims like "20 of 20 sequential calls returned job cards", "8 x HTTP 429
at 8 concurrent", "a profile page is 609,446 characters that gzip to 62,049 bytes on the
wire", and a latency table. This script is where all of those come from. Run it and you
get your own numbers, on your own connection, on today's LinkedIn.

    pip install requests
    export CHOCODATA_API_KEY="your_key"      # optional: skip it and only the free-path
    python benchmarks/measure.py             # and byte measurements run

Output: benchmarks/measurements.json (and a copy in assets/_src/ that the image
generators read, so every number rendered into a graphic traces back to a real run).

Expect your numbers to differ from ours. LinkedIn's page weight drifts between fetches and
the 429 threshold depends on your IP and the moment. That is the point of shipping the
script instead of asking you to trust a table.

A note on bytes: `len(r.text)` counts DECODED characters. Proxies bill the COMPRESSED
transfer, so this script measures both and the README uses the wire number for anything
that costs money. Those differ by ~9x on LinkedIn, which is enough to flip a build-vs-buy
argument, so it is worth getting right.
"""
import json
import os
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "free_scraper"))
from linkedin_free_scraper import HEADERS, extract_jobs  # noqa: E402

GUEST = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
API = "https://api.chocodata.com/api/v1/linkedin"
KEY = os.environ.get("CHOCODATA_API_KEY")
KW, LOC = "python developer", "United States"
POST_URL = ("https://www.linkedin.com/posts/satyanadella_looking-ahead-to-2026-"
            "activity-7411490079984250880-Vb5v")
M = {"measured_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


def sizes(url, params=None, headers=HEADERS):
    """Decoded characters AND compressed bytes off the socket, for the same URL."""
    h = dict(headers or {})
    h["Accept-Encoding"] = "gzip, deflate, br"
    decoded = len(requests.get(url, params=params, headers=h, timeout=60).text)
    r = requests.get(url, params=params, headers=h, timeout=60, stream=True)
    wire = sum(len(c) for c in r.raw.stream(8192, decode_content=False))
    return decoded, wire


print("1. free guest job search, 20 sequential calls")
ok = 0
for i in range(20):
    r = requests.get(GUEST, params={"keywords": KW, "location": LOC, "start": i * 10},
                     headers=HEADERS, timeout=30)
    if r.status_code == 200 and extract_jobs(r.text):
        ok += 1
    time.sleep(0.3)
M["seq_ok"], M["seq_n"] = ok, 20
print(f"   {ok} of 20 returned job cards")

print("2. free guest job search, 40 calls at 8 concurrent")


def one(i):
    try:
        r = requests.get(GUEST, params={"keywords": "engineer", "location": LOC,
                                        "start": (i % 30) * 10}, headers=HEADERS, timeout=30)
        return r.status_code, len(extract_jobs(r.text))
    except Exception:
        return None, 0


t0 = time.time()
with ThreadPoolExecutor(max_workers=8) as p:
    res = list(p.map(one, range(40)))
M["burst_n"], M["burst_workers"] = 40, 8
M["burst_ok"] = sum(1 for sc, n in res if sc == 200 and n > 0)
M["burst_429"] = sum(1 for sc, _ in res if sc == 429)
M["burst_secs"] = round(time.time() - t0, 1)
print(f"   {M['burst_ok']} OK, {M['burst_429']} x HTTP 429, in {M['burst_secs']}s")

print("   cooling down until the guest endpoint serves cards again...")
t0 = time.time()
for _ in range(20):
    probe = requests.get(GUEST, params={"keywords": KW, "location": LOC}, headers=HEADERS, timeout=30)
    if probe.status_code == 200 and extract_jobs(probe.text):
        break
    time.sleep(5)
M["burst_recovery_secs"] = round(time.time() - t0)
print(f"   recovered after ~{M['burst_recovery_secs']}s of sequential polling "
      f"(the 429 is a throttle, not a ban)")

print("3. what one free call gives you")
cards = extract_jobs(requests.get(GUEST, params={"keywords": KW, "location": LOC},
                                  headers=HEADERS, timeout=30).text)
if not cards:
    sys.exit("   still throttled. Wait a minute and re-run: the guest endpoint is rate-limiting you.")
M["free_cards"], M["free_card_fields"] = len(cards), len(cards[0])
M["free_search_decoded"], M["free_search_wire"] = sizes(GUEST, {"keywords": KW, "location": LOC})
print(f"   {M['free_cards']} cards x {M['free_card_fields']} fields | "
      f"{M['free_search_decoded']:,} chars decoded, {M['free_search_wire']:,} on the wire")

print("4. bytes you carry for one public profile page")
M["profile_html_decoded"], M["profile_html_wire"] = sizes("https://www.linkedin.com/in/williamhgates")
M["profile_gzip_ratio"] = round(M["profile_html_decoded"] / M["profile_html_wire"], 1)
print(f"   {M['profile_html_decoded']:,} chars decoded -> {M['profile_html_wire']:,} on the wire "
      f"({M['profile_gzip_ratio']}x)")
for rate in (3, 8):
    print(f"   at ${rate}/GB that fetch costs ${M['profile_html_wire']/1e9*rate:.5f}")
M["profile_wire_cost_3gb"] = round(M["profile_html_wire"] / 1e9 * 3, 5)
M["profile_wire_cost_8gb"] = round(M["profile_html_wire"] / 1e9 * 8, 5)

if not KEY:
    json.dump(M, open(os.path.join(HERE, "measurements.json"), "w"), indent=2)
    sys.exit("\nCHOCODATA_API_KEY not set: skipped the API half. Free key: https://chocodata.com")

print("5. the same job search through the API")
p = {"api_key": KEY, "keywords": KW, "location": LOC}
M["api_search_decoded"], M["api_search_wire"] = sizes(f"{API}/jobsearch", p, headers={})
js = requests.get(f"{API}/jobsearch", params=p, timeout=90).json()
M["api_jobs"], M["api_list_fields"] = len(js["results"]), len(js["results"][0])
print(f"   {M['api_jobs']} jobs x {M['api_list_fields']} fields | "
      f"{M['api_search_decoded']:,} chars, {M['api_search_wire']:,} on the wire")

M["api_profile_decoded"], M["api_profile_wire"] = sizes(
    f"{API}/profile", {"api_key": KEY, "username": "williamhgates"}, headers={})
print(f"   profile: {M['api_profile_decoded']:,} chars, {M['api_profile_wire']:,} on the wire "
      f"(vs {M['profile_html_wire']:,} scraping it yourself)")

print("6. latency, n=5 per endpoint")
BENCH = [("jobsearch", {"keywords": KW, "location": LOC}),
         ("job", {"job_id": js["results"][0]["job_id"]}),
         ("company", {"company": "microsoft"}),
         ("profile", {"username": "williamhgates"}),
         ("post", {"url": POST_URL}),
         ("email", {"url": "https://www.linkedin.com/company/microsoft"})]
M["latency"] = {}
for res_name, params in BENCH:
    ts = []
    for _ in range(5):
        t0 = time.time()
        r = requests.get(f"{API}/{res_name}", params={"api_key": KEY, **params}, timeout=120)
        if r.status_code == 200:
            ts.append(time.time() - t0)
        time.sleep(0.4)
    if ts:
        M["latency"][res_name] = {"median": round(statistics.median(ts), 1),
                                  "lo": round(min(ts), 1), "hi": round(max(ts), 1), "n": len(ts)}
        v = M["latency"][res_name]
        print(f"   /{res_name:10} median {v['median']:4.1f}s  range {v['lo']} to {v['hi']}s  n={v['n']}")

for path in (os.path.join(HERE, "measurements.json"),
             os.path.join(REPO, "assets", "_src", "measurements.json")):
    json.dump(M, open(path, "w"), indent=2)
print("\nwrote benchmarks/measurements.json")
