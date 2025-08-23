import os
from datetime import datetime

# Folders
os.makedirs("posts", exist_ok=True)
os.makedirs("static/images", exist_ok=True)

# Example posts (with optional image)
posts = [
    {
        "title": "Health Tip: Stay Hydrated",
        "content": "Drink at least 8 glasses of water a day to maintain energy and focus.",
        "image": "hydration.jpg"   # Put file inside static/images/
    },
    {
        "title": "AI in Healthcare",
        "content": "AI agents are helping doctors detect diseases earlier with better accuracy.",
        "image": "ai-healthcare.png"
    },
    {
        "title": "Daily Wellness Reminder",
        "content": "Take a short walk every 2 hours to improve blood circulation.",
        "image": None   # post without image
    },
]

# Generate post pages
generated_files = []
for i, post in enumerate(posts, 1):
    slug = f"post-{datetime.now().strftime('%Y-%m-%d')}-{i}.html"
    filepath = os.path.join("posts", slug)
    generated_files.append((slug, post["title"]))

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{post["title"]}</title>
    <link rel="stylesheet" href="../static/style.css">
</head>
<body>
    <div class="container">
        <h1>{post["title"]}</h1>
        <p><em>{datetime.now().strftime('%B %d, %Y')}</em></p>
        {"<img src='../static/images/" + post["image"] + "' alt='Post image' class='post-image'>" if post["image"] else ""}
        <div class="content">{post["content"]}</div>
        <p><a href="../index.html">← Back to homepage</a></p>
    </div>
</body>
</html>""")

# Generate homepage
with open("index.html", "w", encoding="utf-8") as f:
    f.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Universal Health Agent Blog</title>
    <link rel="stylesheet" href="static/style.css">
</head>
<body>
    <div class="container">
        <h1>Universal Health Agent Blog</h1>
        <p>Auto-generated updates from the agent loop.</p>
        <ul>
            {''.join([f'<li><a href="posts/{slug}">{title}</a></li>' for slug, title in generated_files])}
        </ul>
    </div>
</body>
</html>""")

# Add CSS if not present
if not os.path.exists("static/style.css"):
    with open("static/style.css", "w") as f:
        f.write("""
body {
    font-family: Arial, sans-serif;
    background: #f9f9f9;
    margin: 0;
    padding: 0;
}
.container {
    max-width: 700px;
    margin: auto;
    background: #fff;
    padding: 20px;
    border-radius: 8px;
}
h1 { color: #2c3e50; }
a { color: #0077cc; text-decoration: none; }
a:hover { text-decoration: underline; }
ul { list-style-type: none; padding: 0; }
li { margin: 10px 0; }
.post-image {
    max-width: 100%;
    margin: 20px 0;
    border-radius: 6px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.2);
}
""")
