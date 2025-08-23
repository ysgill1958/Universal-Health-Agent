from fastapi import FastAPI, BackgroundTasks
import os, requests, random

app = FastAPI()

# --------------------------
# Config (Railway secrets / .env)
# --------------------------
WP_URL = os.getenv("WP_URL")  # e.g. https://yourwebsite.com/wp-json/wp/v2/posts
WP_USER = os.getenv("WP_USER")
WP_APP_PASS = os.getenv("WP_APP_PASS")

NOTION_API_URL = "https://api.notion.com/v1/pages"
NOTION_DB_ID = os.getenv("NOTION_DB_ID")  # Notion database ID
NOTION_TOKEN = os.getenv("NOTION_TOKEN")  # Integration token

GENERIC_API_URL = os.getenv("GENERIC_API_URL")  # optional
GENERIC_API_KEY = os.getenv("GENERIC_API_KEY")

# Dummy dataset
EVIDENCE_DATA = [
    {
        "title": "Yoga improves lung health",
        "content": "Daily yoga improved respiratory health in a clinical trial.",
        "image_url": "https://picsum.photos/600/400?yoga"
    },
    {
        "title": "Turmeric reduces inflammation",
        "content": "Turmeric was shown to lower inflammation markers significantly.",
        "image_url": "https://picsum.photos/600/400?turmeric"
    },
    {
        "title": "AI in early cancer detection",
        "content": "AI tools now outperform traditional methods in detecting early-stage cancers.",
        "image_url": "https://picsum.photos/600/400?cancer"
    }
]

# --------------------------
# Target Posting Functions
# --------------------------

def post_to_wordpress(evidence):
    """Publish evidence to WordPress with image."""
    if not WP_URL or not WP_USER or not WP_APP_PASS:
        return {"skipped": "WordPress not configured"}
    
    # Upload image
    img_resp = requests.get(evidence["image_url"])
    headers = {"Content-Disposition": f'attachment; filename="image.jpg"'}
    media = requests.post(
        WP_URL.replace("posts", "media"),
        auth=(WP_USER, WP_APP_PASS),
        headers=headers,
        files={"file": ("image.jpg", img_resp.content, "image/jpeg")},
    )
    media_id = media.json().get("id", None)

    # Create post
    data = {
        "title": evidence["title"],
        "content": evidence["content"],
        "status": "publish",
        "featured_media": media_id,
    }
    r = requests.post(WP_URL, auth=(WP_USER, WP_APP_PASS), json=data)
    return r.json()

def post_to_notion(evidence):
    """Save evidence in Notion DB."""
    if not NOTION_DB_ID or not NOTION_TOKEN:
        return {"skipped": "Notion not configured"}
    
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    data = {
        "parent": {"database_id": NOTION_DB_ID},
        "properties": {
            "Title": {"title": [{"text": {"content": evidence["title"]}}]},
            "Content": {"rich_text": [{"text": {"content": evidence["content"]}}]}
        }
    }
    r = requests.post(NOTION_API_URL, headers=headers, json=data)
    return r.json()

def post_to_generic_api(evidence):
    """Send evidence to any REST API."""
    if not GENERIC_API_URL:
        return {"skipped": "Generic API not configured"}
    
    headers = {"Authorization": f"Bearer {GENERIC_API_KEY}"} if GENERIC_API_KEY else {}
    r = requests.post(GENERIC_API_URL, json=evidence, headers=headers)
    return r.json()

# --------------------------
# Agent Loop
# --------------------------

def agent_loop():
    evidence = random.choice(EVIDENCE_DATA)

    results = {
        "wordpress": post_to_wordpress(evidence),
        "notion": post_to_notion(evidence),
        "generic_api": post_to_generic_api(evidence)
    }

    return {"selected_evidence": evidence, "results": results}

# --------------------------
# FastAPI Endpoints
# --------------------------

@app.get("/")
def root():
    return {"status": "ok", "message": "Universal Health Agent running!"}

@app.get("/run-once")
def run_once():
    """Trigger loop and post everywhere configured."""
    return agent_loop()

@app.post("/background-run")
def run_background(background_tasks: BackgroundTasks):
    background_tasks.add_task(agent_loop)
    return {"status": "started"}

@app.get("/health")
def health():
    return {"status": "healthy"}
