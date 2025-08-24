import os
import feedparser
from datetime import datetime
import math

# Feeds
FEEDS = {
    "Health": "https://www.sciencedaily.com/rss/health_medicine.xml",
    "Science": "https://www.sciencedaily.com/rss/top/health.xml",
    "AI": "https://www.sciencedaily.com/rss/computers_math/artificial_intelligence.xml",
    "Medicine": "https://www.sciencedaily.com/rss/health_medicine.xml"
}

# Setup folders
os.makedirs("output/posts", exist_ok=True)
open("output/.nojekyll", "w").close()

today = datetime.now().strftime("%Y-%m-%d")

# Group posts by date
posts_by_date = {}

def truncate(text, length=200):
    if not text:
        return "No summary available."
    return text[:length].rsplit(" ", 1)[0] + "..." if len(text) > length else text

# Scrape feeds
for category, url in FEEDS.items():
    feed = feedparser.parse(url)
    if not feed.entries:
        continue

    for entry in feed.entries[:2]:
        title = entry.title
        link = entry.link
        summary = entry.get("summary", "")
        preview = truncate(summary, 200)

        pub_date = getattr(entry, "published", today)
        pub_day = pub_date.split("T")[0] if "T" in pub_date else pub_date.split(" ")[0]

        slug = f"{pub_day}-{category.lower()}-{title[:40].replace(' ', '-')}"
        filename = f"output/posts/{slug}.html"

        post_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
</head>
<body>
  <h1>{title}</h1>
  <p><i>{category} • Published {pub_day}</i></p>
  <p>{summary}</p>
  <p>Read more: <a href="{link}" target="_blank">{link}</a></p>
  <br><a href="../index.html">← Back to Home</a>
</body>
</html>
"""
        with open(filename, "w", encoding="utf-8") as f:
            f.write(post_html)

        posts_by_date.setdefault(pub_day, []).append((title, slug, category, preview))

# Sort by most recent date
dates_sorted = sorted(posts_by_date.keys(), reverse=True)

# Pagination settings
DAYS_PER_PAGE = 5
total_pages = math.ceil(len(dates_sorted) / DAYS_PER_PAGE)

def build_index(page_num):
    start = (page_num - 1) * DAYS_PER_PAGE
    end = start + DAYS_PER_PAGE
    page_dates = dates_sorted[start:end]

    html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Universal Health Agent Blog</title>
</head>
<body>
  <h1>Universal Health Agent Blog</h1>
  <h2>Latest Breakthroughs</h2>
"""
    for pub_day in page_dates:
        html += f"<h3>{pub_day}</h3>\n<ul>\n"
        for title, slug, category, preview in posts_by_date[pub_day]:
            html += f"""  <li>[{category}] <a href="posts/{slug}.html">{title}</a><br>
      <small>{preview}</small></li>\n"""
        html += "</ul>\n"

    # Navigation
    html += "<p>"
    if page_num > 1:
        prev_file = "index.html" if page_num == 2 else f"page{page_num-1}.html"
        html += f'<a href="{prev_file}">← Prev</a> '
    if page_num < total_pages:
        next_file = f"page{page_num+1}.html"
        html += f'<a href="{next_file}">Next →</a>'
    html += "</p>"

    html += f"<p><i>Auto-updated on {today}</i></p>\n</body>\n</html>"
    return html

# Write pages
for page in range(1, total_pages + 1):
    filename = "output/index.html" if page == 1 else f"output/page{page}.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(build_index(page))

print(f"✅ Generated {sum(len(v) for v in posts_by_date.values())} posts across {total_pages} pages.")
