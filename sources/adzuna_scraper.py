"""
MultiSource JobScanner — Adzuna Scraper (v2)
Fixes:
  - Now fetches FULL JD text by following redirect_url (catches hidden experience requirements)
  - Validates URL is live before including (filters stale/expired listings)
  - Company blacklist for large IT firms that always require experience
Free API: https://api.adzuna.com/v1/api/jobs/{country}/search/{page}
Requires free API key (250 calls/month on Trial Access).
"""
import os
import requests
import time
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load .env from config directory
config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
load_dotenv(os.path.join(config_dir, ".env"))

ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36"
    )
}

# ── Large IT companies that always require 3+ years even for "fresher" postings
ADZUNA_COMPANY_BLACKLIST = {
    "cognizant", "wipro", "tcs", "tata consultancy services",
    "infosys", "accenture", "capgemini", "hcltech", "hcl technologies",
    "mphasis", "ltimindtree", "hexaware", "tech mahindra", "virtusa",
    "exl", "exlservice", "ibm", "oracle", "deloitte", "kpmg",
    "pricewaterhousecoopers", "ey", "ernst & young",
    "jpmorgan", "jpmorgan chase", "goldman sachs", "morgan stanley",
    "palo alto networks", "cisco", "servicenow",
    "bristol myers squibb", "siemens",
}

# ── ATS selectors for fetching full JD from external pages
ATS_SELECTORS = [
    "div.job-description", "div#job-description", "div.description",
    "div#description", "div[class*='job-desc']", "div[class*='jobDesc']",
    "section.job-description", "article.job-description",
    "div[data-automation='jobAdDetails']",
    "div[class*='jobDetail']", "div[class*='job-detail']",
    "div.content", "main", "article",
]

# Search queries targeting AI/ML/Python fresher roles
SEARCH_QUERIES = [
    "AI engineer fresher",
    "Python developer junior",
    "machine learning engineer entry level",
    "generative AI developer",
    "LLM engineer",
    "NLP engineer junior",
    "backend Python engineer",
]

COUNTRIES = ["in"]


def fetch_full_jd(redirect_url: str) -> tuple:
    """
    Follow Adzuna redirect URL and scrape the full JD text.
    Returns (full_jd_text, final_url, is_live).
    """
    try:
        time.sleep(1.5)
        r = requests.get(redirect_url, headers=HEADERS, timeout=12, allow_redirects=True)
        
        # Check if page is alive
        if r.status_code == 404:
            return "", redirect_url, False
        if r.status_code != 200:
            return "", redirect_url, True  # Assume live if not 404
        
        final_url = r.url

        # Check for "page not found" in content
        page_lower = r.text.lower()
        not_found_signals = [
            "page not found", "job no longer", "position has been filled",
            "this job is no longer", "404", "expired", "no longer available",
            "this listing has expired",
        ]
        for signal in not_found_signals:
            if signal in page_lower[:3000]:  # Check only first 3000 chars
                return "", final_url, False

        soup = BeautifulSoup(r.text, "html.parser")

        # Remove noise elements
        for tag in soup.find_all(["nav", "header", "footer", "script", "style", "noscript"]):
            tag.decompose()

        # Try ATS-specific selectors first
        best_text = ""
        for selector in ATS_SELECTORS:
            try:
                el = soup.select_one(selector)
                if el:
                    t = el.get_text(separator=" ", strip=True)
                    if len(t) > len(best_text):
                        best_text = t
            except Exception:
                continue

        # Fallback: find the largest div/section
        if len(best_text) < 150:
            for tag in soup.find_all(["div", "section", "article"]):
                t = tag.get_text(separator=" ", strip=True)
                if 150 < len(t) < 15000 and len(t) > len(best_text):
                    best_text = t

        return best_text[:6000], final_url, True

    except requests.exceptions.ConnectionError:
        return "", redirect_url, False
    except Exception:
        return "", redirect_url, True


def fetch_adzuna_page(country: str, query: str, page: int = 1) -> list:
    """Fetch one page of results from Adzuna API."""
    url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "what": query,
        "results_per_page": 20,
        "max_days_old": 3,
        "sort_by": "date",
        "content-type": "application/json",
    }

    try:
        time.sleep(1)
        r = requests.get(url, params=params, headers=HEADERS, timeout=15)

        if r.status_code == 401:
            print("  [Adzuna] [FAIL] Authentication failed. Check APP_ID and APP_KEY in config/.env")
            return []
        if r.status_code == 429:
            print("  [Adzuna] [WARN] Rate limit hit. Free tier allows 250 calls/month.")
            return []
        if r.status_code != 200:
            print(f"  [Adzuna] API returned status {r.status_code}")
            return []

        data = r.json()
        return data.get("results", [])

    except Exception as e:
        print(f"  [Adzuna] Error: {e}")
        return []


def fetch_adzuna_jobs() -> list:
    """
    Fetch AI/ML/Python jobs from Adzuna free API.
    Now fetches FULL JD by following redirect URLs + validates liveness.
    Returns standardized job list with complete JD text.
    """
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        print("\n  [Adzuna] [WARN] API credentials not configured. Skipping Adzuna.")
        print("  [Adzuna] Get your free key at: https://developer.adzuna.com/")
        return []

    print(f"\n  [Adzuna] Fetching jobs ({len(SEARCH_QUERIES)} queries x {len(COUNTRIES)} countries)...")
    print(f"  [Adzuna] Will follow redirect URLs to fetch full JD text...")

    all_jobs = []
    seen_urls = set()
    api_calls_made = 0
    stale_skipped = 0
    blacklisted_skipped = 0

    for country in COUNTRIES:
        for query in SEARCH_QUERIES:
            results = fetch_adzuna_page(country, query, page=1)
            api_calls_made += 1

            for item in results:
                title = item.get("title", "").strip()
                company = item.get("company", {}).get("display_name", "Unknown").strip()
                short_desc = item.get("description", "").strip()
                redirect_url = item.get("redirect_url", "").strip()
                location = item.get("location", {}).get("display_name", "India").strip()
                created = item.get("created", "")

                # Deduplicate
                if redirect_url in seen_urls:
                    continue
                seen_urls.add(redirect_url)

                if not title or not redirect_url:
                    continue

                # Company blacklist check
                company_lower = company.lower().strip()
                if any(blocked in company_lower for blocked in ADZUNA_COMPANY_BLACKLIST):
                    blacklisted_skipped += 1
                    print(f"    [BLACKLIST] Skipping {company} — large IT firm (always needs 3+ yrs)")
                    continue

                # Follow redirect URL to get full JD + validate liveness
                safe_title = title.encode('ascii', 'ignore').decode('ascii')[:50]
                safe_company = company.encode('ascii', 'ignore').decode('ascii')[:30]
                print(f"    Fetching full JD: {safe_title} @ {safe_company}...")

                full_jd, final_url, is_live = fetch_full_jd(redirect_url)

                if not is_live:
                    stale_skipped += 1
                    print(f"      -> [STALE] Page no longer exists — skipping")
                    continue

                # Use full JD if we got it, otherwise fall back to short snippet
                description = full_jd if len(full_jd) > len(short_desc) else short_desc
                if not description:
                    description = short_desc

                all_jobs.append({
                    "title": title,
                    "company": company,
                    "description": description,
                    "url": final_url if final_url else redirect_url,
                    "location": location,
                    "source": "adzuna",
                    "date_posted": created,
                    "country": country,
                    "jd_length": len(description),
                })
                print(f"      -> Collected ({len(description)} chars JD)")

            # Conservative API call limit
            if api_calls_made >= 20:
                print(f"  [Adzuna] Reached conservative API call limit (20). Preserving free quota.")
                break

        if api_calls_made >= 20:
            break

    print(f"  [Adzuna] Found {len(all_jobs)} live jobs")
    print(f"  [Adzuna] Stale listings skipped: {stale_skipped} | Blacklisted companies: {blacklisted_skipped}")
    return all_jobs


if __name__ == "__main__":
    results = fetch_adzuna_jobs()
    for j in results[:5]:
        print(f"  {j['title']} @ {j['company']} — {j['location']} — JD: {j['jd_length']} chars")
