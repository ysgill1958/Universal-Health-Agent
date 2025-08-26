# app.py — Universal Health Agent (Aggressive Scraper)
# Usage (local):  pip install -r requirements.txt && python app.py --query "longevity OR chronic disease"
# The script writes output/data/items.json + logs.txt and your static site uses them.

import os, re, json, time, hashlib, argparse
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urljoin

import requests
import feedparser
from bs4 import BeautifulSoup

# ---------------------------- Paths ----------------------------
OUTPUT_DIR = Path("output")
DATA_DIR = OUTPUT_DIR / "data"
STATIC_DIR = OUTPUT_DIR / "static"
for p in (OUTPUT_DIR, DATA_DIR, STATIC_DIR):
    p.mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / ".nojekyll").write_text("")

# ---------------------------- Utils ----------------------------
def now_utc() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

def log(msg: str):
    ts = now_utc()
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(DATA_DIR / "logs.txt", "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:
        pass

def clean_text(s: str) -> str:
    if not s:
        return ""
    # strip HTML
    s = re.sub(r"<.*?>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def truncate(s: str, n=360) -> str:
    s = clean_text(s)
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + "…"

def normalize_key(title: str, link: str) -> str:
    host = urlparse(link or "").netloc.lower()
    t = re.sub(r"\s+", " ", (title or "").lower()).strip()
    t = re.sub(r"[^a-z0-9 ]+", "", t)
    return hashlib.sha1(f"{host}|{t}".encode()).hexdigest()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (UHA/2.0; +GitHub Pages Agent)"
}

# ---------------------------- Thumbnails ----------------------------
def get_og_image(url: str, timeout=8) -> str | None:
    """Try og:image, twitter:image, or first <img>. Returns absolute URL or None."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "lxml")

        for css, attr in [
            ('meta[property="og:image"]', "content"),
            ('meta[property="og:image:url"]', "content"),
            ('meta[name="twitter:image"]', "content"),
        ]:
            m = soup.select_one(css)
            if m and m.get(attr):
                return urljoin(url, m.get(attr).strip())

        for img in soup.find_all("img", src=True):
            src = urljoin(url, img["src"])
            if any(bad in src for bad in ("data:", "sprite", "pixel", "base64")):
                continue
            return src
    except Exception as ex:
        log(f"OG image fetch failed: {ex}")
    return None

# ---------------------------- Feeds ----------------------------
def google_news_feed(query: str, lang="en-IN") -> str:
    return f"https://news.google.com/rss/search?q={requests.utils.quote(query)}&hl={lang}&gl=IN&ceid=IN:{lang.split('-')[0]}"

def pubmed_feed(query: str) -> str:
    return f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/erss.cgi?db=pubmed&term={requests.utils.quote(query)}&sort=date"

# Core reputable health/science feeds (RSS/Atom).
# NOTE: If any URL 404s, we log and keep going; the script is resilient.
BASE_FEEDS = [
    # Agencies & orgs
    ("NIH", "https://www.nih.gov/news-events/news-releases/rss.xml"),
    ("WHO", "https://www.who.int/feeds/entity/mediacentre/news/en/rss.xml"),
    ("CDC", "https://tools.cdc.gov/api/v2/resources/media/403372.rss"),
    ("Cochrane News", "https://www.cochrane.org/news-feed.xml"),

    # Journals / publishers
    ("Nature", "https://www.nature.com/nature.rss"),
    ("BMJ", "https://www.bmj.com/latest.xml"),
    ("Lancet", "https://www.thelancet.com/rssfeed/lancet_current.xml"),
    ("PLOS Medicine", "https://journals.plos.org/plosmedicine/feed/atom"),
    ("ScienceDaily Health", "https://www.sciencedaily.com/rss/health_medicine.xml"),
    ("ScienceDaily Top", "https://www.sciencedaily.com/rss/top.xml"),

    # Preprints (fast-moving)
    ("bioRxiv Latest", "https://www.biorxiv.org/rss/latest.xml"),
    ("medRxiv Latest", "https://www.medrxiv.org/rss/latest.xml"),
]

# ---------------------------- Fetching ----------------------------
def parse_date(entry):
    # Use published / updated string if present (feedparser already did the parsing best-effort)
    return entry.get("published", "") or entry.get("updated", "") or entry.get("dc_date", "") or ""

def fetch_feed(source: str, url: str, limit: int, delay: float):
    """Return list of items from a single feed."""
    items = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=25)
        resp.raise_for_status()
        fp = feedparser.parse(resp.content)

        for e in fp.entries[:limit]:
            items.append({
                "source": source,
                "title": (e.get("title") or "").strip(),
                "link": (e.get("link") or "").strip(),
                "summary": truncate(e.get("summary") or e.get("description") or ""),
                "date": parse_date(e),
                "image": None
            })
        log(f"Fetched {len(items)} from {source}")
    except Exception as ex:
        log(f"Fetch error from {source}: {ex}")
    finally:
        if delay > 0:
            time.sleep(delay)
    return items

# ---------------------------- Aggregate ----------------------------
def aggregate(query: str,
              per_feed_limit=80,
              max_total=700,
              thumb_budget=220,
              delay_between=0.4):
    """
    Aggregate across feeds. With default settings, aims for ~500–700 unique items.
    """
    feeds = BASE_FEEDS[:]
    if query:
        feeds = [("Google News", google_news_feed(query)),
                 ("PubMed", pubmed_feed(query))] + feeds

    all_items = []
    for src, url in feeds:
        all_items.extend(fetch_feed(src, url, per_feed_limit, delay_between))

    # Deduplicate by normalized (host|title)
    seen = set()
    deduped = []
    for it in all_items:
        k = normalize_key(it.get("title"), it.get("link"))
        if not it.get("title") or not it.get("link"):
            continue
        if k in seen:
            continue
        seen.add(k)
        deduped.append(it)
        if len(deduped) >= max_total:
            break

    log(f"After dedupe: {len(deduped)} items")

    # Add thumbnails (respect budget)
    for it in deduped:
        if thumb_budget <= 0:
            break
        img = get_og_image(it["link"])
        if img:
            it["image"] = img
            thumb_budget -= 1

    # Sort by date string (best-effort)
    deduped.sort(key=lambda x: x.get("date") or "", reverse=True)
    return deduped

# ---------------------------- Build ----------------------------
def build(query: str):
    items = aggregate(query)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "items.json").write_text(json.dumps(items, indent=2), encoding="utf-8")

    # Ensure other data files exist (site expects them)
    if not (DATA_DIR / "catalog.json").exists():
        (DATA_DIR / "catalog.json").write_text(json.dumps({"programs": [], "experts": [], "institutions": []}, indent=2), encoding="utf-8")
    if not (DATA_DIR / "longevity_plan.json").exists():
        (DATA_DIR / "longevity_plan.json").write_text(json.dumps([], indent=2), encoding="utf-8")

    stamp = now_utc()
    (DATA_DIR / "logs.txt").write_text(f"Generated: {stamp}\nQuery: {query or '—'}\nItems: {len(items)}\n", encoding="utf-8")
    log(f"✅ Built {len(items)} items → output/data/items.json")

# ---------------------------- CLI ----------------------------
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", type=str, default="longevity OR aging OR chronic disease treatment OR randomized trial")
    args = ap.parse_args()
    build(args.query)
