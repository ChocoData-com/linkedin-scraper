"""Render developer-journey screenshots from REAL captured session output.

Follows the pattern oxylabs/amazon-scraper uses: a terminal shot of the command actually
running, then a table shot of the data it retrieved.

The text rendered here is the verbatim stdout of a real run (captured to a local qa/
directory) and the real committed JSON. The shell prompt is deliberately generic so no
local username or path is exposed.
"""
import json
import os
import re

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "..")
DATA = os.path.join(OUT, "..", "linkedin_scraper_api_data")
QA = os.environ.get("LI_QA_DIR", os.path.expandvars(r"%TEMP%\qa"))
F = "C:/Windows/Fonts/"

MONO = ImageFont.truetype(F + "consola.ttf", 15)
MONOB = ImageFont.truetype(F + "consolab.ttf", 15)
UI = ImageFont.truetype(F + "segoeui.ttf", 14)
UIB = ImageFont.truetype(F + "seguisb.ttf", 14)

BG, FG, DIM = (13, 15, 19), (208, 205, 200), (110, 106, 100)
GREEN, BLUE, AMBER, RED, CYAN = (126, 209, 138), (127, 178, 255), (255, 196, 138), (232, 118, 118), (120, 205, 210)

SECRET = re.compile(r"asa_live_[A-Za-z0-9_\-]+")


def sanitize(s: str) -> str:
    """Never leak a key, a local path, or a username into an image."""
    s = SECRET.sub("$CHOCODATA_API_KEY", s)
    s = re.sub(r"[A-Za-z]:\\Users\\[^\\\s]+", "~", s)
    s = re.sub(r"/c/Users/[^/\s]+", "~", s)
    s = s.replace(os.environ.get("USERNAME", "\0"), "dev")
    return s


def terminal(lines, path, width=1180, title="bash"):
    pad, lh = 18, 23
    h = 46 + pad * 2 + lh * len(lines)
    img = Image.new("RGB", (width, h), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, width, 38], fill=(24, 26, 31))
    for i, c in enumerate([(255, 95, 87), (254, 188, 46), (40, 200, 64)]):
        d.ellipse([16 + i * 20, 14, 26 + i * 20, 24], fill=c)
    d.text((width // 2 - 26, 11), title, font=UI, fill=DIM)
    y = 38 + pad
    for text, color, bold in lines:
        d.text((pad, y), text, font=MONOB if bold else MONO, fill=color)
        y += lh
    img.save(os.path.join(OUT, path))
    print("wrote assets/" + path, img.size)


def read_out(name):
    p = os.path.join(QA, name)
    return sanitize(open(p, encoding="utf-8", errors="replace").read()) if os.path.exists(p) else ""


def colorize(l):
    c = FG
    if re.search(r'"\w+":', l):
        c = BLUE
    if re.search(r':\s+\d', l):
        c = AMBER
    return c


def shot_jobsearch():
    """The API call actually running: what a developer sees."""
    body = [l for l in read_out("jobsearch.out").strip().splitlines() if l.strip()]
    head, tail = body[:14], body[-1]
    lines = [('$ export CHOCODATA_API_KEY="your_key"', GREEN, True),
             ("$ python linkedin_scraper_api_codes/jobsearch.py", GREEN, True), ("", FG, False)]
    for l in head:
        lines.append((l[:110], colorize(l), False))
    lines += [("  ...", DIM, False), ("", FG, False), (tail[:110], CYAN, True)]
    terminal(lines, "run-jobsearch.png", title="linkedin-scraper")


def shot_free():
    """The free scraper WORKING. It is not blocked, and pretending otherwise would be a lie."""
    body = [l for l in read_out("free_ok.out").strip().splitlines() if l.strip()]
    lines = [('$ python free_scraper/linkedin_free_scraper.py "python developer" "United States"', GREEN, True),
             ("", FG, False)]
    for l in body[:11]:
        lines.append((l[:105], colorize(l), False))
    lines += [("  ...", DIM, False), ("", FG, False), (body[-1][:105], CYAN, True),
              ("", FG, False),
              ("# no key, no cost, and it works. The wall is throughput, not access:", DIM, False),
              ("# see 'Avoid getting blocked when scraping LinkedIn'.", DIM, False)]
    terminal(lines, "run-free.png", title="linkedin-scraper")


def shot_table():
    """Retrieved data as a table, the way oxylabs shows it."""
    s = json.load(open(os.path.join(DATA, "jobsearch.json"), encoding="utf-8"))["results"][:8]
    cols = [("#", 30), ("title", 260), ("company", 190), ("location", 168), ("job_id", 100), ("posted_date", 100)]
    W = sum(c[1] for c in cols) + 40
    rh, hh = 30, 34
    H = 52 + hh + rh * len(s)
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((20, 14), "linkedin_job_listings", font=UIB, fill=(30, 30, 30))
    x0, y0 = 20, 46
    d.rectangle([x0, y0, W - 20, y0 + hh], fill=(238, 238, 238))
    x = x0
    for name, w in cols:
        d.text((x + 9, y0 + 9), name, font=UIB, fill=(20, 20, 20))
        x += w
    y = y0 + hh
    for i, r in enumerate(s):
        if i % 2:
            d.rectangle([x0, y, W - 20, y + rh], fill=(250, 250, 250))
        def cut(v, n):
            v = str(v) if v is not None else "-"
            return v[:n] + ("..." if len(v) > n else "")
        vals = [str(i), cut(r["title"], 34), cut(r["company"], 24), cut(r["location"], 22),
                r["job_id"], r["posted_date"] or "-"]
        x = x0
        for (name, w), v in zip(cols, vals):
            d.text((x + 9, y + 7), v, font=MONO if name in ("job_id", "posted_date") else UI,
                   fill=(60, 60, 60) if name != "#" else (150, 150, 150))
            x += w
        d.line([(x0, y), (W - 20, y)], fill=(226, 226, 226))
        y += rh
    d.line([(x0, y), (W - 20, y)], fill=(226, 226, 226))
    for i in range(len(cols) + 1):
        xx = x0 + sum(c[1] for c in cols[:i])
        d.line([(xx, y0), (xx, y)], fill=(226, 226, 226))
    img.save(os.path.join(OUT, "retrieved-data.png"))
    print("wrote assets/retrieved-data.png", img.size)


def shot_generic(src, out, cmd, tail_color=CYAN, keep=13, note=None):
    """Terminal shot of any script's real captured stdout."""
    body = [l for l in read_out(src).strip().splitlines() if l.strip()]
    lines = [(f"$ python {cmd}", GREEN, True), ("", FG, False)]
    for l in body[:keep]:
        lines.append((l[:110], colorize(l), False))
    if len(body) > keep + 1:
        lines.append(("  ...", DIM, False))
    lines += [("", FG, False)]
    for l in body[-2:] if len(body) > 1 else body[-1:]:
        lines.append((l[:110], tail_color, True))
    if note:
        lines += [("", FG, False)] + [(n, DIM, False) for n in note]
    terminal(lines, out, title="linkedin-scraper")


def shot_error():
    """The error UX: what a bad key actually gives you. Trust-building."""
    body = read_out("badkey.out").strip().splitlines()
    lines = [('$ export CHOCODATA_API_KEY="wrong_key"', GREEN, True),
             ("$ python linkedin_scraper_api_codes/jobsearch.py", GREEN, True), ("", FG, False)]
    for l in body[:4]:
        lines.append((l[:105], RED, True))
    lines += [("", FG, False),
              ("# no traceback, no silent empty list: every documented error", DIM, False),
              ("# maps to a message that tells you what to do next.", DIM, False)]
    terminal(lines, "run-error.png", title="linkedin-scraper")


if __name__ == "__main__":
    shot_jobsearch()
    shot_free()
    shot_table()
    shot_generic("job.out", "run-job.png", "linkedin_scraper_api_codes/job.py 4437608828")
    shot_generic("profile.out", "run-profile.png", "linkedin_scraper_api_codes/profile.py williamhgates",
                 note=["# the nulls are real: this endpoint returns title and date_range as null",
                       "# on the logged-out profile page, so we do not invent them."])
    shot_generic("monitor1.out", "run-monitor.png",
                 'linkedin_scraper_api_codes/job_monitor.py "python developer" "United States" --enrich', keep=10)
    shot_error()
