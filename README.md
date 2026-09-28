# Clockwise — Canvas Deadline Change Agent

## 1. Problem Addressed
Clockwise prevents students from missing coursework caused by post-syllabus schedule shifts by monitoring Canvas course feeds and surfacing assignment changes rather than static task snapshots.

## 2. Current Capabilities
- Queries Canvas REST endpoints for active courses and assignment schedules via an integrated MCP tool interface.
- Stores baseline assignment states within a local SQLite database and diffs current data against historical snapshots.
- Detects assignment creations, deletions, and modified due dates (`due_at`).
- Leverages an NRP-hosted model to triage material modifications and generate an actionable, 2–3 sentence digest.
- Contains an offline mode (`--offline`) using scrubbed fixture payloads to evaluate behavior without network access.

## 3. Intentionally Deferred Capabilities
- Multi-agent collaboration, critics, and dynamic task-loop handoffs (scheduled for M3).
- Vector databases, semantic retrieval (RAG), and persistent long-term student memory layers.
- Hosted web user interfaces, authentication databases, and automated calendar synchronization.
- Direct notification delivery engines (e.g., SMTP transport or SMS).

## 4. Setup and Execution
1. Clone the repository and establish a virtual environment:
   ```bash
   python -m venv venv
   # On macOS/Linux:
   source venv/bin/activate
   # On Windows (Git Bash):
   source venv/Scripts/activate
   pip install -r requirements.txt
2. Run the test suite (NOT IMPLEMENTED YET):
   ```bash
   pytest
3. Execute locally:
   ```bash
   # Offline mode using /tests/fixtures
   python -m -src.agent --offline
   # Live execution via Canvas API
   python -m -src.agent

## 5. Known Limitations
- Assignments lacking an explicit `due_at` timestamp are bypassed during timeline diff calculations.
- Self-service Canvas API token creation depends on institution-level policy and cannot be generated programmatically if disabled by FGCU.
- Rapid assignment metadata updates that occur between polling cycles only capture the net difference between snapshots, omitting intermediate changes.

