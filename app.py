import os
import datetime
import feedparser

OUTPUT_DIR = "output"

def fetch_latest_breakthroughs():
    feeds = [
        "https://www.sciencedaily.com/rss/top.xml",
        "https://www.nature.com/subjects/artificial-intelligence.rss",
        "https://rss.nytimes.com/services/xml/rss/nyt/Health.xml"
    ]
    posts = []
    for url in feeds:
        try:
            d = feedparser.parse(url)
            for entry in d.entries[:2]:  # take 2 per feed
                posts.append({
                    "title": entry.title,
                    "link": entry.link,
                    "summary": getattr(entry, "summary", "")[:200]
                })
        except Exception as e:
            print(f"⚠️ Error fetching {url}: {e}")
    return posts

def build_site():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    today = datetime.date.today().isoformat()

    posts = fetch_latest_breakthroughs()

    if not posts:  # fallback if feeds fail
        posts_html = "<p>No latest breakthroughs available today. Check back later!</p>"
    else:
        posts_html = "".join([
            f"<li><a href='{p['link']}' target='_blank'>{p['title']}</a><br>{p['summary']}</li>"
            for p in posts
        ])

    html = f"""
    <html>
      <head>
        <title>Universal Health Agent Blog</title>
        <meta charset="utf-8"/>
      </head>
      <body>
        <h1>Universal Health Agent Blog</h1>
        <h2>Daily Health Update - {today}</h2>
        <ul>
          {posts_html}
        </ul>
      </body>
    </html>
    """

    with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)

if __name__ == "__main__":
    build_site()
    print("✅ Site generated successfully in 'output/'")
