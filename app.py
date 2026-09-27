import streamlit as st
import database
import memory
import llm
import config
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="IncidentMind - AI Incident Response Agent",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize DB
database.init_db()

# Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.0rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 1.2rem;
        margin-bottom: 1rem;
    }
    .metric-badge {
        background-color: #3B82F6;
        color: white;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 0.85rem;
    }
    .status-open {
        background-color: #FEF2F2;
        color: #991B1B;
        border: 1px solid #FCA5A5;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    .status-resolved {
        background-color: #F0FDF4;
        color: #166534;
        border: 1px solid #86EFAC;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# Navigation
st.sidebar.image("https://img.icons8.com/color/96/brain--v1.png", width=64)
st.sidebar.title("IncidentMind")
st.sidebar.caption("AI Incident Response with Hindsight Memory")

page = st.sidebar.radio(
    "Navigation",
    [
        "📊 Dashboard",
        "🚨 Submit Incident",
        "🔍 Incident Details & Investigation",
        "✅ Resolve & Remember",
        "🧪 Learning Demonstration"
    ]
)

st.sidebar.divider()
st.sidebar.subheader("System Status")

hs_key_set = bool(config.HINDSIGHT_API_KEY)
groq_key_set = bool(config.GROQ_API_KEY)

st.sidebar.markdown(f"**Hindsight Cloud**: {'🟢 Connected' if hs_key_set else '🟡 Fallback Mode'}")
st.sidebar.markdown(f"**Groq LLM**: {'🟢 Connected' if groq_key_set else '🟡 Fallback Mode'}")
st.sidebar.caption(f"Bank ID: `{config.HINDSIGHT_BANK_ID}`")

# ---------------------------------------------------------
# PAGE 1: DASHBOARD
# ---------------------------------------------------------
if page == "📊 Dashboard":
    st.markdown("<div class='main-header'>Incident Response Dashboard</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-header'>Real-time incident tracking & historical memory operational metrics</div>", unsafe_allow_html=True)

    stats = database.get_dashboard_stats()
    mem_stats = memory.get_memory_stats()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Incidents", stats["total_incidents"])
    with col2:
        st.metric("Open Incidents", stats["open_incidents"])
    with col3:
        st.metric("Resolved Incidents", stats["resolved_incidents"])
    with col4:
        st.metric("Retained Memories", mem_stats["total_retained_memories"])

    st.divider()

    st.subheader("Recent Incidents")
    incidents = database.list_incidents(limit=20)

    if not incidents:
        st.info("No incidents recorded yet. Use 'Submit Incident' or 'Learning Demonstration' to get started!")
    else:
        for inc in incidents:
            with st.container():
                cols = st.columns([1.5, 2.5, 1, 1, 1.5, 1.5])
                with cols[0]:
                    st.markdown(f"**`{inc['incident_id']}`**")
                with cols[1]:
                    st.write(f"**{inc['service']}**: {inc['description'][:50]}...")
                with cols[2]:
                    st.write(f"Severity: `{inc['severity']}`")
                with cols[3]:
                    status_class = "status-resolved" if inc['status'] == "RESOLVED" else "status-open"
                    st.markdown(f"<span class='{status_class}'>{inc['status']}</span>", unsafe_allow_html=True)
                with cols[4]:
                    mem_count = len(inc.get('recalled_memories') or [])
                    st.caption(f"🧠 {mem_count} recalled")
                with cols[5]:
                    if st.button("Inspect", key=f"inspect_{inc['incident_id']}"):
                        st.session_state["selected_incident_id"] = inc['incident_id']
                        st.rerun()

# ---------------------------------------------------------
# PAGE 2: SUBMIT INCIDENT
# ---------------------------------------------------------
elif page == "🚨 Submit Incident":
    st.markdown("<div class='main-header'>Submit New Production Incident</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-header'>Input incident details to trigger memory recall & AI investigation</div>", unsafe_allow_html=True)

    with st.form("new_incident_form"):
        col1, col2 = st.columns(2)
        with col1:
            service = st.selectbox("Affected Service", ["payment-service", "auth-service", "checkout-api", "user-db", "notification-worker", "frontend-gateway"])
            severity = st.selectbox("Severity Level", ["CRITICAL", "HIGH", "MEDIUM", "LOW"])
        with col2:
            custom_id = st.text_input("Incident ID (Optional)", placeholder="e.g. INC-2025-001")
            recent_changes = st.text_input("Recent Deployment / Changes", placeholder="e.g. Deployed v2.1.4 with connection pool update")

        description = st.text_area("Symptom Description", placeholder="Describe what is failing, latency spikes, error rates, or alert details...")
        error_logs = st.text_area("Error Logs / Stack Traces", placeholder="Paste relevant log lines or error stack traces...")

        submitted = st.form_submit_button("🚀 Submit & Trigger AI Investigation", use_container_width=True)

        if submitted:
            if not description:
                st.error("Please provide a symptom description.")
            else:
                inc_id = custom_id if custom_id.strip() else f"INC-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
                incident_payload = {
                    "incident_id": inc_id,
                    "service": service,
                    "severity": severity,
                    "description": description,
                    "error_logs": error_logs,
                    "recent_changes": recent_changes,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "status": "OPEN"
                }

                with st.spinner("Recording incident & recalling Hindsight persistent memory..."):
                    created_id = database.create_incident(incident_payload)

                    # Core recall query
                    query = f"Service: {service}\nDescription: {description}\nLogs: {error_logs}\nChanges: {recent_changes}"
                    recalled_memories = memory.recall_similar_incidents(query=query, service=service)

                    # LLM Investigation
                    report = llm.generate_investigation_report(incident_payload, recalled_memories)

                    # Store report & recalled memories
                    database.update_incident_investigation(created_id, report, recalled_memories)

                st.success(f"Incident {created_id} created & investigated successfully!")
                st.session_state["selected_incident_id"] = created_id
                st.rerun()

# ---------------------------------------------------------
# PAGE 3: INCIDENT DETAILS & INVESTIGATION
# ---------------------------------------------------------
elif page == "🔍 Incident Details & Investigation":
    st.markdown("<div class='main-header'>AI Investigation & Memory Recall</div>", unsafe_allow_html=True)

    selected_id = st.session_state.get("selected_incident_id")
    incidents = database.list_incidents(limit=50)
    inc_ids = [inc["incident_id"] for inc in incidents]

    if not inc_ids:
        st.info("No incidents available. Please submit an incident first.")
    else:
        default_index = inc_ids.index(selected_id) if selected_id in inc_ids else 0
        incident_id = st.selectbox("Select Incident to Review", inc_ids, index=default_index)

        inc = database.get_incident(incident_id)
        if inc:
            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown("### Incident Metadata")
                st.write(f"**ID:** `{inc['incident_id']}`")
                st.write(f"**Service:** `{inc['service']}`")
                st.write(f"**Severity:** `{inc['severity']}`")
                status_class = "status-resolved" if inc['status'] == "RESOLVED" else "status-open"
                st.markdown(f"**Status:** <span class='{status_class}'>{inc['status']}</span>", unsafe_allow_html=True)
                st.write(f"**Timestamp:** {inc['timestamp']}")
                st.write(f"**Recent Deployment:** {inc['recent_changes'] or 'None'}")

                with st.expander("Symptom Description", expanded=True):
                    st.write(inc['description'])
                with st.expander("Error Logs"):
                    st.code(inc['error_logs'] or "No logs attached", language="text")

            with col2:
                recalled = inc.get("recalled_memories", [])
                st.markdown(f"### 🧠 Recalled Hindsight Experience ({len(recalled)} memories)")

                if not recalled:
                    st.info("No relevant historical incidents recalled from Hindsight memory. This appears to be a novel issue.")
                else:
                    for idx, mem in enumerate(recalled, 1):
                        score = mem.get("relevance_score", 0.0)
                        source = mem.get("source", "Hindsight")
                        with st.expander(f"Historical Memory #{idx} (Relevance: {score:.2f} | Source: {source})", expanded=True):
                            st.text(mem.get("content", ""))

            st.divider()
            st.markdown("### 🤖 AI Investigation Report")
            if inc.get("investigation_report"):
                st.markdown(inc["investigation_report"])
            else:
                st.warning("No investigation report generated for this incident.")

            if inc['status'] == "OPEN":
                if st.button("➡️ Proceed to Resolve & Remember", type="primary"):
                    st.session_state["selected_incident_id"] = inc['incident_id']
                    st.session_state["nav_to_resolve"] = True
                    st.rerun()

# ---------------------------------------------------------
# PAGE 4: RESOLVE & REMEMBER
# ---------------------------------------------------------
elif page == "✅ Resolve & Remember":
    st.markdown("<div class='main-header'>Resolve & Retain Experience</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-header'>Record confirmed resolution & store learnings directly into persistent Hindsight memory</div>", unsafe_allow_html=True)

    incidents = database.list_incidents(limit=50)
    open_incidents = [inc for inc in incidents if inc["status"] == "OPEN"]

    selected_id = st.session_state.get("selected_incident_id")

    if not open_incidents and not (selected_id and database.get_incident(selected_id)):
        st.success("All incidents are currently resolved! No open incidents pending resolution.")
    else:
        target_options = [inc["incident_id"] for inc in incidents]
        default_index = target_options.index(selected_id) if selected_id in target_options else 0

        target_id = st.selectbox("Select Incident to Resolve", target_options, index=default_index)
        inc = database.get_incident(target_id)

        if inc:
            st.info(f"Resolving **{inc['incident_id']}** for service **{inc['service']}**")

            with st.form("resolve_form"):
                root_cause = st.text_area("Confirmed Root Cause", placeholder="Explain what actually caused the incident...")
                resolution = st.text_area("Resolution Steps Executed", placeholder="Describe step-by-step how the issue was fixed...")
                runbook = st.text_input("Runbook Used / Created", placeholder="e.g. RB-PAYMENT-RESTART-03")
                lessons = st.text_area("Lessons Learned / Future Prevention", placeholder="What should be done to prevent this or make diagnosis faster next time?")

                submitted = st.form_submit_button("💾 Save Resolution & Retain in Hindsight Memory", use_container_width=True)

                if submitted:
                    if not root_cause or not resolution:
                        st.error("Please provide both confirmed root cause and resolution steps.")
                    else:
                        with st.spinner("Retaining experience in Hindsight persistent memory layer..."):
                            # 1. Update SQLite
                            database.resolve_incident(
                                incident_id=target_id,
                                confirmed_root_cause=root_cause,
                                resolution=resolution,
                                runbook_used=runbook,
                                lesson_learned=lessons
                            )

                            # 2. Retain in Hindsight
                            retain_resp = memory.retain_incident_resolution(
                                incident_id=target_id,
                                service=inc["service"],
                                severity=inc["severity"],
                                description=inc["description"],
                                error_logs=inc.get("error_logs", ""),
                                recent_changes=inc.get("recent_changes", ""),
                                confirmed_root_cause=root_cause,
                                resolution=resolution,
                                runbook_used=runbook,
                                lesson_learned=lessons
                            )

                        st.success(f"Incident {target_id} marked RESOLVED! Experience retained in Hindsight memory.")
                        st.json(retain_resp)

# ---------------------------------------------------------
# PAGE 5: LEARNING DEMONSTRATION
# ---------------------------------------------------------
elif page == "🧪 Learning Demonstration":
    st.markdown("<div class='main-header'>Hindsight Learning Demonstration</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='sub-header'>Demonstrate the complete memory loop: Initial Investigation (no memory) ➡️ Resolution Retained ➡️ Second Investigation (memory recalled)</div>",
        unsafe_allow_html=True
    )

    st.markdown("""
    ### 🔄 How the Learning Demonstration Works:
    1. **Incident 1 (First Encounter)**: A database connection pool exhaustion occurs on `payment-gateway`. AI investigates with **no historical memory**.
    2. **Resolve & Retain**: Engineer resolves Incident 1 (increasing connection limit in `pg_hba.conf`) and retains this lesson in Hindsight.
    3. **Incident 2 (Second Similar Encounter)**: A similar database connection timeout occurs on `payment-gateway`.
    4. **AI Recall & Response**: AI recalls the previous resolution from Hindsight and provides a **targeted, memory-driven recommendation**.
    """)

    if st.button("🚀 Run Full Interactive Learning Loop Demo", type="primary", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()

        # Step 1: Submit Incident 1
        status_text.write("Step 1/4: Submitting first incident (No prior memory)...")
        progress_bar.progress(20)

        inc1_id = f"DEMO-1-{datetime.utcnow().strftime('%H%M%S')}"
        inc1_data = {
            "incident_id": inc1_id,
            "service": "payment-gateway",
            "severity": "CRITICAL",
            "description": "Payment service dropping requests with DB connection timeout errors.",
            "error_logs": "pq: sorry, too many clients already | connection timed out after 5000ms",
            "recent_changes": "Deployed connection pool config change v1.2.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "OPEN"
        }
        database.create_incident(inc1_data)
        mem1 = memory.recall_similar_incidents(query=f"{inc1_data['description']} {inc1_data['error_logs']}", service="payment-gateway")
        report1 = llm.generate_investigation_report(inc1_data, mem1)
        database.update_incident_investigation(inc1_id, report1, mem1)

        # Step 2: Resolve & Retain Incident 1
        status_text.write("Step 2/4: Engineer resolves Incident 1 & retains experience in Hindsight...")
        progress_bar.progress(50)

        database.resolve_incident(
            incident_id=inc1_id,
            confirmed_root_cause="max_connections limit (100) reached in PostgreSQL master due to leak in v1.2.0 client library.",
            resolution="Increased max_connections to 300 and restarted connection pooler pgBouncer.",
            runbook_used="RB-PG-CONN-RECOVERY",
            lesson_learned="Set alert threshold at 80% connection capacity and check pgBouncer client leak."
        )
        memory.retain_incident_resolution(
            incident_id=inc1_id,
            service="payment-gateway",
            severity="CRITICAL",
            description=inc1_data["description"],
            error_logs=inc1_data["error_logs"],
            recent_changes=inc1_data["recent_changes"],
            confirmed_root_cause="max_connections limit (100) reached in PostgreSQL master due to leak in v1.2.0 client library.",
            resolution="Increased max_connections to 300 and restarted connection pooler pgBouncer.",
            runbook_used="RB-PG-CONN-RECOVERY",
            lesson_learned="Set alert threshold at 80% connection capacity and check pgBouncer client leak."
        )

        # Step 3: Submit Incident 2
        status_text.write("Step 3/4: Submitting second similar incident (Triggering Hindsight Recall)...")
        progress_bar.progress(80)

        inc2_id = f"DEMO-2-{datetime.utcnow().strftime('%H%M%S')}"
        inc2_data = {
            "incident_id": inc2_id,
            "service": "payment-gateway",
            "severity": "HIGH",
            "description": "Payment checkout failing with PostgreSQL connection timeouts under high load.",
            "error_logs": "fatal: remaining connection slots are reserved for non-replication superuser connections",
            "recent_changes": "Traffic surge during promo campaign",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "OPEN"
        }
        database.create_incident(inc2_data)
        mem2 = memory.recall_similar_incidents(query=f"{inc2_data['description']} {inc2_data['error_logs']}", service="payment-gateway")
        report2 = llm.generate_investigation_report(inc2_data, mem2)
        database.update_incident_investigation(inc2_id, report2, mem2)

        progress_bar.progress(100)
        status_text.success("Interactive Learning Loop Complete!")

        # Side-by-Side Comparison
        st.divider()
        st.subheader("📊 Side-by-Side Learning Comparison")

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"### 1️⃣ First Encounter (`{inc1_id}`)")
            st.markdown(f"**Recalled Memories**: `{len(mem1)}` (No prior context)")
            st.markdown(report1)

        with col_b:
            st.markdown(f"### 2️⃣ Second Encounter (`{inc2_id}`)")
            st.markdown(f"**Recalled Memories**: `{len(mem2)}` (Hindsight memory active)")
            for idx, m in enumerate(mem2, 1):
                st.success(f"🧠 Recalled Memory #{idx}: {m.get('content')[:120]}...")
            st.markdown(report2)
