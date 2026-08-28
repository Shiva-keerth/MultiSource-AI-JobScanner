"""
MultiSource JobScanner — RemoteOK Scraper
Free JSON API: https://remoteok.com/api
No authentication required.
"""
import requests
import time

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36"
    )
}

# Keywords to filter for AI/ML/Python roles from RemoteOK
AI_KEYWORDS = [
    "ai", "artificial intelligence", "machine learning", "ml",
    "llm", "nlp", "natural language", "generative ai", "genai",
    "python", "langchain", "rag", "prompt engineer", "chatbot",
    "deep learning", "neural", "transformer", "gpt", "openai",
    "backend", "fastapi", "data science",
]


def fetch_remoteok_jobs() -> list:
    """
    Fetch AI/ML/Python jobs from RemoteOK's free JSON API.
    Returns standardized job list.
    """
    print("\n  [RemoteOK] Fetching jobs from free API...")
    
    try:
        time.sleep(2)  # Rate limit courtesy
        r = requests.get("https://remoteok.com/api", headers=HEADERS, timeout=15)
        if r.status_code != 200:
            print(f"  [RemoteOK] API returned status {r.status_code}")
            return []
        
        data = r.json()
        
        # First element is metadata, skip it
        if isinstance(data, list) and len(data) > 0 and "id" not in data[0]:
            data = data[1:]
        
        jobs = []
        skipped = 0
        
        for item in data:
            if not isinstance(item, dict):
                continue
            
            position = item.get("position", "").strip()
            company = item.get("company", "").strip()
            description = item.get("description", "").strip()
            url = item.get("url", "").strip()
            tags = [t.lower() for t in item.get("tags", [])]
            date = item.get("date", "")
            
            if not position or not company:
                continue
            
            # Check if job is AI/ML/Python related via tags + title + description
            all_text = f"{position} {' '.join(tags)} {description[:500]}".lower()
            keyword_hits = sum(1 for kw in AI_KEYWORDS if kw in all_text)
            
            if keyword_hits < 2:
                skipped += 1
                continue
            
            # Build apply URL
            apply_url = url if url.startswith("http") else f"https://remoteok.com{url}"
            
            jobs.append({
                "title": position,
                "company": company,
                "description": description,
                "url": apply_url,
                "location": "Remote",
                "source": "remoteok",
                "date_posted": date,
                "tags": tags,
            })
        
        print(f"  [RemoteOK] Found {len(jobs)} AI/ML jobs (filtered {skipped} non-relevant)")
        return jobs
        
    except Exception as e:
        print(f"  [RemoteOK] Error: {e}")
        return []


if __name__ == "__main__":
    results = fetch_remoteok_jobs()
    for j in results[:5]:
        print(f"  {j['title']} @ {j['company']} — {j['url']}")
