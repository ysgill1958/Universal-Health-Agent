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
posts_list = []

# Loop feeds
for category, url in FEEDS.items():
    feed = feedparser.parse(url)
    if not feed.entries:
        continue

    # Limit to first 2 articles
    for entry in feed.entries[:2]:
        title = entry.title
        link = entry.link
        summary = entry.get("summary", "No summary available.")

        # Unique slug
        slug = f"{today}-{category.lower()}-{title[:40].replace(' ', '-')}"
        filename = f"output/posts/{slug}.html"

        # Post HTML
        post_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
</head>
<body>
  <h1>{title}</h1>
  <p><i>{category} • Published {today}</i></p>
  <p>{summary}</p>
  <p>Read more: <a href="{link}" target="_blank">{link}</a></p>
  <br><a href="../index.html">← Back to Home</a>
</body>
</html>
"""
        with open(filename, "w", encoding="utf-8") as f:
            f.write(post_html)

        posts_list.append((title, slug, category))

# Generate homepage
index_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Universal Health Agent Blog</title>
</head>
<body>
  <h1>Universal Health Agent Blog</h1>
  <h2>Latest Breakthroughs</h2>
  <ul>
"""
for title, slug, category in posts_list:
    index_html += f'    <li>[{category}] <a href="posts/{slug}.html">{title}</a></li>\n'

index_html += """  </ul>
  <p><i>Auto-updated on {}</i></p>
</body>
</html>
""".format(today)

with open("output/index.html", "w", encoding="utf-8") as f:
    f.write(index_html)

print(f"✅ Generated {len(posts_list)} posts and updated homepage.")
