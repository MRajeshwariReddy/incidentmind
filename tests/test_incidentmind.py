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

def test_hindsight_and_groq_configuration():
    assert config.HINDSIGHT_API_URL == "https://api.hindsight.vectorize.io"
    assert config.GROQ_MODEL == "openai/gpt-oss-120b"

def test_learning_demo_isolation_local_fallback():
    memory.clear_local_memory_store()
    demo_bank_id = "test-learning-demo-bank-123"

    # Step 1: Explicit bank creation
    bank_res = memory.create_memory_bank(bank_id=demo_bank_id)
    assert bank_res["status"] == "success"

    # Step 2: First recall on fresh bank MUST return exactly 0 memories
    first_recall = memory.recall_similar_incidents(
        query="PostgreSQL connection timeout max_connections",
        service="payment-gateway",
        bank_id=demo_bank_id
    )
    assert len(first_recall) == 0, "Fresh bank must start with zero memories"

    # Step 3: Retain incident experience into the same bank
    memory.retain_incident_resolution(
        incident_id="INC-DEMO-100",
        service="payment-gateway",
        severity="CRITICAL",
        description="PostgreSQL connection timeout",
        error_logs="pq: connection timeout",
        recent_changes="v1.0 deploy",
        confirmed_root_cause="max_connections limit reached",
        resolution="Increased max_connections to 300",
        runbook_used="RB-PG-POOL",
        lesson_learned="Monitor pool usage",
        bank_id=demo_bank_id
    )

    # Step 4: Second recall on same bank MUST retrieve the retained memory
    second_recall = memory.recall_similar_incidents(
        query="PostgreSQL connection timeout max_connections",
        service="payment-gateway",
        bank_id=demo_bank_id
    )
    assert len(second_recall) == 1
    assert "INC-DEMO-100" in second_recall[0]["content"]

    # Step 5: Verify an isolated different bank returns 0 memories
    isolated_bank_recall = memory.recall_similar_incidents(
        query="PostgreSQL connection timeout max_connections",
        service="payment-gateway",
        bank_id="other-isolated-bank"
    )
    assert len(isolated_bank_recall) == 0

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

            recalled = memory.recall_similar_incidents(
                query="Memory leak OOMKilled",
                service="auth-service",
                bank_id="cloud-bank"
            )
            assert len(recalled) == 1
            assert recalled[0]["source"] == "hindsight_cloud"
            assert "Memory leak" in recalled[0]["content"]

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
