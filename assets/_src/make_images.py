"""Generate the repo's hero + evidence graphics with Pillow.

Every value rendered here is REAL: the JSON card fields come from
linkedin_scraper_api_data/job.json, and the free-vs-API numbers come from the measured
free-path benchmark of 2026-07-16 (20/20 sequential OK, 8 x HTTP 429 at 8 concurrent,
574,191 bytes of profile HTML vs 1,165 bytes of parsed JSON).

Nothing here is a mocked-up screenshot of a page we could not reach, and nothing here is
a metric we did not measure.
"""
import json
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(__file__), "..")
DATA = os.path.join(OUT, "..", "linkedin_scraper_api_data")
F = "C:/Windows/Fonts/"


def font(name, size):
    for cand in (name, "segoeui.ttf"):
        try:
            return ImageFont.truetype(F + cand, size)
        except OSError:
            continue
    return ImageFont.load_default()


BOLD, SEMI, REG, MONO = "segoeuib.ttf", "seguisb.ttf", "segoeui.ttf", "consola.ttf"
INK = (245, 243, 240)
MUTE = (169, 162, 154)
DIM = (111, 106, 100)
ACC = (255, 143, 90)
ACC2 = (255, 196, 138)


def vgrad(w, h, top, bot):
    """Vertical gradient base."""
    img = Image.new("RGB", (1, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(1, h - 1)
        d.point((0, y), tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)))
    return img.resize((w, h))


def glow(img, cx, cy, rx, ry, color, strength):
    """Soft radial glow, composited additively."""
    layer = Image.new("RGB", img.size, (0, 0, 0))
    d = ImageDraw.Draw(layer)
    steps = 44
    for i in range(steps, 0, -1):
        t = i / steps
        a = int(strength * (1 - t) ** 2.2)
        d.ellipse([cx - rx * t, cy - ry * t, cx + rx * t, cy + ry * t],
                  fill=tuple(int(c * a / 255) for c in color))
    return Image.fromarray(
        np.clip(np.asarray(img, dtype=int) + np.asarray(layer, dtype=int), 0, 255).astype("uint8"))


def pill(d, x, y, text, f, hot=False):
    w = d.textlength(text, font=f)
    h = 30
    d.rounded_rectangle([x, y, x + w + 28, y + h], radius=15,
                        fill=(28, 20, 17) if hot else (25, 26, 30),
                        outline=(120, 66, 44) if hot else (52, 54, 60))
    d.text((x + 14, y + 6), text, font=f, fill=ACC2 if hot else (221, 214, 207))
    return w + 28 + 9


def hero():
    W, H = 1280, 540
    img = vgrad(W, H, (15, 17, 21), (26, 18, 16))
    img = glow(img, 1000, 100, 520, 300, (255, 143, 90), 46)
    img = glow(img, 150, 470, 420, 260, (120, 84, 60), 40)
    d = ImageDraw.Draw(img)

    # faint grid
    for x in range(0, W, 64):
        d.line([(x, 0), (x, H)], fill=(24, 26, 31))
    for y in range(0, H, 64):
        d.line([(0, y), (W, y)], fill=(24, 26, 31))

    # brand
    d.ellipse([64, 60, 75, 71], fill=ACC)
    d.text((88, 57), "C H O C O D A T A", font=font(SEMI, 15), fill=(185, 178, 170))

    # headline
    d.text((64, 108), "LinkedIn", font=font(BOLD, 76), fill=INK)
    d.text((64, 192), "Scraper", font=font(BOLD, 76), fill=ACC)

    d.text((64, 300), "Extract job listings, job descriptions, company profiles", font=font(REG, 23), fill=MUTE)
    d.text((64, 334), "and member profiles from LinkedIn.com as structured JSON.", font=font(REG, 23), fill=MUTE)

    # element pills. Only elements the API actually returns.
    els = [("job listings", 1), ("job descriptions", 1), ("company profiles", 1),
           ("member profiles", 1), ("employee counts", 0), ("posts", 1), ("engagement", 0),
           ("seniority", 0), ("industries", 0), ("headlines", 0), ("followers", 0),
           ("locations", 0)]
    f = font(REG, 15)
    x, y = 64, 410
    for t, hot in els:
        w = d.textlength(t, font=f) + 37
        if x + w > 700:
            x, y = 64, y + 39
        x += pill(d, x, y, t, f, hot=bool(hot))

    # real JSON card, straight out of the committed sample
    cx, cy, cw = 828, 150, 388
    d.rounded_rectangle([cx, cy, cx + cw, cy + 268], radius=14, fill=(11, 13, 17), outline=(45, 47, 53))
    d.rounded_rectangle([cx, cy, cx + cw, cy + 38], radius=14, fill=(21, 23, 28))
    d.rectangle([cx, cy + 24, cx + cw, cy + 38], fill=(21, 23, 28))
    for i, c in enumerate([(255, 95, 87), (254, 188, 46), (40, 200, 64)]):
        d.ellipse([cx + 14 + i * 18, cy + 14, cx + 24 + i * 18, cy + 24], fill=c)
    d.line([(cx, cy + 38), (cx + cw, cy + 38)], fill=(38, 40, 46))

    j = json.load(open(os.path.join(DATA, "job.json"), encoding="utf-8"))
    rows = [("{", None, None),
            ('  "title"', f'"{j["title"]}"', "s"),
            ('  "company"', f'"{j["company"]}"', "s"),
            ('  "location"', f'"{j["location"]}"', "s"),
            ('  "seniority"', f'"{j["seniority"]}"', "s"),
            ('  "employment_type"', f'"{j["employment_type"]}"', "s"),
            ('  "applicants"', f'"{j["applicants"]}"', "s"),
            ("}", None, None)]
    fm = font(MONO, 13)
    yy = cy + 58
    for k, v, kind in rows:
        if v is None:
            d.text((cx + 18, yy), k, font=fm, fill=DIM)
        else:
            d.text((cx + 18, yy), k, font=fm, fill=(127, 178, 255))
            kw = d.textlength(k, font=fm)
            d.text((cx + 18 + kw, yy), ": ", font=fm, fill=DIM)
            d.text((cx + 18 + kw + d.textlength(": ", font=fm), yy), v, font=fm,
                   fill=(154, 230, 160) if kind == "s" else ACC2)
        yy += 26
    d.text((828, 468), "6 endpoints  ·  real JSON  ·  no login, no browser", font=font(REG, 14), fill=DIM)
    img.save(os.path.join(OUT, "hero.png"))
    print("wrote assets/hero.png", img.size)


def evidence():
    """The honest side-by-side. The free path WORKS here: that is the real finding, and the
    argument is throughput and parsing, not a bot wall.

    Both panels describe the SAME operation (one job search for "python developer") so the
    rows compare like with like. Wire bytes are the compressed transfer measured with
    decode_content=False, because that is what a proxy actually bills; using the decoded
    character count here would overstate the DIY side by ~9x.
    """
    W, H = 1280, 440
    img = vgrad(W, H, (15, 17, 21), (22, 16, 15))
    d = ImageDraw.Draw(img)
    d.text((64, 40), "The free scraper works. Here is what it costs you.", font=font(BOLD, 27), fill=INK)
    d.text((64, 80), "Measured 2026-07-16 from a clean residential IP. Reproduce it: python benchmarks/measure.py",
           font=font(REG, 15), fill=DIM)

    fm = font(MONO, 13)
    m = json.load(open(os.path.join(os.path.dirname(__file__), "measurements.json"), encoding="utf-8"))

    # left: the free path. Amber, not red: it is not broken, it is limited.
    d.rounded_rectangle([64, 124, 624, 392], radius=13, fill=(22, 18, 12), outline=(112, 84, 40))
    d.text((88, 144), "free_scraper/linkedin_free_scraper.py", font=font(MONO, 13), fill=(224, 176, 96))
    for i, ln in enumerate([
        f"Sequential ......... {m['seq_ok']} of {m['seq_n']} OK",
        f"Jobs per call ...... {m['free_cards']}",
        f"Fields per job ..... {m['free_card_fields']}",
        f"{m['burst_n']} calls @ {m['burst_workers']} conc .. {m['burst_429']} x HTTP 429",
        "Job description .... absent (needs a 2nd fetch)",
        f"Bytes on the wire .. {m['free_search_wire']:,}",
    ]):
        d.text((88, 182 + i * 25), ln, font=fm, fill=(178, 168, 162))
    d.text((88, 352), "Works. Until you need volume.", font=font(BOLD, 16), fill=(226, 170, 84))

    # right: the API, same operation
    d.rounded_rectangle([656, 124, 1216, 392], radius=13, fill=(12, 20, 14), outline=(46, 96, 54))
    d.text((680, 144), "linkedin_scraper_api_codes/jobsearch.py", font=font(MONO, 13), fill=(130, 210, 140))
    js = json.load(open(os.path.join(DATA, "jobsearch.json"), encoding="utf-8"))
    job = json.load(open(os.path.join(DATA, "job.json"), encoding="utf-8"))
    for i, ln in enumerate([
        "HTTP status ........ 200",
        f"Jobs per call ...... {len(js['results'])}",
        f"Fields per job ..... {len(js['results'][0])}",
        "Concurrency ........ 10 to 50 by plan",
        f"Job description .... 1 call away ({len(job['description']):,} chars)",
        f"Bytes on the wire .. {m['api_search_wire']:,}",
    ]):
        d.text((680, 182 + i * 25), ln, font=fm, fill=(178, 168, 162))
    d.text((680, 352), f"Parsed JSON, {len(js['results'][0])} fields per listing",
           font=font(BOLD, 16), fill=(110, 210, 130))

    img.save(os.path.join(OUT, "free-vs-api.png"))
    print("wrote assets/free-vs-api.png", img.size)


if __name__ == "__main__":
    hero()
    evidence()
