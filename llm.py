import logging
from typing import List, Dict, Any, Optional
import config

logger = logging.getLogger("incidentmind.llm")

SYSTEM_PROMPT = """You are IncidentMind, an expert AI Incident Response Specialist and Senior Site Reliability Engineer.
Your task is to analyze production incidents using both current diagnostic signals AND historical experience recalled from past incidents.

Core Rules for Analysis:
1. Distinguish clearly between HISTORICAL EVIDENCE (past confirmed incidents recalled from memory) and CURRENT HYPOTHESES (educated deductions based on current symptoms).
2. Never invent or hallucinate past incidents. Use ONLY the historical memories provided in the prompt. If no historical memory is relevant, explicitly state that this appears to be a novel incident pattern without prior recorded occurrences.
3. Keep recommendations actionable, practical, and clear for DevOps/SRE teams.

Structure your report in Markdown using the following sections:

### 1. Executive Summary & Problem Diagnosis
Brief synthesis of the incident symptoms, service impacted, and immediate operational severity.

### 2. Historical Memory & Evidence Analysis
- List relevant recalled past incidents.
- Explain how past resolutions or root causes apply (or differ) from the current symptoms.
- If no past memories exist, state that no prior match was found in Hindsight memory.

### 3. Root Cause Hypotheses & Evidence Evaluation
- **Confirmed Historical Evidence**: What facts from past incidents directly correlate with current error logs/metrics.
- **Current Hypotheses**: Potential root causes specific to current changes or error messages.

### 4. Recommended Investigation Steps
Bullet list of immediate diagnostic commands, log queries, or metric checks to confirm the root cause.

### 5. Recommended Remediation & Runbooks
- Step-by-step remediation plan to resolve the incident.
- Reference relevant runbooks from memory if available.
"""

def get_groq_client():
    if not config.GROQ_API_KEY:
        logger.warning("GROQ_API_KEY is not configured.")
        return None
    try:
        from groq import Groq
        return Groq(api_key=config.GROQ_API_KEY)
    except Exception as e:
        logger.error(f"Failed to initialize Groq client: {e}")
        return None

def generate_investigation_report(
    incident: Dict[str, Any],
    recalled_memories: List[Dict[str, Any]]
) -> str:
    """
    Generates an investigation report using Groq LLM API or structured fallbacks if API is unconfigured.
    """
    # Format current incident details
    incident_details = (
        f"Incident ID: {incident.get('incident_id', 'N/A')}\n"
        f"Service: {incident.get('service', 'N/A')}\n"
        f"Severity: {incident.get('severity', 'N/A')}\n"
        f"Description: {incident.get('description', 'N/A')}\n"
        f"Error Logs:\n{incident.get('error_logs', 'None provided')}\n"
        f"Recent Deployment/Changes:\n{incident.get('recent_changes', 'None reported')}\n"
        f"Timestamp: {incident.get('timestamp', 'N/A')}\n"
    )

    # Format recalled memories
    if recalled_memories:
        memories_text = "RECALLED HISTORICAL INCIDENTS FROM HINDSIGHT MEMORY:\n\n"
        for idx, mem in enumerate(recalled_memories, 1):
            score = mem.get("relevance_score", 0.0)
            content = mem.get("content", "")
            memories_text += f"--- Memory #{idx} (Relevance Score: {score:.2f}) ---\n{content}\n\n"
    else:
        memories_text = "RECALLED HISTORICAL INCIDENTS FROM HINDSIGHT MEMORY:\nNone found. This incident has no matching historical records in memory.\n"

    user_prompt = (
        f"CURRENT INCIDENT SYMPTOMS & SIGNALS:\n{incident_details}\n\n"
        f"{memories_text}\n"
        f"Please analyze this incident and generate the complete structured investigation report."
    )

    client = get_groq_client()
    if client:
        try:
            response = client.chat.completions.create(
                model=config.GROQ_MODEL or "llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=2048
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq API call failed: {e}")
            return _generate_fallback_report(incident, recalled_memories, error_msg=str(e))
    else:
        return _generate_fallback_report(incident, recalled_memories)

def _generate_fallback_report(
    incident: Dict[str, Any],
    recalled_memories: List[Dict[str, Any]],
    error_msg: Optional[str] = None
) -> str:
    """Deterministic fallback report generator for offline or keyless execution."""
    service = incident.get("service", "Service")
    inc_id = incident.get("incident_id", "INC-000")
    severity = incident.get("severity", "MEDIUM")
    desc = incident.get("description", "No description")
    logs = incident.get("error_logs", "")
    changes = incident.get("recent_changes", "")

    note = f"\n*(Note: Generated via fallback engine. GROQ_API_KEY status: {error_msg or 'Not provided'})*\n" if error_msg else ""

    if recalled_memories:
        mem_summary = f"Identified {len(recalled_memories)} matching past incident memory record(s) from Hindsight."
        historical_section = ""
        for idx, mem in enumerate(recalled_memories, 1):
            historical_section += f"- **Memory #{idx}**: {mem.get('content', '').strip()}\n"

        evidence_eval = (
            f"**Confirmed Historical Evidence**: Matching historical patterns suggest high correlation with previously resolved incidents for `{service}`.\n"
            f"**Current Hypotheses**: Investigate recent deployment `{changes}` against known failure modes."
        )
        remediation_steps = (
            f"1. Apply historical resolution pattern from recalled memory.\n"
            f"2. Validate service status and monitor key operational metrics for `{service}`.\n"
            f"3. Run automated health checks to ensure recovery."
        )
    else:
        mem_summary = "No past incidents found in Hindsight memory for this error pattern."
        historical_section = "No prior recorded historical memories match this incident."
        evidence_eval = (
            f"**Confirmed Historical Evidence**: None available in memory.\n"
            f"**Current Hypotheses**: Primary hypothesis points to recent change/deployment `{changes}` or unhandled error in `{service}`."
        )
        remediation_steps = (
            f"1. Inspect error logs for detailed trace.\n"
            f"2. Consider rolling back recent deployment `{changes}` if issue started immediately after deploy.\n"
            f"3. Record actual resolution in Hindsight memory once confirmed."
        )

    return f"""### 1. Executive Summary & Problem Diagnosis
Incident **{inc_id}** on service **{service}** ({severity} severity).
Symptom Summary: {desc}
{note}

### 2. Historical Memory & Evidence Analysis
{mem_summary}

{historical_section}

### 3. Root Cause Hypotheses & Evidence Evaluation
{evidence_eval}

### 4. Recommended Investigation Steps
- Check application logs for `{service}` around the time of alert.
- Review system resource utilization (CPU, memory, disk I/O, database connections).
- Inspect trace details for logs: `{logs}`.

### 5. Recommended Remediation & Runbooks
{remediation_steps}
"""
