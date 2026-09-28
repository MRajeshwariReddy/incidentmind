import logging
from typing import Dict, Any, List, Optional
import database
import memory
import llm

logger = logging.getLogger("incidentmind.agent")

def get_incident_context(incident_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Tool 1: Retrieves current incident details from SQLite database.
    """
    return database.get_incident(incident_id, db_path=db_path)

def recall_historical_incidents(
    query: str,
    bank_id: Optional[str] = None,
    service: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Tool 2: Recalls historical incident memories using Hindsight memory layer.
    """
    try:
        return memory.recall_similar_incidents(query=query, service=service, bank_id=bank_id)
    except Exception as e:
        logger.error(f"Error in recall_historical_incidents tool: {e}")
        return []

def build_investigation_context(
    incident_context: Dict[str, Any],
    historical_memories: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Tool 3: Combines current incident context with recalled historical memories
    into a structured context payload for LLM analysis.
    """
    return {
        "incident": incident_context,
        "historical_memories": historical_memories,
        "memory_count": len(historical_memories),
        "has_historical_context": len(historical_memories) > 0
    }

class IncidentInvestigationAgent:
    """
    Lightweight, tool-based Incident Response Agent orchestrator.
    Executes investigation pipeline without modifying database or resolving incidents.
    """
    def __init__(self):
        pass

    def investigate(
        self,
        incident_id: str,
        bank_id: Optional[str] = None,
        db_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Orchestrates tool calls to investigate an incident:
        1. Tool: get_incident_context()
        2. Tool: recall_historical_incidents()
        3. Tool: build_investigation_context()
        4. LLM reasoning: llm.generate_investigation_report()
        """
        try:
            # Step 1: Tool call - get_incident_context
            incident_ctx = get_incident_context(incident_id, db_path=db_path)
            if not incident_ctx:
                raise ValueError(f"Incident ID '{incident_id}' not found in database.")

            # Step 2: Build recall query from incident signals
            service = incident_ctx.get("service", "")
            desc = incident_ctx.get("description", "")
            logs = incident_ctx.get("error_logs", "")
            changes = incident_ctx.get("recent_changes", "")
            
            query = f"Service: {service}\nDescription: {desc}\nLogs: {logs}\nChanges: {changes}".strip()

            # Step 3: Tool call - recall_historical_incidents
            recalled_memories = recall_historical_incidents(
                query=query,
                bank_id=bank_id,
                service=service
            )

            # Step 4: Tool call - build_investigation_context
            investigation_ctx = build_investigation_context(incident_ctx, recalled_memories)

            # Step 5: Generate LLM investigation report
            report = llm.generate_investigation_report(
                incident=investigation_ctx["incident"],
                recalled_memories=investigation_ctx["historical_memories"]
            )

            return {
                "incident_id": incident_id,
                "investigation_report": report,
                "recalled_memories": recalled_memories,
                "memory_count": len(recalled_memories),
                "status": "success"
            }

        except Exception as e:
            logger.error(f"IncidentInvestigationAgent failed for '{incident_id}': {e}")
            # Graceful agent fallback - preserve working investigation path if agent fails
            fallback_incident = get_incident_context(incident_id, db_path=db_path) or {
                "incident_id": incident_id,
                "service": "unknown",
                "severity": "HIGH",
                "description": f"Investigation failed with error: {e}"
            }
            fallback_report = llm.generate_investigation_report(fallback_incident, [])
            return {
                "incident_id": incident_id,
                "investigation_report": fallback_report,
                "recalled_memories": [],
                "memory_count": 0,
                "status": "fallback",
                "error": str(e)
            }
