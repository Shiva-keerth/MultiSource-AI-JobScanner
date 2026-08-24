"""
MultiSource JobScanner — LLM Evaluator Module
Uses Groq API (GPT-OSS-120B primary, Qwen backup) for job evaluation.
"""
import os
import json
import time
from groq import Groq
from dotenv import load_dotenv

# Load .env from config directory
config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
load_dotenv(os.path.join(config_dir, ".env"))

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


CANDIDATE_PROFILE = """
Shiva Keerth — Generative AI Engineer | Agentic AI Developer
Location: Ahmedabad/Remote | Target: 0-2 YOE permanent roles | Target CTC: ₹8-12 LPA

TECHNICAL SKILLS:
LangChain, LangGraph, LangGraph ReAct agents, ChromaDB, FAISS, Neo4j, Neo4j Aura,
FastAPI, Docker, AWS EC2, Groq API, Llama-3.3-70B, Groq Whisper, RAG pipelines,
Graph RAG, GraphCypherQAChain, Pydantic, Supabase, SQLite, Python 3.10+,
Prompt Engineering, Multi-agent systems, Agentic AI, Knowledge Graphs,
Retrieval Augmented Generation, Vector databases, Embeddings, LLM fine-tuning,
Tavily Search, BeautifulSoup4, Playwright, Streamlit, APScheduler

PROJECTS:
OmniMind AI — Enterprise Knowledge Graph + Graph-RAG platform.
Stack: Neo4j Aura, LangChain GraphCypherQAChain, Groq Whisper STT,
Llama-3.3-70B inference, Pydantic data validation.
Deployed: Hugging Face Spaces. Repo: github.com/Shiva-keerth/OmniMind-AI-Enterprise

Dual-Domain Agentic RAG Platform — Production multi-agent system.
Stack: LangGraph ReAct agents, ChromaDB vector store, Tavily Search tool,
Docker containerization, AWS EC2 deployment.
Domains: Healthcare document QA + Financial data analysis.

SkillMatch AI — AI-powered workforce recommendation engine.
Stack: 6-signal TF-IDF scoring, 3-tier RBAC, Groq Llama-3, FastAPI backend,
Supabase database, Streamlit UI. 600-job dataset.

EXPERIENCE:
Infolabz Pvt. Ltd. — AI & Data Science Intern (8 months)
Data Analytics, Machine Learning pipelines, Python automation

EDUCATION:
B.Tech Information Technology — Indus University, Ahmedabad
CGPA: 9.57 | Graduated: May 2026
"""


EVALUATOR_PROMPT = """You are a strict Senior Technical Recruiter evaluating a job match.

CANDIDATE PROFILE:
{profile}

JOB TO EVALUATE:
Company: {company}
Role: {role}
Source: {source}
Full JD:
{jd_text}

INSTRUCTIONS — follow this exact order:

STEP 1 — MANDATORY EXPERIENCE CHECK (do this FIRST, before looking at skills):
Read the ENTIRE JD carefully and extract the experience requirement.
Look for phrases like "X years", "X+ years", "X-Y years", "X to Y years", "minimum X years",
"at least X years", "Exp: X", or any similar phrasing.

DISQUALIFY IMMEDIATELY (set "verdict" to "DISQUALIFIED" and "match_score" to 0) if ANY of these are true:
  a) The JD mentions ANY experience requirement of 2 or more years. Examples that MUST be disqualified:
     "2+ years", "3-6 years", "3 to 6 years", "5+ years", "2-3 years", "minimum 3 years".
     Even if the tech stack is a perfect match, you MUST still disqualify. NO EXCEPTIONS.
  b) The role title or JD implies Senior / Lead / Principal / Staff / Manager / Director level.
  c) The role is Contract / Freelance / Gig with no permanent track.

ONLY proceed to Step 2 if the experience requirement is 0-1 years, "fresher", "entry-level",
"new grad", or NOT mentioned at all.

STEP 2 — TECH STACK MATCH (only if Step 1 passed):
- List which of the candidate's skills directly appear or are implied in the JD.
- List any hard requirements in the JD that the candidate completely lacks.
- If the candidate lacks more than 3 hard requirements, set verdict to "Poor Fit".

STEP 3 — FINAL SCORE (only if Step 1 passed):
- Score 0-100 based on genuine skill overlap, not keyword presence.
- 80-100: Strong match, candidate should prioritize this application.
- 60-79: Good fit, worth applying with a tailored cover letter.
- 40-59: Partial fit, apply only if volume is low.
- Below 40: Poor fit, skip.

Respond ONLY with a valid JSON object. No preamble, no markdown, no explanation outside the JSON:
{{
  "match_score": <0-100 integer>,
  "verdict": "<DISQUALIFIED | Poor Fit | Partial Fit | Good Fit | Strong Match>",
  "experience_required": "<what the JD states or 'Not specified'>",
  "matched_skills": ["<skill1>", "<skill2>"],
  "missing_skills": ["<skill1>", "<skill2>"],
  "reason": "<2-3 sentences max explaining the score>"
}}"""


def evaluate_job(job: dict, jd_text: str) -> dict:
    """Evaluate a job against candidate profile using Groq LLM."""
    source = job.get("source", "unknown")

    prompt = EVALUATOR_PROMPT.format(
        profile=CANDIDATE_PROFILE,
        company=job.get("company", "Unknown"),
        role=job.get("title", "Unknown"),
        source=source,
        jd_text=jd_text[:1500]  # Groq context limit guard
    )

    # Model fallback chain
    models = ["openai/gpt-oss-120b", "qwen/qwen3.6-27b"]
    last_error = "Unknown error"

    for i, model in enumerate(models):
        try:
            start_time = time.time()
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
                temperature=0.1
            )
            latency_ms = (time.time() - start_time) * 1000
            raw = response.choices[0].message.content.strip()

            # Strip Qwen's <think>...</think> block
            if "<think>" in raw and "</think>" in raw:
                raw = raw.split("</think>")[-1].strip()

            # Strip markdown fences
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            result = json.loads(raw)

            print(f"      [LLM] {model} | {latency_ms:.0f}ms | Score: {result.get('match_score', '?')}")
            return result

        except json.JSONDecodeError as e:
            print(f"      [LLM] JSON parse failed on {model}. Trying next.")
            last_error = f"JSON parse failed: {e}"
            continue
        except Exception as e:
            print(f"      [LLM] {model} failed: {e}. Trying next.")
            last_error = str(e)
            continue

    print(f"      [LLM] All models failed for {job.get('title', '?')} @ {job.get('company', '?')}")
    return None
