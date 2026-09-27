import logging
from typing import List, Dict, Any, Optional
import config

logger = logging.getLogger("incidentmind.memory")

_local_memory_store: List[Dict[str, Any]] = []

def get_hindsight_client():
    if not config.HINDSIGHT_API_KEY:
        logger.warning("HINDSIGHT_API_KEY is not configured. Hindsight memory client will operate in fallback mode.")
        return None
    try:
        from hindsight_client import Hindsight
        client = Hindsight(
            base_url=config.HINDSIGHT_API_URL or "https://api.hindsight.tech",
            api_key=config.HINDSIGHT_API_KEY
        )
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Hindsight client: {e}")
        return None

def retain_incident_resolution(
    incident_id: str,
    service: str,
    severity: str,
    description: str,
    error_logs: str,
    recent_changes: str,
    confirmed_root_cause: str,
    resolution: str,
    runbook_used: str,
    lesson_learned: str,
    bank_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Retains a resolved incident and its lesson/resolution in Hindsight memory.
    """
    bank = bank_id or config.HINDSIGHT_BANK_ID or "incidentmind-default"

    memory_payload = (
        f"INCIDENT MEMORY RECORD:\n"
        f"Incident ID: {incident_id}\n"
        f"Service: {service}\n"
        f"Severity: {severity}\n"
        f"Symptom Description: {description}\n"
        f"Error Logs: {error_logs}\n"
        f"Recent Deployment/Change: {recent_changes}\n"
        f"Confirmed Root Cause: {confirmed_root_cause}\n"
        f"Resolution Executed: {resolution}\n"
        f"Runbook Used: {runbook_used}\n"
        f"Lessons Learned: {lesson_learned}\n"
    )

    metadata = {
        "incident_id": incident_id,
        "service": service,
        "severity": severity,
        "type": "incident_resolution"
    }

    # Always keep in local fallback store for seamless demonstration/testing
    local_record = {
        "incident_id": incident_id,
        "service": service,
        "severity": severity,
        "description": description,
        "error_logs": error_logs,
        "recent_changes": recent_changes,
        "confirmed_root_cause": confirmed_root_cause,
        "resolution": resolution,
        "runbook_used": runbook_used,
        "lesson_learned": lesson_learned,
        "formatted_text": memory_payload
    }
    _local_memory_store.append(local_record)

    client = get_hindsight_client()
    if client:
        try:
            # Ensure bank exists if using cloud
            try:
                client.create_bank(bank_id=bank, name="IncidentMind Memory Bank")
            except Exception:
                pass # Bank may already exist

            response = client.retain(
                bank_id=bank,
                content=memory_payload,
                metadata=metadata,
                tags=[service, severity, "incident_resolution"]
            )
            return {"status": "success", "source": "hindsight_cloud", "response": str(response)}
        except Exception as e:
            logger.error(f"Hindsight API retain error: {e}")
            return {"status": "fallback", "source": "local_fallback", "error": str(e)}
    else:
        return {"status": "success", "source": "local_fallback", "message": "Retained in memory"}

def recall_similar_incidents(
    query: str,
    service: Optional[str] = None,
    bank_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Recalls historical incident memories relevant to the current problem description or error logs.
    """
    bank = bank_id or config.HINDSIGHT_BANK_ID or "incidentmind-default"
    client = get_hindsight_client()

    recalled_items: List[Dict[str, Any]] = []

    if client:
        try:
            recall_resp = client.recall(
                bank_id=bank,
                query=query,
                tags=[service] if service else None,
                budget="mid"
            )

            # Extract results from RecallResponse
            results = getattr(recall_resp, "results", []) or getattr(recall_resp, "memories", [])
            for item in results:
                text = getattr(item, "text", "") or getattr(item, "content", "") or str(item)
                score = getattr(item, "score", 0.0) or getattr(item, "relevance", 1.0)
                meta = getattr(item, "metadata", {}) or {}
                recalled_items.append({
                    "content": text,
                    "relevance_score": float(score) if score else 0.85,
                    "metadata": meta,
                    "source": "hindsight_cloud"
                })
        except Exception as e:
            logger.error(f"Hindsight API recall error: {e}")

    # Fallback / local memory retrieval matching
    if not recalled_items and _local_memory_store:
        query_terms = [t.lower() for t in query.replace("\n", " ").split() if len(t) > 2]
        for item in _local_memory_store:
            item_text = item["formatted_text"].lower()
            matches = sum(1 for term in query_terms if term in item_text)
            if matches > 0 or (service and service.lower() == item["service"].lower()):
                recalled_items.append({
                    "content": item["formatted_text"],
                    "relevance_score": min(0.95, 0.5 + (matches * 0.1)),
                    "metadata": {
                        "incident_id": item["incident_id"],
                        "service": item["service"],
                        "severity": item["severity"]
                    },
                    "source": "local_memory"
                })

    return recalled_items

def get_memory_stats(bank_id: Optional[str] = None) -> Dict[str, Any]:
    return {
        "total_retained_memories": len(_local_memory_store),
        "active_bank": bank_id or config.HINDSIGHT_BANK_ID or "incidentmind-default",
        "hindsight_connected": bool(config.HINDSIGHT_API_KEY)
    }
