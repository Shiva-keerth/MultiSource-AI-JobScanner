"""
MultiSource JobScanner — Email Notification Module
Sends job alerts via Gmail SMTP (free, no third-party service needed).
"""
import os
import smtplib
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load .env from config directory
config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
load_dotenv(os.path.join(config_dir, ".env"))

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")


def send_job_alert(jobs: list, source_summary: str = "") -> bool:
    """
    Send an email alert with the list of qualified jobs.
    Returns True if email sent successfully, False otherwise.
    """
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        print("[NOTIFIER] Gmail credentials not configured. Skipping email.")
        return False

    if not jobs:
        print("[NOTIFIER] No jobs to notify about. Skipping email.")
        return False

    now = datetime.datetime.now().strftime("%d %b %Y, %I:%M %p")
    subject = f"🎯 JobScanner Alert: {len(jobs)} New AI Jobs Found! ({now})"

    # Build HTML email body
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 700px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    color: white; padding: 20px; border-radius: 10px; text-align: center;">
            <h1 style="margin: 0;">🎯 JobScanner Alert</h1>
            <p style="margin: 5px 0 0 0; opacity: 0.9;">{len(jobs)} New AI Engineer Opportunities Found</p>
            <p style="margin: 5px 0 0 0; opacity: 0.7; font-size: 12px;">{now}</p>
        </div>

        {f'<p style="color: #666; font-size: 13px; margin-top: 15px;">{source_summary}</p>' if source_summary else ''}
    """

    for i, job in enumerate(jobs, 1):
        score = job.get("match_score", job.get("score", 0))
        verdict = job.get("verdict", "N/A")
        company = job.get("company", "Unknown")
        title = job.get("title", "Unknown Role")
        url = job.get("url", job.get("apply_url", "#"))
        source = job.get("source", "unknown")
        reason = job.get("reason", "")
        exp = job.get("experience_required", "Not specified")
        decision = job.get("apply_decision", "APPLY")
        matched = ", ".join(job.get("matched_skills", [])[:6])
        missing = ", ".join(job.get("missing_skills", [])[:4])

        # Color coding based on score
        if score >= 80:
            badge_color = "#10b981"
            badge_text = "⭐ Strong Match"
        elif score >= 60:
            badge_color = "#f59e0b"
            badge_text = "✅ Good Fit"
        else:
            badge_color = "#ef4444"
            badge_text = "⚠️ Partial"

        # Source badge
        source_colors = {
            "remoteok": "#4f46e5",
            "hackernews": "#ff6600",
            "adzuna": "#00a98f",
        }
        src_color = source_colors.get(source, "#666")

        html_body += f"""
        <div style="border: 1px solid #e5e7eb; border-radius: 10px; padding: 18px; margin: 15px 0;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h3 style="margin: 0; color: #1f2937;">#{i}. {title}</h3>
            </div>
            <p style="margin: 5px 0; color: #6b7280;">
                <strong>{company}</strong>
                <span style="background: {src_color}; color: white; padding: 2px 8px; 
                      border-radius: 12px; font-size: 11px; margin-left: 8px;">{source.upper()}</span>
                <span style="background: {badge_color}; color: white; padding: 2px 8px; 
                      border-radius: 12px; font-size: 11px; margin-left: 5px;">Score: {score}</span>
            </p>
            <p style="margin: 8px 0 5px 0; font-size: 13px; color: #374151;">
                <strong>Experience:</strong> {exp} | <strong>Decision:</strong> {decision}
            </p>
            <p style="margin: 5px 0; font-size: 13px; color: #4b5563;">{reason[:200]}</p>
            {"<p style='margin: 5px 0; font-size: 12px; color: #059669;'><strong>Skills Match:</strong> " + matched + "</p>" if matched else ""}
            {"<p style='margin: 5px 0; font-size: 12px; color: #dc2626;'><strong>Missing:</strong> " + missing + "</p>" if missing else ""}
            <a href="{url}" style="display: inline-block; background: #4f46e5; color: white; 
               padding: 8px 20px; border-radius: 6px; text-decoration: none; margin-top: 10px;
               font-size: 13px;">Apply Now →</a>
        </div>
        """

    html_body += """
        <div style="text-align: center; margin-top: 25px; padding: 15px; 
                    background: #f3f4f6; border-radius: 8px;">
            <p style="margin: 0; color: #6b7280; font-size: 12px;">
                🤖 MultiSource JobScanner — Automated Job Discovery<br>
                Sources: RemoteOK | Hacker News | Adzuna
            </p>
        </div>
    </body>
    </html>
    """

    # Build email message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = GMAIL_ADDRESS  # Send to yourself

    # Plain text fallback
    plain_text = f"JobScanner Alert: {len(jobs)} new AI jobs found!\n\n"
    for i, job in enumerate(jobs, 1):
        plain_text += f"#{i}. {job.get('title', '?')} @ {job.get('company', '?')} "
        plain_text += f"(Score: {job.get('match_score', job.get('score', '?'))}) "
        plain_text += f"— {job.get('url', job.get('apply_url', ''))}\n"

    msg.attach(MIMEText(plain_text, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        print(f"[NOTIFIER] [OK] Email sent to {GMAIL_ADDRESS} with {len(jobs)} jobs!")
        return True
    except smtplib.SMTPAuthenticationError:
        print("[NOTIFIER] [FAIL] Gmail authentication failed! Check your App Password in config/.env")
        return False
    except Exception as e:
        print(f"[NOTIFIER] [FAIL] Email failed: {e}")
        return False
