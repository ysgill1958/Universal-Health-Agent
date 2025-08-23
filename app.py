import os
from datetime import datetime

OUTPUT_DIR = "output"

# Example posts - replace with your real agent loop
posts = [
    {"title": "AI in Healthcare: A Quick Overview", "filename": "post1.html", "content": "<p>AI is changing healthcare...</p>"},
    {"title": "Why Preventive Care Matters", "filename": "post2.html", "content": "<p>Prevention is better than cure...</p>"}
]

def save_post(title, filename, content):
    """Save an individual post as an HTML file."""
    with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
</head>
<body>
  <h1>{title}</h1>
  <div>{content}</div>
  <p><a href="index.html">⬅ Back to Home</a></p>
</body>
</html>""")

def build_index(posts):
    """Generate index.html linking to all posts."""
    links = "\n".join([f'<li><a href="{p["filename"]}">{p["title"]}</a></li>' for p in posts])
    with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Universal Health Agent</title>
</head>
<body>
  <h1>Universal Health Agent</h1>
  <p>Generated on {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}</p>
  <ul>
    {links}
  </ul>
</body>
</html>""")

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Generate posts
    for post in posts:
        save_post(post["title"], post["filename"], post["content"])

    # Generate homepage
    build_index(posts)

if __name__ == "__main__":
    main()
