# MultiSource AI Job Scanner

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2CA5E0?style=for-the-badge&logo=docker&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-LLM%20Eval-orange?style=for-the-badge)

An intelligent, multi-platform job aggregation and evaluation pipeline designed to autonomously fetch, filter, and score software engineering and AI roles across multiple job boards using LLM-powered candidate-fit evaluation.

## 🚀 Features
- Integrates with multiple job boards simultaneously (Adzuna, HackerNews, RemoteOK)
- Uses Groq's GPT-OSS 120B model for semantic parsing and candidate-fit evaluation
- Strict role-whitelist and experience regex pre-filter to drop overqualified/stretch roles
- Multi-model fallback chain (primary → backup) for 100% evaluation uptime
- Automated HTML email reports via SMTP with ranked job results
- Fully containerized with Docker for one-command deployment

## 🛠️ Tech Stack
- **Backend:** Python 3.10, Requests, BeautifulSoup4
- **LLM Evaluation:** Groq API (GPT-OSS 120B)
- **Deployment:** Docker, python-dotenv
- **Notifications:** SMTP Email (HTML formatted)

## 🐳 Docker Quick Start
```bash
docker build -t job-scanner .
docker run --env-file config/.env job-scanner
```

## 📁 Project Structure
```
MultiSource_JobScanner/
├── core/
│   ├── filters.py        # Role whitelist + experience regex gate
│   ├── evaluator.py      # Groq LLM evaluation logic
│   └── notifier.py       # SMTP email notification system
├── sources/
│   ├── adzuna_scraper.py
│   ├── hackernews_scraper.py
│   └── remoteok_scraper.py
├── config/
│   └── .env.example      # Environment variable template
├── run_scanner.py         # Main pipeline orchestrator
└── Dockerfile
```

## 🤝 Connect
- **GitHub:** [Shiva-keerth](https://github.com/Shiva-keerth)
- **Focus:** Generative AI, Agentic Systems, LLMOps, RAG Pipelines
