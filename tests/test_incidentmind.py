import os
import pytest
import database
import memory
import llm

@pytest.fixture
def temp_db(tmp_path):
    db_file = str(tmp_path / "test_incidentmind.db")
    database.init_db(db_file)
    return db_file

def test_database_crud(temp_db):
    inc_data = {
        "incident_id": "TEST-001",
        "service": "test-service",
        "severity": "HIGH",
        "description": "Test description",
        "error_logs": "Test log line",
        "recent_changes": "v1.0.0 deploy",
        "timestamp": "2025-01-01T00:00:00Z",
        "status": "OPEN"
    }
    created_id = database.create_incident(inc_data, db_path=temp_db)
    assert created_id == "TEST-001"

    inc = database.get_incident("TEST-001", db_path=temp_db)
    assert inc is not None
    assert inc["service"] == "test-service"
    assert inc["status"] == "OPEN"

    database.update_incident_investigation("TEST-001", "Report text", [{"content": "mem1"}], db_path=temp_db)
    inc_updated = database.get_incident("TEST-001", db_path=temp_db)
    assert inc_updated["investigation_report"] == "Report text"
    assert len(inc_updated["recalled_memories"]) == 1

    database.resolve_incident("TEST-001", "Root cause", "Fix step", "RB-01", "Lesson", db_path=temp_db)
    inc_resolved = database.get_incident("TEST-001", db_path=temp_db)
    assert inc_resolved["status"] == "RESOLVED"
    assert inc_resolved["confirmed_root_cause"] == "Root cause"

    stats = database.get_dashboard_stats(db_path=temp_db)
    assert stats["total_incidents"] == 1
    assert stats["resolved_incidents"] == 1
    assert stats["open_incidents"] == 0

def test_memory_retain_and_recall():
    retain_res = memory.retain_incident_resolution(
        incident_id="INC-MEMORY-1",
        service="auth-api",
        severity="HIGH",
        description="JWT token validation failure",
        error_logs="Signature invalid",
        recent_changes="Rotated public key",
        confirmed_root_cause="Public key mismatch in cache",
        resolution="Flushed redis key cache",
        runbook_used="RB-AUTH-CACHE",
        lesson_learned="Invalidate token cache on key rotation"
    )
    assert retain_res["status"] in ["success", "fallback"]

    recalled = memory.recall_similar_incidents(
        query="JWT token validation failure Signature invalid",
        service="auth-api"
    )
    assert len(recalled) > 0
    assert "INC-MEMORY-1" in recalled[0]["content"] or "auth-api" in recalled[0]["content"]

def test_llm_report_generation():
    inc = {
        "incident_id": "INC-LLM-1",
        "service": "checkout-service",
        "severity": "CRITICAL",
        "description": "Database deadlock on checkout table",
        "error_logs": "ERROR: deadlock detected",
        "recent_changes": "None"
    }
    recalled_mems = [{
        "content": "INCIDENT MEMORY RECORD:\nRoot cause: Deadlock due to out-of-order locks\nResolution: Sorted locking order",
        "relevance_score": 0.95
    }]

    report = llm.generate_investigation_report(inc, recalled_mems)
    assert report is not None
    assert len(report) > 50
    assert "Executive Summary" in report or "Incident" in report
