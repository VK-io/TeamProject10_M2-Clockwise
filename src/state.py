import sqlite3
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

DB_PATH = "clockwise.db"

def init_db(db_path: str = DB_PATH):
    """Initializes the SQLite schema."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assignments_snapshot (
                id INTEGER PRIMARY KEY,
                course_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                due_at TEXT,
                updated_at TEXT,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL
            )
        """)
        conn.commit()

def get_current_snapshot(db_path: str = DB_PATH) -> Dict[int, Dict[str, Any]]:
    """Retrieves all previously recorded assignments indexed by ID."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, course_id, name, due_at, updated_at FROM assignments_snapshot")
        rows = cursor.fetchall()
        return {
            row[0]: {
                "id": row[0],
                "course_id": row[1],
                "name": row[2],
                "due_at": row[3],
                "updated_at": row[4]
            }
            for row in rows
        }

def compute_diff_and_update(current_assignments: List[Dict[str, Any]], db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """
    Compares fetched assignments against previous SQLite snapshot,
    updates database records, and emits ChangeEvent objects.
    """
    init_db(db_path)
    previous_snapshot = get_current_snapshot(db_path)
    now_iso = datetime.now(timezone.utc).isoformat()
    changes = []

    current_ids = {a["id"] for a in current_assignments}

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        #1. Check for NEW and DUE_DATE_MOVED
        for assign in current_assignments:
            a_id = assign["id"]
            due_at = assign.get("due_at")
            updated_at = assign.get("updated_at")
            course_id = assign["course_id"]
            name = assign.get("name", "Untitled")

            if a_id not in previous_snapshot:
                #Event: NEW
                changes.append({
                    "event_type": "NEW",
                    "assignment_id": a_id,
                    "name": name,
                    "course_id": course_id,
                    "due_at": due_at
                })
                cursor.execute("""
                    INSERT INTO assignments_snapshot (id, course_id, name, due_at, updated_at, first_seen, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (a_id, course_id, name, due_at, updated_at, now_iso, now_iso))

            else:
                old = previous_snapshot[a_id]
                #Compare due dates (normalize None and strings)
                if (old["due_at"] or "") != (due_at or ""):
                    #Event: DUE_DATE_MOVED
                    changes.append({
                        "event_type": "DUE_DATE_MOVED",
                        "assignment_id": a_id,
                        "name": name,
                        "course_id": course_id,
                        "old_due_at": old["due_at"],
                        "new_due_at": due_at
                    })

                #Refresh metadata & last_seen
                cursor.execute("""
                    UPDATE assignments_snapshot
                    SET name = ?, due_at = ?, updated_at = ?, last_seen = ?
                    WHERE id = ?
                """, (name, due_at, updated_at, now_iso, a_id))

        #2. Check for REMOVED assignments
        for old_id, old_data in previous_snapshot.items():
            if old_id not in current_ids:
                changes.append({
                    "event_type": "REMOVED",
                    "assignment_id": old_id,
                    "name": old_data["name"],
                    "course_id": old_data["course_id"]
                })
                cursor.execute("DELETE FROM assignments_snapshot WHERE id = ?", (old_id,))

        conn.commit()

    return changes