# 🧠 IncidentMind

**IncidentMind** is an AI-powered incident investigation and response assistant for DevOps and software engineering teams.

During production incidents, engineers often spend valuable time reconstructing what happened, searching through previous incidents, and determining whether a familiar failure pattern has occurred before. IncidentMind helps streamline that workflow by combining structured incident data, persistent incident memory, and LLM-assisted investigation.

The system can investigate a new incident, recall relevant historical experience, generate an investigation report, and retain confirmed resolutions and lessons for future incidents.

---

## 🌟 Key Features

### 🚨 Incident Submission

Record production incident details including:

* Affected service
* Severity
* Symptoms and description
* Error logs
* Recent deployments or configuration changes
* Incident timestamp

### 🔍 AI Investigation & Memory Recall

When an incident is submitted, IncidentMind:

1. Retrieves the incident from the database.
2. Builds an investigation context from the incident details.
3. Searches persistent memory for similar historical incidents.
4. Passes the current incident and relevant historical experience to the LLM.
5. Generates a structured investigation report.

Historical information is treated as supporting evidence rather than automatically assuming that a previous incident is the cause of the current one.

### 🧠 Resolve & Remember

After an incident is resolved, engineers can record:

* Confirmed root cause
* Resolution steps
* Runbook used or created
* Lessons learned

The confirmed experience is retained in persistent semantic memory so that it can contribute to future investigations.

### 🧪 Learning Demonstration

The application includes an interactive demonstration of the learning loop:

**First similar incident → investigation with no prior memory → resolution retained → second similar incident → relevant historical experience recalled.**

This makes the memory lifecycle visible from investigation through future reuse.

### 📊 Incident Dashboard

The dashboard provides visibility into:

* Total incidents
* Open incidents
* Resolved incidents
* Investigation reports
* Historical memory recall

---

## 🏗️ Architecture

```
┌─────────────────────────────┐
│       Streamlit UI          │
│          app.py             │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│ Incident Investigation Agent│
│          agent.py           │
└───────┬───────────┬─────────┘
        │           │
        ▼           ▼
┌──────────────┐ ┌─────────────────────┐
│   SQLite     │ │ Persistent Semantic │
│  database.py │ │       Memory        │
└──────────────┘ │      Hindsight      │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │ Investigation       │
                 │ Context + LLM       │
                 │      Groq           │
                 └─────────────────────┘
```

### Main Components

| Component           | Technology | Purpose                                                              |
| ------------------- | ---------- | -------------------------------------------------------------------- |
| User Interface      | Streamlit  | Incident submission, investigation, resolution, and dashboard        |
| Agent Orchestration | Python     | Coordinates incident retrieval, memory recall, and report generation |
| Persistent Memory   | Hindsight  | Stores and recalls historical incident experience                    |
| LLM                 | Groq       | Generates structured investigation reports                           |
| Database            | SQLite     | Stores incidents, reports, and application state                     |

---

## 🧠 Persistent Incident Memory

IncidentMind uses **Hindsight** as its persistent semantic memory layer.

The memory workflow is:

```text
Incident occurs
      ↓
Incident submitted
      ↓
Historical experience recalled
      ↓
Investigation report generated
      ↓
Incident resolved
      ↓
Root cause + resolution + lessons retained
      ↓
Future incidents can recall that experience
```

The important distinction is that the system does not simply store incident records and perform a basic keyword lookup. Confirmed incident experience can be retained as reusable knowledge and recalled when investigating a later incident.

This allows the system to build an evolving operational knowledge base from previous investigations.

---

## 🚀 Quickstart

### Prerequisites

* Python 3.10+
* A Groq API key for LLM-powered investigation
* A Hindsight API key for persistent cloud memory

The application also contains fallback behavior for local development and testing when external services are unavailable.

### 1. Clone the Repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd incidentmind
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

Using a virtual environment is recommended:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Configure the required values:

```env
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-120b

HINDSIGHT_API_KEY=your_hindsight_api_key
HINDSIGHT_API_URL=https://api.hindsight.vectorize.io
HINDSIGHT_BANK_ID=incidentmind-default

DATABASE_PATH=incidentmind.db
```

**Never commit `.env` or API keys to the repository.**

### 4. Run IncidentMind

```bash
streamlit run app.py
```

Then open:

```text
http://localhost:8501
```

---

## 🧪 Running Tests

Run the complete automated test suite:

```bash
PYTHONPATH=. python3 -m pytest -v
```

The test suite covers:

* Database CRUD operations
* LLM and memory configuration
* Local fallback behavior
* Persistent-memory integration
* External memory error handling
* Investigation report generation

---

## 📁 Project Structure

```text
incidentmind/
├── app.py                 # Streamlit application
├── agent.py               # Incident investigation orchestration
├── config.py              # Environment and configuration
├── database.py            # SQLite persistence
├── llm.py                 # LLM integration and report generation
├── memory.py              # Persistent and fallback memory operations
├── requirements.txt       # Python dependencies
├── .env.example           # Environment configuration template
└── tests/
    ├── test_agent.py
    └── test_incidentmind.py
```

---

## 🔄 Example Investigation Flow

A typical incident can move through the following lifecycle:

```text
1. Submit Incident
        ↓
2. Retrieve Incident Context
        ↓
3. Recall Similar Historical Experience
        ↓
4. Generate Investigation Report
        ↓
5. Confirm Root Cause
        ↓
6. Record Resolution
        ↓
7. Retain Lessons Learned
        ↓
8. Reuse Knowledge During Future Incidents
```

For example, an incident involving database connection-pool exhaustion can be investigated alongside historical incidents involving similar connection-management failures. Once the root cause and resolution are confirmed, that experience becomes available as context for future investigations.

---

## ☁️ Deployment

IncidentMind can be deployed using Streamlit Community Cloud or another environment capable of running a Streamlit application.

For a Streamlit deployment:

1. Push the repository to GitHub.
2. Create a new Streamlit deployment.
3. Set `app.py` as the application entry point.
4. Configure the required environment variables as deployment secrets.
5. Deploy the application.

Keep all API credentials in the deployment's secret/environment configuration rather than committing them to source control.

---

## 🔐 Security Notes

* Do not commit `.env` files.
* Do not commit API keys or other credentials.
* Use environment variables for external service configuration.
* Avoid storing sensitive production data in demonstration incidents.
* Use separate memory banks/configurations for development and production environments.

---

## 🛠️ Technology Stack

* **Python**
* **Streamlit**
* **SQLite**
* **Groq API**
* **Hindsight**
* **Pytest**

---

## 📌 Project Status

IncidentMind is an actively developed prototype focused on persistent-memory-assisted incident investigation and response workflows.
