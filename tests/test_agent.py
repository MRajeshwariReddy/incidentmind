import pytest
from unittest.mock import patch, MagicMock
import database
import memory
import agent

@pytest.fixture
def temp_db(tmp_path):
    db_file = str(tmp_path / "test_agent_suite.db")
    database.init_db(db_file)
    return db_file

def test_get_incident_context(temp_db):
    inc_data = {
        "incident_id": "TEST-AGENT-1",
        "service": "auth-service",
        "severity": "CRITICAL",
        "description": "JWT key rotation error",
        "error_logs": "KeyNotFoundError: invalid key ID",
        "recent_changes": "v2.1 deploy"
    }
    database.create_incident(inc_data, db_path=temp_db)

    ctx = agent.get_incident_context("TEST-AGENT-1", db_path=temp_db)
    assert ctx is not None
    assert ctx["service"] == "auth-service"
    assert ctx["severity"] == "CRITICAL"

def test_recall_historical_incidents_fallback():
    memory.clear_local_memory_store()
    bank = "test-agent-bank"

    # Retain memory
    memory.retain_incident_resolution(
        incident_id="INC-HIST-1",
        service="auth-service",
        severity="HIGH",
        description="JWT signature invalid",
        error_logs="invalid key ID",
        recent_changes="v2.0 deploy",
        confirmed_root_cause="Stale cache",
        resolution="Flushed key cache",
        runbook_used="RB-AUTH",
        lesson_learned="Invalidate cache on key rotation",
        bank_id=bank
    )

    recalled = agent.recall_historical_incidents("JWT signature invalid key ID", bank_id=bank, service="auth-service")
    assert len(recalled) == 1
    assert "INC-HIST-1" in recalled[0]["content"]

def test_build_investigation_context():
    inc_ctx = {"incident_id": "INC-1", "service": "payment"}
    mems = [{"content": "Historical memory content"}]

    comb = agent.build_investigation_context(inc_ctx, mems)
    assert comb["incident"]["service"] == "payment"
    assert comb["historical_memories"] == mems
    assert comb["memory_count"] == 1
    assert comb["has_historical_context"] is True

def test_agent_investigate_success(temp_db):
    inc_data = {
        "incident_id": "TEST-AGENT-2",
        "service": "payment-service",
        "severity": "HIGH",
        "description": "Payment processing timeout",
        "error_logs": "Timeout waiting for lock",
        "recent_changes": "Config update"
    }
    database.create_incident(inc_data, db_path=temp_db)

    ag = agent.IncidentInvestigationAgent()
    res = ag.investigate(incident_id="TEST-AGENT-2", bank_id="test-agent-bank-2", db_path=temp_db)

    assert res["status"] == "success"
    assert res["incident_id"] == "TEST-AGENT-2"
    assert "investigation_report" in res
    assert isinstance(res["recalled_memories"], list)

def test_agent_investigate_fallback_error(temp_db):
    ag = agent.IncidentInvestigationAgent()
    # Non-existent incident triggers graceful agent fallback
    res = ag.investigate(incident_id="NON-EXISTENT-INC", db_path=temp_db)

    assert res["status"] == "fallback"
    assert "error" in res
    assert "investigation_report" in res
