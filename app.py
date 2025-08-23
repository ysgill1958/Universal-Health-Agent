import os
import re
from datetime import datetime

OUTPUT_DIR = "output"
POSTS_DIR = os.path.join(OUTPUT_DIR, "posts")

# Dummy agent output (replace with your loop later)
posts = [
    {"title": "My First Post", "content": "Hello from the Universal Agent!"},
    {"title": "Another Post", "content": "Second entry generated automatically."},
]

def slugify(title: str) -> str:
    """Make filename safe for URLs"""
    return re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')

def save_post(title: str, content: str):
    os.makedirs(POSTS_DIR, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{date_str}-{slugify(title)}.html"
    filepath = os.path.join(POSTS_DIR, filename)

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 40px; }}
    h1 {{ color: #2c3e50; }}
    a {{ color: #2980b9; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <p>{content}</p>
  <p><a href="../index.html">← Back to Home</a></p>
</body>
</html>
"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    return filename, title

def generate_index(posts_meta):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    links = "\n".join(
        [f'<li><a href="posts/{fname}">{title}</a></li>' for fname, title in posts_meta]
    )
    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Universal Health Agent Blog</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 40px; }}
    h1 {{ color: #16a085; }}
    ul {{ line-height: 1.8; }}
    li {{ margin-bottom: 8px; }}
    a {{ color: #2980b9; }}
  </style>
</head>
<body>
  <h1>Universal Health Agent Blog</h1>
  <ul>
    {links}
  </ul>
</body>
</html>
"""
    with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)

if __name__ == "__main__":
    posts_meta = [save_post(p["title"], p["content"]) for p in posts]
    generate_index(posts_meta)
    print(f"Generated {len(posts_meta)} posts and index.html")
