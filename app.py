# app.py — Universal Beat (Aggressive evidence + Catalog + Archives)
# Local run:
#   pip install -r requirements.txt
#   python app.py --query "longevity OR aging OR chronic disease treatment" --build-catalog
# Archives: writes output/archive/<YYYY-MM>.html and output/archive/index.html

import os, re, json, time, hashlib, argparse, email.utils as eut, calendar
from time import mktime
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urljoin

import requests
import feedparser
from bs4 import BeautifulSoup

OUTPUT_DIR = Path("output")
DATA_DIR = OUTPUT_DIR / "data"
STATIC_DIR = OUTPUT_DIR / "static"
ARCHIVE_DIR = OUTPUT_DIR / "archive"
for p in (OUTPUT_DIR, DATA_DIR, STATIC_DIR, ARCHIVE_DIR):
    p.mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / ".nojekyll").write_text("")

def now_utc_str() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

def log(msg: str):
    line = f"[{now_utc_str()}] {msg}"
    print(line)
    try:
        with open(DATA_DIR / "logs.txt", "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:
        pass

def clean_text(s: str) -> str:
    if not s: return ""
    s = re.sub(r"<.*?>", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def truncate(s: str, n=360) -> str:
    s = clean_text(s)
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + "…"

def normalize_key(title: str, link: str) -> str:
    host = urlparse(link or "").netloc.lower()
    t = re.sub(r"\s+", " ", (title or "").lower()).strip()
    t = re.sub(r"[^a-z0-9 ]+", "", t)
    return hashlib.sha1(f"{host}|{t}".encode()).hexdigest()

HEADERS = {"User-Agent": "Mozilla/5.0 (UHA/2.1; +GitHub Pages Agent)"}

def get_og_image(url: str, timeout=8) -> str | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "lxml")
        for css, attr in [('meta[property="og:image"]',"content"),
                          ('meta[property="og:image:url"]',"content"),
                          ('meta[name="twitter:image"]',"content")]:
            m = soup.select_one(css)
            if m and m.get(attr):
                return urljoin(url, m.get(attr).strip())
        for img in soup.find_all("img", src=True):
            src = urljoin(url, img["src"])
            if any(bad in src for bad in ("data:","sprite","pixel","base64")): continue
            return src
    except Exception as ex:
        log(f"OG image fetch failed: {ex}")
    return None

def google_news_feed(query: str, lang="en-IN") -> str:
    return f"https://news.google.com/rss/search?q={requests.utils.quote(query)}&hl={lang}&gl=IN&ceid=IN:{lang.split('-')[0]}"

def pubmed_feed(query: str) -> str:
    return f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/erss.cgi?db=pubmed&term={requests.utils.quote(query)}&sort=date"

BASE_FEEDS = [
    ("NIH","https://www.nih.gov/news-events/news-releases/rss.xml"),
    ("WHO","https://www.who.int/feeds/entity/mediacentre/news/en/rss.xml"),
    ("CDC","https://tools.cdc.gov/api/v2/resources/media/403372.rss"),
    ("Cochrane News","https://www.cochrane.org/news-feed.xml"),
    ("Nature","https://www.nature.com/nature.rss"),
    ("BMJ","https://www.bmj.com/latest.xml"),
    ("Lancet","https://www.thelancet.com/rssfeed/lancet_current.xml"),
    ("PLOS Medicine","https://journals.plos.org/plosmedicine/feed/atom"),
    ("ScienceDaily Health","https://www.sciencedaily.com/rss/health_medicine.xml"),
    ("ScienceDaily Top","https://www.sciencedaily.com/rss/top.xml"),
    ("bioRxiv Latest","https://www.biorxiv.org/rss/latest.xml"),
    ("medRxiv Latest","https://www.medrxiv.org/rss/latest.xml"),
]

def parse_date(entry):
    for key in ("published_parsed","updated_parsed"):
        if entry.get(key):
            try:
                return datetime.utcfromtimestamp(mktime(entry[key])).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pass
    for key in ("published","updated","dc_date"):
        if entry.get(key):
            try:
                tt = eut.parsedate_to_datetime(entry[key])
                if tt.tzinfo: tt = tt.astimezone(timezone.utc).replace(tzinfo=None)
                return tt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                continue
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
        if delay > 0: time.sleep(delay)
    return items

def aggregate(query: str, per_feed_limit=80, max_total=700, thumb_budget=220, delay_between=0.4):
    feeds = [("Google News", google_news_feed(query)), ("PubMed", pubmed_feed(query))] + BASE_FEEDS if query else BASE_FEEDS[:]
    all_items = []
    for src, url in feeds:
        all_items.extend(fetch_feed(src, url, per_feed_limit, delay_between))

    seen, deduped = set(), []
    for it in all_items:
        k = normalize_key(it.get("title"), it.get("link"))
        if not it.get("title") or not it.get("link"): continue
        if k in seen: continue
        seen.add(k); deduped.append(it)
        if len(deduped) >= max_total: break

    log(f"After dedupe: {len(deduped)} items")

    for it in deduped:
        if thumb_budget <= 0: break
        img = get_og_image(it["link"])
        if img: it["image"] = img; thumb_budget -= 1

    deduped.sort(key=lambda x: x.get("date") or "", reverse=True)
    return deduped

def write_archives(items):
    """Create archive pages by month: output/archive/<YYYY-MM>.html and index.html"""
    # Group by YYYY-MM
    by_month = {}
    for it in items:
        d = (it.get("date") or "")[:10]
        ym = d[:7] if d else "unknown"
        by_month.setdefault(ym, []).append(it)

    # Month pages (Date • Headline)
    for ym, arr in by_month.items():
        arr.sort(key=lambda x: x.get("date") or "", reverse=True)
        year, month = ym.split("-") if ym != "unknown" else ("", "")
        title = f"Archive — {ym}" if ym != "unknown" else "Archive"
        lines = [
            "<!doctype html><meta charset='utf-8'><title>"+title+"</title>",
            "<style>body{font-family:system-ui,Arial;margin:20px;background:#f8f9fa;color:#212529}"
            "a{color:#0d6efd;text-decoration:none}a:hover{text-decoration:underline}"
            ".wrap{max-width:900px;margin:0 auto}.head{display:flex;justify-content:space-between;align-items:center}"
            "h1{margin:0 0 8px 0}.item{padding:6px 0;border-bottom:1px solid #e9ecef}"
            ".date{color:#6c757d;font-size:.9em;margin-right:8px}</style>",
            "<div class='wrap'>",
            f"<div class='head'><h1>{title}</h1><a href='../index.html'>← Home</a></div>",
            "<p>Items listed newest first. Headlines only.</p>"
        ]
        cur_day = None
        for it in arr:
            d = (it.get("date") or "")[:10]
            if d != cur_day:
                lines.append(f"<h3 style='margin:16px 0 6px'>{d}</h3>")
                cur_day = d
            title_txt = (it.get('title') or '').replace("<","&lt;").replace(">","&gt;")
            link = it.get('link') or '#'
            lines.append(f"<div class='item'><span class='date'>{it.get('date') or ''}</span><a target='_blank' href='{link}'>{title_txt}</a></div>")
        lines.append("</div>")
        (ARCHIVE_DIR / f"{ym}.html").write_text("\n".join(lines), encoding="utf-8")

    # Archive index
    months = sorted(by_month.keys(), reverse=True)
    idx = [
        "<!doctype html><meta charset='utf-8'><title>Archive</title>",
        "<style>body{font-family:system-ui,Arial;margin:20px;background:#f8f9fa;color:#212529}"
        "a{color:#0d6efd;text-decoration:none}a:hover{text-decoration:underline}"
        ".wrap{max-width:900px;margin:0 auto}.month{padding:8px 0;border-bottom:1px solid #e9ecef}</style>",
        "<div class='wrap'><h1>Archive</h1><p>Browse by month.</p><p><a href='../index.html'>← Home</a></p>"
    ]
    for ym in months:
        if ym == "unknown": continue
        y, m = ym.split("-")
        name = f"{calendar.month_name[int(m)]} {y}"
        idx.append(f"<div class='month'><a href='./{ym}.html'>{name}</a></div>")
    if "unknown" in months:
        idx.append("<div class='month'><a href='./unknown.html'>Unknown dates</a></div>")
    idx.append("</div>")
    (ARCHIVE_DIR / "index.html").write_text("\n".join(idx), encoding="utf-8")

def build(query: str):
    items = aggregate(query)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "items.json").write_text(json.dumps(items, indent=2), encoding="utf-8")
    # ensure placeholders exist
    if not (DATA_DIR / "catalog.json").exists():
        (DATA_DIR / "catalog.json").write_text(json.dumps({"programs": [], "experts": [], "institutions": []}, indent=2), encoding="utf-8")
    if not (DATA_DIR / "longevity_plan.json").exists():
        (DATA_DIR / "longevity_plan.json").write_text(json.dumps([], indent=2), encoding="utf-8")

    # archives (everything; homepage JS shows only 25)
    write_archives(items)

    (DATA_DIR / "logs.txt").write_text(
        f"Generated: {now_utc_str()}\nQuery: {query or '—'}\nItems: {len(items)}\n",
        encoding="utf-8")
    log(f"✅ Built {len(items)} items → output/data/items.json + archives")

# ---------------- Catalog scraping (same sources; unchanged logic) ----------------
def domain_of(u): 
    try: return urlparse(u).netloc.lower()
    except Exception: return ""

def is_external_link(page_url, href):
    if not href: return False
    return domain_of(page_url) != domain_of(href)

def guess_name_from_anchor(a_tag, href):
    txt = (a_tag.get_text(" ", strip=True) if a_tag else "")[:120]
    if txt and not txt.lower().startswith(("http://","https://")): return txt
    dom = domain_of(href)
    if dom.startswith("www."): dom = dom[4:]
    return dom or href

def make_record(kind, name, href, image=None, **extra):
    rec = {"name": name, "url": href, "image": image, "__type": kind}; rec.update(extra); return rec

SITE_MAP = {
    "scispot_top20_longevity_biotechs": {
        "mode": "outlinks","type": "institution",
        "url": "https://www.scispot.com/blog/top-20-of-most-innovative-anti-aging-companies-in-the-world",
        "container": "article, main, .blog-content, .prose",
        "tags": ["longevity","biotech","companies"]
    },
    "labiotech_top_biotech_companies": {
        "mode": "outlinks","type": "institution",
        "url": "https://www.labiotech.eu/best-biotech/anti-aging-biotech-companies/",
        "container": "article, main, .single-content, .article__content",
        "tags": ["longevity","biotech","companies"]
    },
    "longevity_clinic_top18": {
        "mode": "outlinks","type": "institution",
        "url": "https://longevity-clinic.co.uk/what-is-the-best-longevity-clinic-in-the-world/",
        "container": "article, main, .entry-content, .content",
        "tags": ["longevity","clinic","ranking"]
    },
    "lifespan_rejuvenation_roadmap": {
        "mode": "outlinks","type": "program",
        "url": "https://www.lifespan.io/road-maps/the-rejuvenation-roadmap/",
        "container": "article, main, #content, .entry-content, .wrap",
        "tags": ["rejuvenation","roadmap","programs"]
    },
    "dr_kalidas_center": {
        "mode": "single","type": "institution",
        "url": "https://drkalidas.com/",
        "name": "The Center for Natural & Integrative Medicine (Dr. Kalidas)",
        "location": "Orlando, Florida, USA",
        "tags": ["integrative","naturopathic","clinic"]
    },
}

def scrape_outlinks(cfg):
    out = []
    try:
        page_url = cfg["url"]
        r = requests.get(page_url, headers=HEADERS, timeout=25); r.raise_for_status()
        soup = BeautifulSoup(r.content, "lxml")
        container = None
        for sel in (cfg.get("container") or "").split(","):
            node = soup.select_one(sel.strip())
            if node: container = node; break
        if container is None: container = soup
        seen = set()
        for a in container.select("a[href]"):
            href = urljoin(page_url, a.get("href"))
            if not is_external_link(page_url, href): continue
            d = domain_of(href)
            if any(bad in d for bad in ("facebook.","twitter.","x.com","instagram.","linkedin.","pinterest.","reddit.")): continue
            key = (d, href.split("#")[0])
            if key in seen: continue
            seen.add(key)
            name = guess_name_from_anchor(a, href)
            img = get_og_image(href)
            out.append(make_record(cfg["type"], name, href, image=img, tags=cfg.get("tags", [])))
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
        out.append(make_record(cfg["type"], name, page_url, image=img, location=cfg.get("location"), tags=cfg.get("tags", [])))
        log(f"[catalog] single: {name}")
    except Exception as ex:
        log(f"[catalog] single error: {ex}")
    return out

def build_catalog():
    raw = []
    for _, cfg in SITE_MAP.items():
        raw.extend(scrape_single(cfg) if cfg.get("mode")=="single" else scrape_outlinks(cfg))
    # dedupe
    def kfn(x):
        nm = (x.get("name") or "").strip().lower()
        domain = domain_of(x.get("url") or "")
        return f"{nm}|{domain}" if nm and domain else None
    seen, deduped = set(), []
    for x in raw:
        k = kfn(x)
        if not k or k in seen: continue
        seen.add(k); deduped.append(x)
    bucketed = {"programs": [], "experts": [], "institutions": []}
    for rec in deduped:
        t = (rec.get("__type") or "").lower()
        if t == "program":
            bucketed["programs"].append({
                "name": rec.get("name"), "category": "—", "description": "External resource from roadmap",
                "location": "—", "url": rec.get("url"), "image": rec.get("image"), "tags": rec.get("tags", [])
            })
        elif t == "expert":
            bucketed["experts"].append({
                "name": rec.get("name"), "specialty": "—", "location": rec.get("location") or "—",
                "rating": None, "url": rec.get("url"), "image": rec.get("image"), "tags": rec.get("tags", [])
            })
        else:
            bucketed["institutions"].append({
                "name": rec.get("name"), "focus": "Longevity / Clinic / Biotech", "location": rec.get("location") or "—",
                "url": rec.get("url"), "image": rec.get("image"), "tags": rec.get("tags", [])
            })
    (DATA_DIR / "catalog.json").write_text(json.dumps(bucketed, indent=2), encoding="utf-8")
    log(f"[catalog] Wrote {len(bucketed['programs'])} programs, {len(bucketed['experts'])} experts, {len(bucketed['institutions'])} institutions")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", type=str, default="longevity OR aging OR chronic disease treatment OR randomized trial")
    ap.add_argument("--build-catalog", action="store_true", help="Scrape and write output/data/catalog.json")
    ap.add_argument("--weekly-only", action="store_true", help="Only build catalog on Sunday (UTC)")
    args = ap.parse_args()

    build(args.query)  # evidence/news → items.json + archives

    # Weekly directory scrape: only if requested AND it's Sunday UTC (weekday=6) or --weekly-only not set
    if args.build_catalog:
        if args.weekly_only:
            if datetime.utcnow().weekday() == 6:
                build_catalog()
            else:
                log("[catalog] Skipped (weekly-only; not Sunday UTC)")
        else:
            build_catalog()
