"""
Send application email to SkillsCapital careers inbox
"""
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

config_dir = os.path.join(os.path.dirname(__file__), "config")
load_dotenv(os.path.join(config_dir, ".env"))

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

TO_EMAIL = "careers@skillscapital.io"
SUBJECT = "Application: Software Engineer Intern (AI/ML & Agentic AI) - Shiva Keerth"

BODY_HTML = """\
<html>
<body style="font-family: Arial, sans-serif; color: #222; line-height: 1.7; max-width: 650px;">

<p>Dear Hiring Team at SkillsCapital,</p>

<p>I recently applied for the <strong>Software Engineer Intern (AI/ML &amp; Agentic AI)</strong> position through LinkedIn and wanted to follow up directly. SkillsCapital is building an AI-Native Talent Intelligence Platform, and I believe my hands-on experience building similar systems makes me a strong fit for this role.</p>

<p><strong>Here is what I have built:</strong></p>

<ul>
  <li><strong>Dual-Domain Agentic RAG Platform</strong> — Built using LangGraph ReAct agents where each agent autonomously retrieves, reasons, and responds within its own domain. No human-in-the-loop needed.</li>
  <li><strong>Enterprise Knowledge Graph (Neo4j) with Graph-RAG</strong> — Structures unstructured data and grounds LLM responses to eliminate hallucinations through retrieval-augmented generation.</li>
  <li><strong>Voice AI Pipeline</strong> — Integrated Groq Whisper for speech-to-text with Llama-3.3-70B for end-to-end natural language query processing.</li>
</ul>

<p>These are not course projects — they are live and deployed on <strong>Streamlit Cloud</strong> and <strong>Hugging Face Spaces</strong>, available for anyone to try.</p>

<p><strong>Technical Stack:</strong> Python, FastAPI, LangChain, LangGraph, Docker, Neo4j, ChromaDB, FAISS, Groq API, Prompt Engineering</p>

<p>I am available to <strong>join immediately</strong> and am comfortable working <strong>fully remote</strong>. I am confident I can start contributing from Day 1 rather than requiring a lengthy onboarding period.</p>

<p>I would welcome the opportunity to discuss how my experience aligns with SkillsCapital's vision. I am happy to hop on a quick call at your convenience.</p>

<p>Thank you for your time and consideration.</p>

<p>
Best regards,<br>
<strong>Shiva Keerth</strong><br>
Email: gantishivakeerth@gmail.com<br>
Location: Ahmedabad, Gujarat<br>
LinkedIn: <a href="https://www.linkedin.com/in/shiva-keerth/">linkedin.com/in/shiva-keerth/</a>
</p>

</body>
</html>
"""

BODY_PLAIN = """
Dear Hiring Team at SkillsCapital,

I recently applied for the Software Engineer Intern (AI/ML & Agentic AI) position through LinkedIn and wanted to follow up directly.

Here is what I have built:
- Dual-Domain Agentic RAG Platform using LangGraph ReAct agents
- Enterprise Knowledge Graph (Neo4j) with Graph-RAG for hallucination-free responses
- Voice AI Pipeline using Groq Whisper + Llama-3.3-70B

These are live and deployed on Streamlit Cloud and Hugging Face Spaces.

I am available to join immediately and am comfortable working fully remote.

Best regards,
Shiva Keerth
Email: gantishivakeerth@gmail.com
"""

msg = MIMEMultipart("alternative")
msg["From"] = GMAIL_ADDRESS
msg["To"] = TO_EMAIL
msg["Subject"] = SUBJECT
msg["Reply-To"] = GMAIL_ADDRESS

msg.attach(MIMEText(BODY_PLAIN, "plain"))
msg.attach(MIMEText(BODY_HTML, "html"))

try:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.send_message(msg)
    print(f"[OK] Email sent to {TO_EMAIL} from {GMAIL_ADDRESS}")
except smtplib.SMTPAuthenticationError:
    print("[FAIL] Gmail authentication failed. Check App Password.")
except Exception as e:
    print(f"[FAIL] Email failed: {e}")
