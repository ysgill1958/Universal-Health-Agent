import os
from datetime import datetime

def run_agent_loop():
    # Dummy agent loop for now
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    post_html = f"""
    <html>
      <head>
        <title>Universal Health Agent</title>
      </head>
      <body>
        <h1>Universal Health Agent - Demo</h1>
        <p>This page was generated automatically at {now} UTC.</p>
        <p>Each run of GitHub Actions will update this page.</p>
      </body>
    </html>
    """
    return post_html

if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)
    with open("output/index.html", "w", encoding="utf-8") as f:
        f.write(run_agent_loop())
    print("✅ HTML generated in /output/index.html")
