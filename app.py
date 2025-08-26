# app.py — Universal Health Agent (Aggressive + Catalog)
# Local run:
#   pip install -r requirements.txt
#   python app.py --query "longevity OR aging OR chronic disease treatment" --build-catalog

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
    s = re.sub(r"<.*?>", " ", s)           # strip HTML tags
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

# ---------------------------- Evidence feeds ----------------------------
def google_news_feed(query: str, lang="en-IN") -> str:
    return f"https://news.google.com/rss/search?q={requests.utils.quote(query)}&hl={lang}&gl=IN&ceid=IN:{lang.split('-')[0]}"

def pubmed_feed(query: str) -> str:
    return f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/erss.cgi?db=pubmed&term={requests.utils.quote(query)}&sort=date"

BASE_FEEDS = [
    ("NIH", "https://www.nih.gov/news-events/news-releases/rss.xml"),
    ("WHO", "https://www.who.int/feeds/entity/mediacentre/news/en/rss.xml"),
    ("CDC", "https://tools.cdc.gov/api/v2/resources/media/403372.rss"),
    ("Cochrane News", "https://www.cochrane.org/news-feed.xml"),
    ("Nature", "https://www.nature.com/nature.rss"),
    ("BMJ", "https://www.bmj.com/latest.xml"),
    ("Lancet", "https://www.thelancet.com/rssfeed/lancet_current.xml"),
    ("PLOS Medicine", "https://journals.plos.org/plosmedicine/feed/atom"),
    ("ScienceDaily Health", "https://www.sciencedaily.com/rss/health_medicine.xml"),
    ("ScienceDaily Top", "https://www.sciencedaily.com/rss/top.xml"),
    ("bioRxiv Latest", "https://www.biorxiv.org/rss/latest.xml"),
    ("medRxiv Latest", "https://www.medrxiv.org/rss/latest.xml"),
]

def parse_date(entry):
    return entry.get("published", "") or entry.get("updated", "") or entry.get("dc_date", "") or ""

def fetch_feed(source: str, url: str, limit: int, delay: float):
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

def aggregate(query: str,
              per_feed_limit=80,
              max_total=700,
              thumb_budget=220,
              delay_between=0.4):
    feeds = BASE_FEEDS[:]
    if query:
        feeds = [("Google News", google_news_feed(query)),
                 ("PubMed", pubmed_feed(query))] + feeds

    all_items = []
    for src, url in feeds:
        all_items.extend(fetch_feed(src, url, per_feed_limit, delay_between))

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

    for it in deduped:
        if thumb_budget <= 0:
            break
        img = get_og_image(it["link"])
        if img:
            it["image"] = img
            thumb_budget -= 1

    deduped.sort(key=lambda x: x.get("date") or "", reverse=True)
    return deduped

def build(query: str):
    items = aggregate(query)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "items.json").write_text(json.dumps(items, indent=2), encoding="utf-8")

    if not (DATA_DIR / "catalog.json").exists():
        (DATA_DIR / "catalog.json").write_text(json.dumps({"programs": [], "experts": [], "institutions": []}, indent=2), encoding="utf-8")
    if not (DATA_DIR / "longevity_plan.json").exists():
        (DATA_DIR / "longevity_plan.json").write_text(json.dumps([], indent=2), encoding="utf-8")

    stamp = now_utc()
    (DATA_DIR / "logs.txt").write_text(f"Generated: {stamp}\nQuery: {query or '—'}\nItems: {len(items)}\n", encoding="utf-8")
    log(f"✅ Built {len(items)} items → output/data/items.json")

# ---------------------------- Catalog scraping ----------------------------
from collections import defaultdict

SITE_MAP = {
    # ↓ Replace these with real, permitted listing pages you trust
    # Example placeholders to show structure:
    "example_clinics": {
        "type": "institution",
        "url": "https://example.com/longevity-clinics",
        "item": ".clinic",
        "fields": {
            "name": ".title",
            "focus": ".desc",
            "location": ".location",
            "url": "a[href]",
            "image": "img[src]"
        }
    },
    "example_experts": {
        "type": "expert",
        "url": "https://example.com/experts",
        "item": ".expert-card",
        "fields": {
            "name": ".expert-name",
            "specialty": ".expert-specialty",
            "location": ".expert-location",
            "url": "a[href]",
            "image": "img[src]"
        }
    },
    "example_programs": {
        "type": "program",
        "url": "https://example.com/programs",
        "item": ".program-item",
        "fields": {
            "name": ".program-title",
            "category": ".program-category",
            "description": ".program-description",
            "location": ".program-location",
            "url": "a[href]",
            "image": "img[src]"
        }
    }
}

def text_or_none(node):
    return node.get_text(strip=True) if node else None

def abs_url(base, maybe):
    try:
        return urljoin(base, maybe) if maybe else None
    except Exception:
        return maybe

def scrape_generic_list(source_key, cfg):
    out = []
    try:
        r = requests.get(cfg["url"], headers=HEADERS, timeout=25)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "lxml")
        for card in soup.select(cfg["item"]):
            rec = {}
            for field, sel in cfg["fields"].items():
                if sel.endswith("[href]"):
                    tag = card.select_one(sel.split("[")[0])
                    rec[field] = abs_url(cfg["url"], tag.get("href") if tag else None)
                elif sel.endswith("[src]"):
                    tag = card.select_one(sel.split("[")[0])
                    rec[field] = abs_url(cfg["url"], tag.get("src") if tag else None)
                else:
                    rec[field] = text_or_none(card.select_one(sel))
            if not rec.get("image") and rec.get("url"):
                rec["image"] = get_og_image(rec["url"])
            rec = {k: v for k, v in rec.items() if v}
            rec["__type"] = cfg["type"]
            out.append(rec)
        log(f"[catalog] {source_key}: scraped {len(out)} items")
    except Exception as ex:
        log(f"[catalog] {source_key} error: {ex}")
    return out

def dedupe_by_key(items, key_fn):
    seen, out = set(), []
    for x in items:
        k = key_fn(x)
        if not k or k in seen:
            continue
        seen.add(k); out.append(x)
    return out

def classify_record(rec):
    t = rec.pop("__type", "").lower()
    if t == "program":
        return "programs", {
            "name": rec.get("name"),
            "category": rec.get("category") or "—",
            "description": rec.get("description") or rec.get("focus") or "—",
            "location": rec.get("location") or "—",
            "url": rec.get("url"),
            "image": rec.get("image"),
            "tags": []
        }
    if t == "expert":
        rating = None
        try:
            rating = float(rec.get("rating", "").strip())
        except Exception:
            pass
        return "experts", {
            "name": rec.get("name"),
            "specialty": rec.get("specialty") or "—",
            "location": rec.get("location") or "—",
            "rating": rating,
            "url": rec.get("url"),
            "image": rec.get("image"),
            "tags": []
        }
    return "institutions", {
        "name": rec.get("name"),
        "focus": rec.get("focus") or rec.get("description") or "—",
        "location": rec.get("location") or "—",
        "url": rec.get("url"),
        "image": rec.get("image"),
        "tags": []
    }

def build_catalog():
    all_raw = []
    for key, cfg in SITE_MAP.items():
        all_raw.extend(scrape_generic_list(key, cfg))

    def kfn(x):
        nm = (x.get("name") or "").strip().lower()
        domain = urlparse(x.get("url") or "").netloc.lower()
        return f"{nm}|{domain}" if nm else None

    all_raw = dedupe_by_key(all_raw, kfn)

    bucketed = {"programs": [], "experts": [], "institutions": []}
    for rec in all_raw:
        kind, norm = classify_record(rec)
        if norm.get("name") and norm.get("url"):
            bucketed[kind].append(norm)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "catalog.json").write_text(json.dumps(bucketed, indent=2), encoding="utf-8")
    log(f"[catalog] Wrote {len(bucketed['programs'])} programs, {len(bucketed['experts'])} experts, {len(bucketed['institutions'])} institutions")

# ---------------------------- CLI ----------------------------
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", type=str, default="longevity OR aging OR chronic disease treatment OR randomized trial")
    ap.add_argument("--build-catalog", action="store_true", help="Scrape and write output/data/catalog.json")
    args = ap.parse_args()

    build(args.query)
    if args.build_catalog:
        build_catalog()
