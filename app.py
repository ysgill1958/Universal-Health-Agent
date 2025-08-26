# app.py — Universal Health Agent (Aggressive + Catalog, newest-first ordering)
# Local run:
#   pip install -r requirements.txt
#   python app.py --query "longevity OR aging OR chronic disease treatment" --build-catalog

import os, re, json, time, hashlib, argparse, email.utils as eut
from time import mktime
from datetime import datetime, timezone
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

# Newest-first date parsing
def parse_date(entry):
    # Prefer structured time if present
    for key in ("published_parsed", "updated_parsed"):
        if entry.get(key):
            try:
                return datetime.utcfromtimestamp(mktime(entry[key])).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pass
    # Try common string fields
    for key in ("published", "updated", "dc_date"):
        if entry.get(key):
            try:
                tt = eut.parsedate_to_datetime(entry[key])
                if tt.tzinfo:
                    tt = tt.astimezone(timezone.utc).replace(tzinfo=None)
                return tt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                continue
    # Fallback: empty (will sort to bottom)
    return ""

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

    # Add thumbnails (respect budget)
    for it in deduped:
        if thumb_budget <= 0:
            break
        img = get_og_image(it["link"])
        if img:
            it["image"] = img
            thumb_budget -= 1

    # Newest-first
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

# ---------------------------- Catalog scraping (Programs / Experts / Institutions) ----------------------------
def domain_of(u):
    try:
        return urlparse(u).netloc.lower()
    except Exception:
        return ""

def is_external_link(page_url, href):
    if not href: return False
    d0 = domain_of(page_url)
    d1 = domain_of(href)
    return d1 and d1 != d0

def guess_name_from_anchor(a_tag, href):
    # Prefer anchor text; fallback to domain
    txt = (a_tag.get_text(" ", strip=True) if a_tag else "")[:120]
    if txt and not txt.lower().startswith(("http://","https://")):
        return txt
    dom = domain_of(href)
    if dom.startswith("www."): dom = dom[4:]
    return dom or href

def make_record(kind, name, href, image=None, **extra):
    rec = {"name": name, "url": href, "image": image, "__type": kind}
    rec.update(extra)
    return rec

# Seeds for your 5 sources
SITE_MAP = {
    # 1) Scispot list → external company links
    "scispot_top20_longevity_biotechs": {
        "mode": "outlinks",
        "type": "institution",
        "url": "https://www.scispot.com/blog/top-20-of-most-innovative-anti-aging-companies-in-the-world",
        "container": "article, main, .blog-content, .prose",
        "tags": ["longevity", "biotech", "companies"]
    },
    # 2) Labiotech list → external company links
    "labiotech_top_biotech_companies": {
        "mode": "outlinks",
        "type": "institution",
        "url": "https://www.labiotech.eu/best-biotech/anti-aging-biotech-companies/",
        "container": "article, main, .single-content, .article__content",
        "tags": ["longevity", "biotech", "companies"]
    },
    # 3) Longevity-Clinic list → external clinic links
    "longevity_clinic_top18": {
        "mode": "outlinks",
        "type": "institution",
        "url": "https://longevity-clinic.co.uk/what-is-the-best-longevity-clinic-in-the-world/",
        "container": "article, main, .entry-content, .content",
        "tags": ["longevity", "clinic", "ranking"]
    },
    # 4) Lifespan.io Rejuvenation Roadmap → outbound programs/resources
    "lifespan_rejuvenation_roadmap": {
        "mode": "outlinks",
        "type": "program",
        "url": "https://www.lifespan.io/road-maps/the-rejuvenation-roadmap/",
        "container": "article, main, #content, .entry-content, .wrap",
        "tags": ["rejuvenation", "roadmap", "programs"]
    },
    # 5) DrKalidas clinic homepage → single institution
    "dr_kalidas_center": {
        "mode": "single",
        "type": "institution",
        "url": "https://drkalidas.com/",
        "name": "The Center for Natural & Integrative Medicine (Dr. Kalidas)",
        "location": "Orlando, Florida, USA",
        "tags": ["integrative", "naturopathic", "clinic"]
    },
}

def scrape_outlinks(cfg):
    out = []
    try:
        page_url = cfg["url"]
        r = requests.get(page_url, headers=HEADERS, timeout=25)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "lxml")
        container = None
        for sel in (cfg.get("container") or "").split(","):
            sel = sel.strip()
            if not sel: continue
            node = soup.select_one(sel)
            if node:
                container = node
                break
        if container is None:
            container = soup  # fallback

        seen = set()
        for a in container.select("a[href]"):
            href = a.get("href")
            href = urljoin(page_url, href)
            if not is_external_link(page_url, href):
                continue
            d = domain_of(href)
            # ignore social/share/junk
            if any(bad in d for bad in ("facebook.", "twitter.", "x.com", "instagram.", "linkedin.", "pinterest.", "reddit.")):
                continue
            key = (d, href.split("#")[0])
            if key in seen:
                continue
            seen.add(key)
            name = guess_name_from_anchor(a, href)
            img = get_og_image(href)
            rec = make_record(cfg["type"], name, href, image=img, tags=cfg.get("tags", []))
            out.append(rec)

        log(f"[catalog] outlinks: {len(out)} from {page_url}")
    except Exception as ex:
        log(f"[catalog] outlinks error: {ex}")
    return out

def scrape_single(cfg):
    out = []
    try:
        page_url = cfg["url"]
        name = cfg.get("name") or domain_of(page_url)
        img = get_og_image(page_url)
        rec = make_record(cfg["type"], name, page_url, image=img,
                          location=cfg.get("location"), tags=cfg.get("tags", []))
        out.append(rec)
        log(f"[catalog] single: {name}")
    except Exception as ex:
        log(f"[catalog] single error: {ex}")
    return out

def build_catalog():
    raw = []
    for key, cfg in SITE_MAP.items():
        mode = cfg.get("mode", "outlinks")
        if mode == "single":
            raw.extend(scrape_single(cfg))
        else:
            raw.extend(scrape_outlinks(cfg))

    # Dedupe broadly by (name + url domain)
    def kfn(x):
        nm = (x.get("name") or "").strip().lower()
        domain = domain_of(x.get("url") or "")
        return f"{nm}|{domain}" if nm and domain else None

    deduped = []
    seen = set()
    for x in raw:
        k = kfn(x)
        if not k or k in seen:
            continue
        seen.add(k)
        deduped.append(x)

    # Normalize buckets
    bucketed = {"programs": [], "experts": [], "institutions": []}
    for rec in deduped:
        t = (rec.get("__type") or "").lower()
        if t == "program":
            bucketed["programs"].append({
                "name": rec.get("name"),
                "category": "—",
                "description": "External resource from roadmap",
                "location": "—",
                "url": rec.get("url"),
                "image": rec.get("image"),
                "tags": rec.get("tags", [])
            })
        elif t == "expert":
            bucketed["experts"].append({
                "name": rec.get("name"),
                "specialty": "—",
                "location": rec.get("location") or "—",
                "rating": None,
                "url": rec.get("url"),
                "image": rec.get("image"),
                "tags": rec.get("tags", [])
            })
        else:
            bucketed["institutions"].append({
                "name": rec.get("name"),
                "focus": "Longevity / Clinic / Biotech",
                "location": rec.get("location") or "—",
                "url": rec.get("url"),
                "image": rec.get("image"),
                "tags": rec.get("tags", [])
            })

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "catalog.json").write_text(json.dumps(bucketed, indent=2), encoding="utf-8")
    log(f"[catalog] Wrote {len(bucketed['programs'])} programs, {len(bucketed['experts'])} experts, {len(bucketed['institutions'])} institutions")

# ---------------------------- CLI ----------------------------
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", type=str, default="longevity OR aging OR chronic disease treatment OR randomized trial")
    ap.add_argument("--build-catalog", action="store_true", help="Scrape and write output/data/catalog.json")
    args = ap.parse_args()

    build(args.query)            # evidence/news → items.json (sorted newest-first)
    if args.build_catalog:
        build_catalog()          # programs/experts/institutions → catalog.json
