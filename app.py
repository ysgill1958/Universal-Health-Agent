import os
import datetime
import traceback
import requests
import feedparser

# Ensure output folder exists
OUTPUT_DIR = "output"
POSTS_DIR = os.path.join(OUTPUT_DIR, "posts")
os.makedirs(POSTS_DIR, exist_ok=True)

def log_message(message):
    """Append logs into logs.html and print for GitHub Actions"""
    print(message)
    with open(os.path.join(OUTPUT_DIR, "logs.html"), "a", encoding="utf-8") as f:
        f.write(f"<p>{datetime.datetime.now()} - {message}</p>\n")

def fetch_breakthroughs():
    """Fetch latest science/health breakthroughs from Google News RSS"""
    feeds = [
        "https://news.google.com/rss/search?q=medical+breakthrough&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=health+innovation&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=science+discovery&hl=en-IN&gl=IN&ceid=IN:en",
    ]
    items = []
    try:
        for url in feeds:
            d = feedparser.parse(requests.get(url, timeout=10).content)
            for entry in d.entries[:3]:  # take top 3 per feed
                items.append(f"<li><a href='{entry.link}' target='_blank'>{entry.title}</a></li>")
        return items
    except Exception as e:
        log_message(f"⚠️ Could not fetch RSS feeds: {e}")
        return ["<li>No live breakthroughs available today.</li>"]

try:
    today = datetime.date.today().isoformat()

    # Generate breakthroughs list
    breakthroughs = fetch_breakthroughs()

    # Generate a daily blog post
    post_filename = f"{today}-daily-update.html"
    post_path = os.path.join(POSTS_DIR, post_filename)

    post_content = f"""
    <html>
    <head><title>Daily Health Update - {today}</title></head>
    <body>
    <h1>Daily Health Update - {today}</h1>
    <p>This is the automatically generated blog post for {today}.</p>

    <h2>Latest Health & Science Breakthroughs</h2>
    <ul>
    {''.join(breakthroughs)}
    </ul>

    <p>Future versions will include Universal Health Agent reports, news, and health tips.</p>
    </body>
    </html>
    """

    with open(post_path, "w", encoding="utf-8") as f:
        f.write(post_content.strip())

    log_message(f"✅ Generated blog post: {post_filename}")

    # Generate/Update index.html
    posts_list = []
    for fname in sorted(os.listdir(POSTS_DIR), reverse=True):
        if fname.endswith(".html"):
            posts_list.append(f'<li><a href="posts/{fname}">{fname}</a></li>')

    index_content = f"""
    <html>
    <head><title>Universal Health Agent Blog</title></head>
    <body>
    <h1>Universal Health Agent Blog</h1>
    <ul>
    {''.join(posts_list)}
    </ul>
    <p><a href="logs.html">View build logs</a></p>
    </body>
    </html>
    """

    with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_content.strip())

    log_message("✅ index.html updated successfully")

except Exception as e:
    error_msg = f"❌ Error: {str(e)}"
    log_message(error_msg)
    log_message(traceback.format_exc())

