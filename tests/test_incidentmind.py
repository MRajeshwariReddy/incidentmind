import os
import pytest
from unittest.mock import patch, MagicMock
import database
import memory
import llm
import config

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

    database.update_incident_investigation("TEST-001", "Report text", [{"content": "mem1"}], db_path=temp_db)
    inc_updated = database.get_incident("TEST-001", db_path=temp_db)
    assert inc_updated["investigation_report"] == "Report text"
    assert len(inc_updated["recalled_memories"]) == 1

    database.resolve_incident("TEST-001", "Root cause", "Fix step", "RB-01", "Lesson", db_path=temp_db)
    inc_resolved = database.get_incident("TEST-001", db_path=temp_db)
    assert inc_resolved["status"] == "RESOLVED"

def test_hindsight_configuration():
    assert config.HINDSIGHT_API_URL == "https://api.hindsight.vectorize.io"
    assert config.GROQ_MODEL is not None

def test_local_fallback_retain_and_recall():
    memory.clear_local_memory_store()
    bank_id = "test-bank-local"

    # 1. Zero-memory initial stage
    recalled_empty = memory.recall_similar_incidents(
        query="Database connection timeout",
        service="payment-service",
        bank_id=bank_id
    )
    assert len(recalled_empty) == 0

    # 2. Retain experience
    retain_res = memory.retain_incident_resolution(
        incident_id="INC-MEMORY-1",
        service="payment-service",
        severity="HIGH",
        description="Database connection pool exhausted",
        error_logs="pq: connection timeout",
        recent_changes="v1.0.0 deploy",
        confirmed_root_cause="max_connections reached",
        resolution="Increased pool limit to 300",
        runbook_used="RB-PG-POOL",
        lesson_learned="Monitor pool usage",
        bank_id=bank_id
    )
    assert retain_res["status"] == "success"
    assert retain_res["source"] == "local_fallback"

    # 3. Memory-backed second stage
    recalled = memory.recall_similar_incidents(
        query="Database connection timeout max_connections",
        service="payment-service",
        bank_id=bank_id
    )
    assert len(recalled) == 1
    assert "INC-MEMORY-1" in recalled[0]["content"]

def test_hindsight_cloud_mocked_retain_and_recall():
    mock_client = MagicMock()

    mock_recall_result = MagicMock()
    mock_item = MagicMock()
    mock_item.text = "INCIDENT MEMORY RECORD: Root Cause: Memory leak in auth worker"
    mock_item.type = "incident_resolution"
    mock_recall_result.results = [mock_item]
    mock_client.recall.return_value = mock_recall_result

    with patch.object(config, "HINDSIGHT_API_KEY", "mock_key"):
        with patch("memory.get_hindsight_client", return_value=mock_client):
            # Retain test
            retain_res = memory.retain_incident_resolution(
                incident_id="INC-CLOUD-1",
                service="auth-service",
                severity="CRITICAL",
                description="Memory leak",
                error_logs="OOMKilled",
                recent_changes="v2.0",
                confirmed_root_cause="Worker leak",
                resolution="Restarted worker",
                runbook_used="RB-AUTH-OOM",
                lesson_learned="Set mem limits",
                bank_id="cloud-bank"
            )
            assert retain_res["status"] == "success"
            assert retain_res["source"] == "hindsight_cloud"
            mock_client.retain.assert_called_once()

            # Recall test
            recalled = memory.recall_similar_incidents(
                query="Memory leak OOMKilled",
                service="auth-service",
                bank_id="cloud-bank"
            )
            assert len(recalled) == 1
            assert recalled[0]["source"] == "hindsight_cloud"
            assert "Memory leak" in recalled[0]["content"]
            mock_client.recall.assert_called_once_with(
                bank_id="cloud-bank",
                query="Memory leak OOMKilled",
                tags=["auth-service"],
                budget="mid"
            )

def test_hindsight_cloud_error_handling():
    mock_client = MagicMock()
    mock_client.recall.side_effect = Exception("Connection refused to Hindsight Cloud")

    with patch.object(config, "HINDSIGHT_API_KEY", "mock_key"):
        with patch("memory.get_hindsight_client", return_value=mock_client):
            with pytest.raises(RuntimeError, match="Connection refused to Hindsight Cloud"):
                memory.recall_similar_incidents(query="test", bank_id="fail-bank")

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
        "content": "INCIDENT MEMORY RECORD:\nRoot cause: Deadlock due to out-of-order locks\nResolution: Sorted locking order"
    }]

    report = llm.generate_investigation_report(inc, recalled_mems)
    assert report is not None
    assert len(report) > 50
