import os
import feedparser
from datetime import datetime

# Feeds to track
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
    """Shorten text safely for preview."""
    if not text:
        return "No summary available."
    return text[:length].rsplit(" ", 1)[0] + "..." if len(text) > length else text

# Loop feeds
for category, url in FEEDS.items():
    feed = feedparser.parse(url)
    if not feed.entries:
        continue

    for entry in feed.entries[:2]:
        title = entry.title
        link = entry.link
        summary = entry.get("summary", "")
        preview = truncate(summary, 200)

        # Try to parse feed date, fallback to today
        pub_date = getattr(entry, "published", today)
        pub_day = pub_date.split("T")[0] if "T" in pub_date else pub_date.split(" ")[0]

        # Unique slug
        slug = f"{pub_day}-{category.lower()}-{title[:40].replace(' ', '-')}"
        filename = f"output/posts/{slug}.html"

        # Post page
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

        # Add to grouped list
        posts_by_date.setdefault(pub_day, []).append((title, slug, category, preview))

# Build homepage grouped by date
index_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Universal Health Agent Blog</title>
</head>
<body>
  <h1>Universal Health Agent Blog</h1>
  <h2>Latest Breakthroughs</h2>
"""

# Sort by most recent date
for pub_day in sorted(posts_by_date.keys(), reverse=True):
    index_html += f"<h3>{pub_day}</h3>\n<ul>\n"
    for title, slug, category, preview in posts_by_date[pub_day]:
        index_html += f"""  <li>[{category}] <a href="posts/{slug}.html">{title}</a><br>
      <small>{preview}</small></li>\n"""
    index_html += "</ul>\n"

index_html += f"<p><i>Auto-updated on {today}</i></p>\n</body>\n</html>"

with open("output/index.html", "w", encoding="utf-8") as f:
    f.write(index_html)

print(f"✅ Generated {sum(len(v) for v in posts_by_date.values())} posts across {len(posts_by_date)} dates.")
