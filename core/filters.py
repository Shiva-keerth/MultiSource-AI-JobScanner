"""
MultiSource JobScanner — Filters Module
Ported from Jobline Pipeline with all existing filter logic.
"""
import re


# ── ROLE TITLE WHITELIST ──
ALLOWED_ROLE_KEYWORDS = [
    "ai engineer", "gen ai", "genai", "generative ai", "llm engineer",
    "llm developer", "agentic", "prompt engineer", "ai developer",
    "nlp engineer", "ai software engineer", "machine learning engineer",
    "ml engineer", "applied ai", "ai backend", "conversational ai",
    "foundation model", "ai product engineer", "associate ai",
    "software engineer", "forward deployed engineer", "ai agent",
    "ai/ml engineer", "ai ml engineer", "junior ai", "trainee ai",
    "python developer", "python engineer", "backend engineer",
    "ai intern", "ai associate", "language model", "rag engineer",
]

# ── ROLE TITLE BLACKLIST ──
BLOCKED_ROLE_KEYWORDS = [
    "data scientist", "research analyst", "research scientist",
    "technical writer", "applied scientist", "data analyst",
    "data engineer", "business analyst", "cloud engineer",
    "devops", "content writer", "seo", "marketing",
    "sales", "account manager", "hr", "recruiter",
    "product manager", "project manager", "scrum",
    "data entry", "support engineer", "qa engineer",
    "test engineer", "tester", "network engineer",
    "customer support", "operations", "finance",
    "blockchain", "web3", "embedded", "firmware",
]

# ── TOOL-GAP keywords: Missing these = still apply ──
TOOL_GAP_SIGNALS = [
    "llamaindex", "llamaparse", "crewai", "autogen", "langflow",
    "tableau", "powerbi", "power bi", "grafana", "kibana",
    "xgboost", "lightgbm", "catboost", "svm", "random forest",
    "celery", "redis", "kafka", "terraform",
    "mlflow", "wandb", "weights & biases", "dvc",
    "node.js", "react", "angular", "vue",
    "snowflake", "databricks",
    "rlhf", "dpo", "reward modeling",
    "n8n", "airflow", "prefect",
    "kubernetes", "ci/cd", "jenkins",
    "typescript", "postgresql", "mysql", "microsoft copilot",
]

# ── CORE-GAP keywords: Missing these = SKIP ──
CORE_GAP_SIGNALS = [
    "java", "c++", "c#", "scala", "golang", "go lang", "rust",
    "r language", "r programming", "rstudio",
    "computer vision", "opencv", "image processing",
    "video generation", "diffusion model", "stable diffusion",
    "oracle", "mainframe", "cobol",
    "salesforce", "sap", "erp",
    "itsm", "servicenow",
    "sampling analytics",
    "3+ years", "4+ years", "5+ years",
]

# ── Experience killer keywords in role titles ──
EXPERIENCE_KILLERS = [
    "senior engineer", "lead engineer", "principal engineer",
    "director", "manager", "architect", "tech lead",
    "staff engineer", "distinguished",
]

# ── Company blacklist — large IT firms that always need 3+ yrs even for 'fresher' roles ──
COMPANY_BLACKLIST = {
    "scoutit",
}

# ── Aggregator signals ──
AGGREGATOR_SIGNALS = [
    "one platform. every opportunity",
    "powered by ai. apply now",
    "we connect candidates",
    "our client is seeking",
    "confidential company",
]


def is_role_allowed(title: str) -> tuple:
    """Check if a role title matches our AI Engineer whitelist."""
    title_lower = title.lower()
    for blocked in BLOCKED_ROLE_KEYWORDS:
        if blocked in title_lower:
            return False, f"Blocked role type: '{blocked}'"
    for allowed in ALLOWED_ROLE_KEYWORDS:
        if allowed in title_lower:
            return True, f"Matched allowed role: '{allowed}'"
    return False, "Role title not in AI Engineer whitelist"


def pre_filter_experience(jd_text: str, role_title: str) -> tuple:
    """Returns (True, matched_string) if JD should be DISQUALIFIED, else (False, '')."""
    text_to_check = (jd_text + " " + role_title).lower()

    # Normalize Unicode dashes to plain hyphens
    text_to_check = text_to_check.replace('\u2013', '-')   # en-dash
    text_to_check = text_to_check.replace('\u2014', '-')   # em-dash
    text_to_check = text_to_check.replace('\u2012', '-')   # figure-dash
    text_to_check = text_to_check.replace('\u2015', '-')   # horizontal bar

    # Title/role keyword killers
    for killer in EXPERIENCE_KILLERS:
        match = re.search(rf'\b{re.escape(killer)}\b', text_to_check)
        if match:
            return True, match.group(0)

    # Experience patterns
    NUM = r'([2-9]|\d{2,})'
    YRS = r'(?:years?|yrs?)'

    patterns = [
        rf'{NUM}\+?\s*-\s*\d+\s*{YRS}',
        rf'{NUM}\s+to\s+\d+\s*{YRS}',
        rf'{NUM}\+\s*{YRS}',
        rf'{NUM}\+?\s*{YRS}\s+of\s+.{{0,80}}?\b(?:experience|exp)\b',
        rf'(?:experience|exp)\s*[:\-|]+\s*{NUM}',
        rf'(?:minimum|at\s*least|atleast|min\.?)\s*{NUM}\+?\s*{YRS}',
        rf'{NUM}\+?\s*{YRS}\s+(?:of\s+)?(?:hands[\s-]on|professional|industry|relevant|related|proven|practical|prior|total|overall|software|production)',
        rf'{NUM}\+?\s*{YRS}\s+(?:of\s+)?(?:.{{0,40}}?\b)?(?:building|working|developing|designing|leading|managing|shipping|deploying)',
        rf'{NUM}\s*{YRS}(?:\s+of)?\s+(?:work\s+)?(?:experience|exp)\b',
        rf'(?:requires|required|minimum|min)\s+(?:of\s+)?{NUM}\s*{YRS}',
        # ── Structured job portal metadata fields (e.g. Zensar, Naukri, Shine)
        # Catches: "Minimum Experience (In Years): 5" / "minimum experience in years 5"
        rf'minimum\s+experience\s*(?:\(in\s+years?\))?\s*[:\-]?\s*{NUM}',
        rf'experience\s*(?:required|needed)?\s*(?:\(in\s+years?\))?\s*[:\-]?\s*{NUM}',
        rf'(?:exp|experience)\s*[:\-]\s*{NUM}\s*(?:to|-|\s)\s*\d+',
        # Catches bare number in structured fields: "5 to 8" / "5-8" near experience context
        rf'(?:min(?:imum)?|maximum|total)\s+exp(?:erience)?[^\n]{{0,30}}{NUM}',
    ]

    for pat in patterns:
        match = re.search(pat, text_to_check, re.IGNORECASE)
        if match:
            return True, match.group(0)

    return False, ""


def is_blacklisted(company: str) -> bool:
    """Check if company is in the blacklist."""
    return company.lower().strip() in COMPANY_BLACKLIST


def has_aggregator_signals(jd_text: str) -> bool:
    """Check if JD text contains aggregator/fake company signals."""
    jd_lower = jd_text.lower()
    return any(signal in jd_lower for signal in AGGREGATOR_SIGNALS)


def analyze_apply_decision(missing_skills: list) -> tuple:
    """Analyze missing skills and decide APPLY vs SKIP."""
    if not missing_skills:
        return "APPLY", "No missing skills — perfect match!"
    missing_text = " ".join([s.lower() for s in missing_skills])
    core_gaps_found = [s for s in CORE_GAP_SIGNALS if s in missing_text]
    tool_gaps_found = [s for s in TOOL_GAP_SIGNALS if s in missing_text]
    if core_gaps_found:
        return "SKIP", f"Core skill gaps: {', '.join(core_gaps_found)}"
    elif tool_gaps_found:
        return "APPLY", f"Only tool gaps (learnable): {', '.join(tool_gaps_found)}"
    else:
        return "APPLY", "Missing skills appear to be optional tools, not core blockers"


def quick_keyword_filter(text: str) -> bool:
    """
    Quick keyword check for unstructured text (HN comments, etc.)
    Returns True if the text likely contains an AI/ML/Python-related job.
    """
    text_lower = text.lower()
    ai_keywords = [
        "python", "machine learning", "ml engineer", "ai engineer",
        "llm", "langchain", "langgraph", "generative ai", "genai",
        "nlp", "natural language", "rag", "retrieval augmented",
        "prompt engineer", "agentic", "chatbot", "fastapi",
        "deep learning", "neural network", "transformer",
        "gpt", "openai", "groq", "anthropic", "claude",
        "vector database", "chromadb", "pinecone", "weaviate",
        "knowledge graph", "neo4j", "backend engineer",
    ]
    matches = sum(1 for kw in ai_keywords if kw in text_lower)
    return matches >= 2  # At least 2 AI keywords present
