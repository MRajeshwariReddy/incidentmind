import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
import config

def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = db_path or config.DATABASE_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path: Optional[str] = None) -> None:
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            incident_id TEXT PRIMARY KEY,
            service TEXT NOT NULL,
            severity TEXT NOT NULL,
            description TEXT NOT NULL,
            error_logs TEXT,
            recent_changes TEXT,
            timestamp TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'OPEN',
            investigation_report TEXT,
            recalled_memories TEXT,
            confirmed_root_cause TEXT,
            resolution TEXT,
            runbook_used TEXT,
            lesson_learned TEXT,
            resolved_at TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def create_incident(incident_data: Dict[str, Any], db_path: Optional[str] = None) -> str:
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    incident_id = incident_data.get("incident_id")
    if not incident_id:
        timestamp_code = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        incident_id = f"INC-{timestamp_code}"

    created_at = datetime.utcnow().isoformat() + "Z"
    timestamp = incident_data.get("timestamp") or created_at

    cursor.execute("""
        INSERT INTO incidents (
            incident_id, service, severity, description, error_logs,
            recent_changes, timestamp, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        incident_id,
        incident_data.get("service", "Unknown Service"),
        incident_data.get("severity", "MEDIUM"),
        incident_data.get("description", ""),
        incident_data.get("error_logs", ""),
        incident_data.get("recent_changes", ""),
        timestamp,
        incident_data.get("status", "OPEN"),
        created_at
    ))
    conn.commit()
    conn.close()
    return incident_id

def update_incident_investigation(
    incident_id: str,
    investigation_report: str,
    recalled_memories: List[Dict[str, Any]],
    db_path: Optional[str] = None
) -> None:
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE incidents
        SET investigation_report = ?,
            recalled_memories = ?
        WHERE incident_id = ?
    """, (
        investigation_report,
        json.dumps(recalled_memories, ensure_ascii=False),
        incident_id
    ))
    conn.commit()
    conn.close()

def resolve_incident(
    incident_id: str,
    confirmed_root_cause: str,
    resolution: str,
    runbook_used: str,
    lesson_learned: str,
    db_path: Optional[str] = None
) -> None:
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    resolved_at = datetime.utcnow().isoformat() + "Z"
    cursor.execute("""
        UPDATE incidents
        SET confirmed_root_cause = ?,
            resolution = ?,
            runbook_used = ?,
            lesson_learned = ?,
            status = 'RESOLVED',
            resolved_at = ?
        WHERE incident_id = ?
    """, (
        confirmed_root_cause,
        resolution,
        runbook_used,
        lesson_learned,
        resolved_at,
        incident_id
    ))
    conn.commit()
    conn.close()

def get_incident(incident_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM incidents WHERE incident_id = ?", (incident_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    data = dict(row)
    if data.get("recalled_memories"):
        try:
            data["recalled_memories"] = json.loads(data["recalled_memories"])
        except Exception:
            data["recalled_memories"] = []
    else:
        data["recalled_memories"] = []
    return data

def list_incidents(
    status_filter: Optional[str] = None,
    limit: int = 50,
    db_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    if status_filter:
        cursor.execute(
            "SELECT * FROM incidents WHERE status = ? ORDER BY created_at DESC LIMIT ?",
            (status_filter, limit)
        )
    else:
        cursor.execute(
            "SELECT * FROM incidents ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
    rows = cursor.fetchall()
    conn.close()

    result = []
    for row in rows:
        data = dict(row)
        if data.get("recalled_memories"):
            try:
                data["recalled_memories"] = json.loads(data["recalled_memories"])
            except Exception:
                data["recalled_memories"] = []
        else:
            data["recalled_memories"] = []
        result.append(data)
    return result

def get_dashboard_stats(db_path: Optional[str] = None) -> Dict[str, Any]:
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM incidents")
    total_incidents = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM incidents WHERE status = 'RESOLVED'")
    resolved_incidents = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM incidents WHERE status = 'OPEN'")
    open_incidents = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM incidents WHERE recalled_memories IS NOT NULL AND recalled_memories != '[]'")
    incidents_with_recall = cursor.fetchone()[0]

    conn.close()

    return {
        "total_incidents": total_incidents,
        "resolved_incidents": resolved_incidents,
        "open_incidents": open_incidents,
        "incidents_with_recall": incidents_with_recall
    }
