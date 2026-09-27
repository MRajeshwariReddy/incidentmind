# 🧠 IncidentMind

**IncidentMind** is an AI-powered Incident Response Agent for DevOps and Software Engineering teams. It addresses a critical problem in software operations: during production incidents, engineers lose valuable time rediscovering how similar past incidents were diagnosed and resolved.

IncidentMind leverages **Hindsight Cloud** as its persistent semantic memory layer to retain confirmed root causes, resolutions, runbooks, and post-mortem lessons across incident lifecycles.

---

## 🌟 Key Features

1. **Incident Submission**: Record new incident details (Service, Severity, Description, Error Logs, Recent Deployments/Changes, Timestamp).
2. **AI Investigation & Memory Recall**: Uses Hindsight memory recall to fetch past incident experience and Groq LLM API to generate structured investigation reports distinguishing confirmed historical evidence from hypotheses.
3. **Resolve & Remember Loop**: Record confirmed root causes, resolutions, runbooks used, and lessons learned—retaining them into persistent Hindsight memory.
4. **Interactive Learning Demonstration**: A 1-click end-to-end learning loop demonstration proving the difference between investigating an incident with *zero memory* versus investigating a similar incident *after memory retention*.
5. **Incident Dashboard**: Real-time SQLite tracking of total, open, resolved incidents and Hindsight memory recall metrics.

---

## 🏗️ Architecture

- **User Interface**: Streamlit (`app.py`)
- **Persistent Agent Memory**: Hindsight (`hindsight-client` -> `https://api.hindsight.vectorize.io`)
- **Reasoning LLM Engine**: Groq API (`openai/gpt-oss-120b` or configurable model)
- **Structured Database**: SQLite (`database.py`)

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.10+
- (Optional) Groq API Key ([console.groq.com](https://console.groq.com))
- (Optional) Hindsight Cloud API Key ([docs.hindsight.vectorize.io](https://docs.hindsight.vectorize.io/))

### 2. Installation
Clone the repository and install requirements:
```bash
git clone https://github.com/your-org/incidentmind.git
cd incidentmind
pip install -r requirements.txt
```

### 3. Environment Setup
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env` with your API keys:
```env
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-120b
HINDSIGHT_API_KEY=your_hindsight_api_key_here
HINDSIGHT_API_URL=https://api.hindsight.vectorize.io
HINDSIGHT_BANK_ID=incidentmind-default
DATABASE_PATH=incidentmind.db
```
*(Note: If keys are omitted, IncidentMind will run using local fallback engines for offline development.)*

### 4. Run the Application
Launch Streamlit locally:
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 🧪 Running Automated Tests

Run the complete pytest test suite:
```bash
PYTHONPATH=. python3 -m pytest -v
```

---

## ☁️ Deployment to Streamlit Community Cloud

1. Push this repository to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io).
3. Connect your repository and set `app.py` as the main entry point.
4. Add environment variables in **Secrets**:
   ```toml
   GROQ_API_KEY = "gsk_..."
   GROQ_MODEL = "openai/gpt-oss-120b"
   HINDSIGHT_API_KEY = "..."
   HINDSIGHT_API_URL = "https://api.hindsight.vectorize.io"
   HINDSIGHT_BANK_ID = "incidentmind-prod"
   DATABASE_PATH = "incidentmind.db"
   ```
5. Click **Deploy**.
