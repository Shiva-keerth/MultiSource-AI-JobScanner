"""
MultiSource JobScanner — Hacker News "Who is Hiring" Scraper
Uses free HN Algolia API + Firebase API.
No authentication required.
"""
import requests
import re
import time
import html

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36"
    )
}

# AI/ML keywords to filter HN job comments
AI_KEYWORDS = [
    "python", "machine learning", "ml engineer", "ai engineer",
    "llm", "langchain", "langgraph", "generative ai", "genai",
    "nlp", "natural language", "rag", "retrieval augmented",
    "prompt engineer", "agentic", "chatbot", "fastapi",
    "deep learning", "neural network", "transformer",
    "gpt", "openai", "groq", "anthropic", "claude",
    "vector database", "chromadb", "pinecone", "weaviate",
    "knowledge graph", "neo4j", "backend engineer",
    "artificial intelligence", "data science",
]


def find_latest_hiring_thread() -> dict | None:
    """
    Find the most recent 'Ask HN: Who is hiring?' thread using Algolia search.
    Returns the thread metadata or None.
    """
    try:
        url = (
            "https://hn.algolia.com/api/v1/search?"
            "query=%22Ask%20HN%3A%20Who%20is%20hiring%22"
            "&tags=ask_hn"
            "&hitsPerPage=5"
        )
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return None

        data = r.json()
        hits = data.get("hits", [])

        # Find the most recent "Who is hiring" thread (exact title match)
        for hit in hits:
            title = hit.get("title", "").lower()
            if "who is hiring" in title and "ask hn" in title:
                return {
                    "id": hit["objectID"],
                    "title": hit["title"],
                    "created_at": hit.get("created_at", ""),
                    "num_comments": hit.get("num_comments", 0),
                }

        return None
    except Exception as e:
        print(f"  [HN] Error finding thread: {e}")
        return None


def parse_hn_comment(comment_text: str) -> dict:
    """
    Parse a raw HN job comment into structured data.
    HN job comments typically follow the format:
    CompanyName | Location | Role | Remote/Onsite | ...
    """
    # Unescape HTML entities
    text = html.unescape(comment_text)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    if len(text) < 50:
        return {}

    # Try to extract company name and role from first line
    lines = text.split("|")
    company = lines[0].strip() if len(lines) >= 1 else "Unknown"
    
    # Truncate company name if too long (it's probably the whole comment)
    if len(company) > 80:
        company = company[:80].rsplit(" ", 1)[0] + "..."

    # Try to find a role/title
    role = "Unknown Role"
    role_patterns = [
        r'(?:hiring|looking for|seeking)\s+(?:a\s+)?(.+?)(?:\.|,|\||\n)',
        r'(?:role|position|title)\s*:\s*(.+?)(?:\.|,|\||\n)',
    ]
    for pat in role_patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            role = match.group(1).strip()[:100]
            break

    # If we have pipe-separated header, second or third field is often the role
    if len(lines) >= 3:
        # Try to find which pipe-segment looks like a role title
        for segment in lines[1:4]:
            seg = segment.strip()
            if any(kw in seg.lower() for kw in ["engineer", "developer", "scientist", "intern", "lead", "manager"]):
                role = seg
                break

    # Extract apply URL if present
    url_match = re.search(r'(https?://\S+)', text)
    apply_url = url_match.group(1).rstrip(".,)") if url_match else ""

    # Extract location hints
    location = "Unknown"
    if len(lines) >= 2:
        loc_candidate = lines[1].strip()
        if len(loc_candidate) < 60:
            location = loc_candidate

    # Check for remote
    if re.search(r'\bremote\b', text, re.IGNORECASE):
        if location == "Unknown":
            location = "Remote"
        else:
            location += " / Remote"

    return {
        "company": company[:100],
        "title": role[:150],
        "description": text[:3000],
        "url": apply_url if apply_url else f"https://news.ycombinator.com/",
        "location": location,
        "source": "hackernews",
    }


def fetch_hn_jobs(max_comments: int = 200) -> list:
    """
    Fetch AI/ML/Python jobs from the latest HN 'Who is Hiring' thread.
    Returns standardized job list.
    """
    print("\n  [HN] Searching for latest 'Who is Hiring' thread...")

    thread = find_latest_hiring_thread()
    if not thread:
        print("  [HN] Could not find a recent 'Who is Hiring' thread.")
        return []

    thread_id = thread["id"]
    print(f"  [HN] Found: '{thread['title']}' ({thread['num_comments']} comments)")

    # Fetch thread details to get child comment IDs
    try:
        r = requests.get(
            f"https://hacker-news.firebaseio.com/v0/item/{thread_id}.json",
            headers=HEADERS, timeout=15
        )
        if r.status_code != 200:
            print(f"  [HN] Failed to fetch thread details.")
            return []

        thread_data = r.json()
        child_ids = thread_data.get("kids", [])[:max_comments]
        print(f"  [HN] Fetching {len(child_ids)} top-level comments...")

    except Exception as e:
        print(f"  [HN] Error fetching thread: {e}")
        return []

    # Fetch each top-level comment (each is a job posting)
    jobs = []
    ai_filtered = 0

    for idx, comment_id in enumerate(child_ids):
        try:
            time.sleep(0.1)  # Rate limit courtesy
            r = requests.get(
                f"https://hacker-news.firebaseio.com/v0/item/{comment_id}.json",
                headers=HEADERS, timeout=10
            )
            if r.status_code != 200:
                continue

            comment_data = r.json()
            if not comment_data or comment_data.get("deleted") or comment_data.get("dead"):
                continue

            comment_text = comment_data.get("text", "")
            if not comment_text or len(comment_text) < 50:
                continue

            # Quick AI keyword filter before parsing
            text_lower = html.unescape(re.sub(r'<[^>]+>', ' ', comment_text)).lower()
            keyword_hits = sum(1 for kw in AI_KEYWORDS if kw in text_lower)

            if keyword_hits < 2:
                ai_filtered += 1
                continue

            # Parse the comment into structured job data
            parsed = parse_hn_comment(comment_text)
            if parsed and parsed.get("description"):
                parsed["hn_comment_id"] = comment_id
                parsed["hn_thread_id"] = thread_id
                jobs.append(parsed)

        except Exception:
            continue

        # Progress indicator every 50 comments
        if (idx + 1) % 50 == 0:
            print(f"  [HN] Processed {idx + 1}/{len(child_ids)} comments...")

    print(f"  [HN] Found {len(jobs)} AI/ML jobs (filtered {ai_filtered} non-relevant)")
    return jobs


if __name__ == "__main__":
    results = fetch_hn_jobs(max_comments=100)
    for j in results[:5]:
        print(f"  {j['title']} @ {j['company']} — {j['location']}")
