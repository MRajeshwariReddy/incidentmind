import logging
from typing import List, Dict, Any, Optional
import config

logger = logging.getLogger("incidentmind.memory")

_local_memory_store: List[Dict[str, Any]] = []

def clear_local_memory_store() -> None:
    """Helper to reset local memory store for testing or isolated runs."""
    global _local_memory_store
    _local_memory_store = []

def get_hindsight_client():
    if not config.HINDSIGHT_API_KEY:
        logger.warning("HINDSIGHT_API_KEY is not configured. Hindsight memory client will operate in local fallback mode.")
        return None
    try:
        from hindsight_client import Hindsight
        base_url = config.HINDSIGHT_API_URL or "https://api.hindsight.vectorize.io"
        client = Hindsight(
            base_url=base_url,
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
    If HINDSIGHT_API_KEY is configured, uses Hindsight Cloud.
    Raises RuntimeError if Hindsight Cloud is configured but fails.
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

    client = get_hindsight_client()

    if client:
        # Hindsight Cloud is configured - use real Hindsight Cloud
        try:
            try:
                client.create_bank(bank_id=bank, name=f"IncidentMind Bank {bank}")
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
            err_msg = f"Hindsight Cloud API retain failed for bank '{bank}': {e}"
            logger.error(err_msg)
            # Do NOT silently fallback if credentials are explicitly configured
            raise RuntimeError(err_msg) from e
    else:
        # Local fallback mode when no credentials are provided
        local_record = {
            "bank_id": bank,
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
        return {"status": "success", "source": "local_fallback", "message": "Retained in local memory"}

def recall_similar_incidents(
    query: str,
    service: Optional[str] = None,
    bank_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Recalls historical incident memories relevant to the query from Hindsight memory.
    If HINDSIGHT_API_KEY is configured, queries Hindsight Cloud.
    Raises RuntimeError if Hindsight Cloud is configured but fails.
    """
    bank = bank_id or config.HINDSIGHT_BANK_ID or "incidentmind-default"
    client = get_hindsight_client()

    if client:
        # Hindsight Cloud is configured
        try:
            recall_resp = client.recall(
                bank_id=bank,
                query=query,
                tags=[service] if service else None,
                budget="mid"
            )

            recalled_items: List[Dict[str, Any]] = []
            results = getattr(recall_resp, "results", []) or getattr(recall_resp, "memories", [])
            for item in results:
                # Official SDK memory text field
                text = getattr(item, "text", None) or getattr(item, "content", None) or str(item)

                mem_dict = {
                    "content": text,
                    "source": "hindsight_cloud",
                    "type": getattr(item, "type", "historical_memory")
                }

                # Only include score if provided by SDK without fabricating
                raw_score = getattr(item, "score", None) or getattr(item, "relevance", None)
                if raw_score is not None:
                    mem_dict["relevance_score"] = float(raw_score)

                meta = getattr(item, "metadata", None)
                if meta:
                    mem_dict["metadata"] = meta

                recalled_items.append(mem_dict)

            return recalled_items
        except Exception as e:
            err_msg = f"Hindsight Cloud API recall failed for bank '{bank}': {e}"
            logger.error(err_msg)
            # Do NOT silently fallback if credentials are explicitly configured
            raise RuntimeError(err_msg) from e
    else:
        # Local fallback mode when no credentials are provided
        recalled_items = []
        query_terms = [t.lower() for t in query.replace("\n", " ").split() if len(t) > 2]

        for item in _local_memory_store:
            # Respect bank_id isolation in local memory
            if item.get("bank_id") and item.get("bank_id") != bank:
                continue

            item_text = item["formatted_text"].lower()
            matches = sum(1 for term in query_terms if term in item_text)
            if matches > 0 or (service and service.lower() == item["service"].lower()):
                recalled_items.append({
                    "content": item["formatted_text"],
                    "source": "local_fallback",
                    "type": "incident_resolution",
                    "metadata": {
                        "incident_id": item["incident_id"],
                        "service": item["service"],
                        "severity": item["severity"]
                    }
                })
        return recalled_items

def get_memory_stats(bank_id: Optional[str] = None) -> Dict[str, Any]:
    return {
        "total_retained_memories": len(_local_memory_store),
        "active_bank": bank_id or config.HINDSIGHT_BANK_ID or "incidentmind-default",
        "hindsight_connected": bool(config.HINDSIGHT_API_KEY)
    }
