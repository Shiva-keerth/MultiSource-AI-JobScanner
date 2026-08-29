"""
╔══════════════════════════════════════════════════════════════╗
║          MultiSource JobScanner — Main Runner                ║
║  Sources: RemoteOK | Hacker News | Adzuna                    ║
║  Filters: Role Whitelist → Experience Regex → LLM Eval       ║
║  Output:  Ranked JSON + Email Notification                   ║
╚══════════════════════════════════════════════════════════════╝
"""
import os
import sys
import json
import time
import datetime
import io

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from sources.remoteok_scraper import fetch_remoteok_jobs
from sources.hackernews_scraper import fetch_hn_jobs
from sources.adzuna_scraper import fetch_adzuna_jobs
from core.filters import (
    is_role_allowed, pre_filter_experience, is_blacklisted,
    has_aggregator_signals, analyze_apply_decision, quick_keyword_filter
)
from core.evaluator import evaluate_job
from core.notifier import send_job_alert


# ── Load previous results to avoid duplicates ──
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

def load_previous_results() -> set:
    """Load all previously found job URLs to avoid duplicates."""
    seen = set()
    for f in os.listdir(RESULTS_DIR):
        if f.endswith(".json"):
            try:
                with open(os.path.join(RESULTS_DIR, f), "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                    for job in data:
                        url = job.get("url", job.get("apply_url", "")).strip()
                        if url:
                            seen.add(url)
            except Exception:
                continue
    return seen


def run_scanner():
    """Main scanning pipeline."""
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    
    print(f"{'='*65}")
    print(f"  MULTISOURCE JOBSCANNER — Scan at {now.strftime('%d %b %Y, %I:%M %p')}")
    print(f"  Sources: RemoteOK (free API) | HN Who is Hiring | Adzuna (free API)")
    print(f"  Filters: Role Whitelist → Experience Regex → Groq LLM Eval")
    print(f"{'='*65}")

    # Load exclusions
    seen_urls = load_previous_results()
    print(f"\n  Loaded {len(seen_urls)} previously found job URLs for deduplication.")

    # ═══════════════════════════════════════════════
    #  STEP 1: Fetch from all sources
    # ═══════════════════════════════════════════════
    print(f"\n{'─'*50}")
    print(f"  STEP 1: Fetching from all sources...")
    print(f"{'─'*50}")

    remoteok_jobs = fetch_remoteok_jobs()
    hn_jobs = fetch_hn_jobs(max_comments=200)
    adzuna_jobs = fetch_adzuna_jobs()

    all_raw = remoteok_jobs + hn_jobs + adzuna_jobs
    print(f"\n  Total raw jobs fetched: {len(all_raw)}")
    print(f"    RemoteOK: {len(remoteok_jobs)} | HN: {len(hn_jobs)} | Adzuna: {len(adzuna_jobs)}")

    # ═══════════════════════════════════════════════
    #  STEP 2: Deduplicate
    # ═══════════════════════════════════════════════
    print(f"\n{'─'*50}")
    print(f"  STEP 2: Deduplication...")
    print(f"{'─'*50}")

    deduped = []
    seen_keys = set()
    for job in all_raw:
        url = job.get("url", "").strip()
        dedup_key = f"{job.get('company', '').lower().strip()}|{job.get('title', '').lower().strip()}"

        if url in seen_urls:
            continue
        if dedup_key in seen_keys:
            continue

        seen_urls.add(url)
        seen_keys.add(dedup_key)
        deduped.append(job)

    print(f"  After dedup: {len(deduped)} unique jobs (removed {len(all_raw) - len(deduped)} duplicates)")

    # ═══════════════════════════════════════════════
    #  STEP 3: Role filter
    # ═══════════════════════════════════════════════
    print(f"\n{'─'*50}")
    print(f"  STEP 3: Role title filtering...")
    print(f"{'─'*50}")

    role_filtered = []
    role_rejected = 0
    for job in deduped:
        title = job.get("title", "")
        
        # For HN jobs, if title is "Unknown Role", use keyword filter on description
        if title in ["Unknown Role", ""] and job.get("source") == "hackernews":
            if quick_keyword_filter(job.get("description", "")):
                role_filtered.append(job)
            else:
                role_rejected += 1
            continue
        
        if is_blacklisted(job.get("company", "")):
            role_rejected += 1
            continue

        role_ok, reason = is_role_allowed(title)
        if role_ok:
            role_filtered.append(job)
        else:
            role_rejected += 1
            safe_title = title.encode('ascii', 'ignore').decode('ascii')[:60]
            # Only print first 20 rejections to avoid spam
            if role_rejected <= 20:
                print(f"    [SKIP] '{safe_title}' — {reason}")
            elif role_rejected == 21:
                print(f"    ... (suppressing further role filter logs)")

    print(f"  After role filter: {len(role_filtered)} jobs (rejected {role_rejected})")

    # ═══════════════════════════════════════════════
    #  STEP 4: Experience pre-filter
    # ═══════════════════════════════════════════════
    print(f"\n{'─'*50}")
    print(f"  STEP 4: Experience pre-filter (regex)...")
    print(f"{'─'*50}")

    exp_filtered = []
    exp_rejected = 0
    for job in role_filtered:
        jd_text = job.get("description", "")
        title = job.get("title", "")
        
        if has_aggregator_signals(jd_text):
            exp_rejected += 1
            continue

        is_filtered, match_str = pre_filter_experience(jd_text, title)
        if is_filtered:
            exp_rejected += 1
            safe_title = title.encode('ascii', 'ignore').decode('ascii')[:50]
            if exp_rejected <= 15:
                print(f"    [EXP] '{safe_title}' — matched: '{match_str}'")
            elif exp_rejected == 16:
                print(f"    ... (suppressing further experience filter logs)")
        else:
            exp_filtered.append(job)

    print(f"  After experience filter: {len(exp_filtered)} jobs (rejected {exp_rejected})")

    # ═══════════════════════════════════════════════
    #  STEP 5: LLM Evaluation (Groq)
    # ═══════════════════════════════════════════════
    print(f"\n{'─'*50}")
    print(f"  STEP 5: LLM Evaluation via Groq...")
    print(f"{'─'*50}")

    qualified_jobs = []
    llm_rejected = 0

    for i, job in enumerate(exp_filtered):
        jd_text = job.get("description", "")
        title = job.get("title", "Unknown")
        company = job.get("company", "Unknown")
        source = job.get("source", "unknown")

        safe_title = title.encode('ascii', 'ignore').decode('ascii')[:50]
        safe_company = company.encode('ascii', 'ignore').decode('ascii')[:30]
        print(f"\n    [{i+1}/{len(exp_filtered)}] Evaluating: {safe_title} @ {safe_company} [{source}]")

        eval_res = evaluate_job(job, jd_text)

        if not eval_res:
            print(f"      -> Skipped (LLM error)")
            continue

        score = eval_res.get("match_score", 0)
        verdict = eval_res.get("verdict", "")

        if verdict in ["DISQUALIFIED", "BLACKLISTED"] or score < 60:
            llm_rejected += 1
            print(f"      -> Rejected (Score: {score}, Verdict: {verdict})")
            continue

        # Skill gap analysis
        missing_skills = eval_res.get("missing_skills", [])
        apply_decision, apply_reason = analyze_apply_decision(missing_skills)

        qualified_jobs.append({
            "title": title,
            "company": company,
            "url": job.get("url", ""),
            "location": job.get("location", "Unknown"),
            "source": source,
            "match_score": score,
            "verdict": verdict,
            "reason": eval_res.get("reason", ""),
            "experience_required": eval_res.get("experience_required", "Not specified"),
            "matched_skills": eval_res.get("matched_skills", []),
            "missing_skills": missing_skills,
            "apply_decision": apply_decision,
            "apply_reason": apply_reason,
            "scanned_at": now.isoformat(),
        })

        print(f"      -> ✅ QUALIFIED! Score: {score} | {verdict} | {apply_decision}")
        print(f"         #{len(qualified_jobs)} collected")

        time.sleep(0.5)  # Groq rate limit buffer

    # ═══════════════════════════════════════════════
    #  STEP 6: Sort, Save, Notify
    # ═══════════════════════════════════════════════
    qualified_jobs.sort(key=lambda x: x["match_score"], reverse=True)

    print(f"\n\n{'='*65}")
    print(f"  SCAN COMPLETE — {now.strftime('%d %b %Y, %I:%M %p')}")
    print(f"{'='*65}")
    print(f"  Raw jobs fetched:     {len(all_raw)}")
    print(f"  After dedup:          {len(deduped)}")
    print(f"  After role filter:    {len(role_filtered)}")
    print(f"  After exp filter:     {len(exp_filtered)}")
    print(f"  LLM rejected:         {llm_rejected}")
    print(f"  ✅ QUALIFIED:          {len(qualified_jobs)}")
    print(f"{'='*65}")

    # Print results
    if qualified_jobs:
        print(f"\n  🎯 TOP QUALIFIED JOBS:\n")
        for i, job in enumerate(qualified_jobs, 1):
            src_emoji = {"remoteok": "🌐", "hackernews": "🟠", "adzuna": "🟢"}.get(job["source"], "📋")
            print(f"  --- #{i} [{src_emoji} {job['source'].upper()}] ---")
            print(f"    Role:       {job['title']}")
            print(f"    Company:    {job['company']}")
            print(f"    Location:   {job['location']}")
            print(f"    Score:      {job['match_score']}")
            print(f"    Verdict:    {job['verdict']}")
            print(f"    Experience: {job['experience_required']}")
            print(f"    Decision:   {job['apply_decision']}")
            print(f"    Reason:     {job['reason'][:150]}")
            skills = ', '.join(job['matched_skills'][:6])
            missing = ', '.join(job['missing_skills'][:4])
            print(f"    Skills OK:  {skills if skills else 'N/A'}")
            print(f"    Missing:    {missing if missing else 'None'}")
            print(f"    LINK:       {job['url']}")
            print()
    else:
        print("\n  No qualified jobs found in this scan. Will try again next cycle.")

    # Save results
    output_file = os.path.join(RESULTS_DIR, f"scan_{timestamp}.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(qualified_jobs, f, indent=2, ensure_ascii=False)
    print(f"  Results saved to: {output_file}")

    # Send email notification
    if qualified_jobs:
        source_summary = (
            f"Sources scanned: RemoteOK ({len(remoteok_jobs)} raw) | "
            f"HN ({len(hn_jobs)} raw) | Adzuna ({len(adzuna_jobs)} raw). "
            f"After all filters: {len(qualified_jobs)} qualified."
        )
        send_job_alert(qualified_jobs, source_summary)
    else:
        print("  [NOTIFIER] No qualified jobs — skipping email notification.")

    apply_count = sum(1 for j in qualified_jobs if j['apply_decision'] == 'APPLY')
    skip_count = sum(1 for j in qualified_jobs if j['apply_decision'] == 'SKIP')
    print(f"\n  FINAL: {apply_count} to APPLY | {skip_count} to SKIP")
    
    return qualified_jobs


if __name__ == "__main__":
    run_scanner()
