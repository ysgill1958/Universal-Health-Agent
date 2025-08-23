import os
from datetime import datetime

# Ensure posts folder exists
os.makedirs("posts", exist_ok=True)

# Example post content
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
post_filename = f"posts/post_{now.replace(':','-').replace(' ','_')}.html"

with open(post_filename, "w") as f:
    f.write(f"""
    <html>
    <head><title>Test Post</title></head>
    <body>
        <h1>Post generated at {now}</h1>
        <p>This is a dummy generated post.</p>
    </body>
    </html>
    """)

# Generate homepage index
posts = sorted(os.listdir("posts"))
with open("index.html", "w") as f:
    f.write("<html><head><title>Homepage</title></head><body>")
    f.write("<h1>Posts</h1><ul>")
    for post in posts:
        f.write(f'<li><a href="posts/{post}">{post}</a></li>')
    f.write("</ul></body></html>")
