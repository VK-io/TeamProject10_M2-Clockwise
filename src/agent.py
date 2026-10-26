import sys
import json
from datetime import datetime, timezone
from pathlib import Path
from src.canvas_client import fetch_active_courses, fetch_course_assignments
from src.state import compute_diff_and_update, has_snapshot
from src.report import build_report, parse_due, format_due
from src.llm import query_nrp

NOTIFY_EVENTS = ("NEW", "DUE_DATE_MOVED")

def run_agent(offline: bool = False, db_path: str = "clockwise.db"):
    assignments_data = []

    if offline:
        fixtures_dir = Path("tests/fixtures")
        assignments_file = fixtures_dir / "assignments.json"
        if not assignments_file.exists():
            print("Error: Offline fixtures not found in tests/fixtures/")
            sys.exit(1)

        with open(assignments_file) as f:
            assignments_data = json.load(f)
        with open(fixtures_dir / "courses.json") as f:
            courses = json.load(f)
        print(f"[OFFLINE] Loaded {len(assignments_data)} assignment(s).")

    else:
        try:
            courses = fetch_active_courses()
            for course in courses:
                c_assignments = fetch_course_assignments(course["id"])
                assignments_data.extend(c_assignments)
            print(f"Fetched {len(assignments_data)} active assignment(s) from Canvas.")
        except Exception as e:
            print(f"Canvas fetch failed: {e}")
            sys.exit(1)

    course_names = {c["id"]: c["name"] for c in courses}
    for a in assignments_data:
        a["course_name"] = course_names.get(a["course_id"], str(a["course_id"]))

    #First run records a baseline so existing coursework isn't reported as NEW
    first_run = not has_snapshot(db_path)
    changes = compute_diff_and_update(assignments_data, db_path=db_path)
    if first_run:
        print(f"Baseline saved ({len(assignments_data)} assignment(s)). Future runs will report changes.")
        return

    #Core Value Prop: Silence unless something was added or a deadline moved
    triggers = [c for c in changes if c["event_type"] in NOTIFY_EVENTS]
    if not triggers:
        print("no material changes")
        return

    now = datetime.now(timezone.utc)
    for c in triggers:
        c["course_name"] = course_names.get(c["course_id"], str(c["course_id"]))
        due = parse_due(c.get("due_at") or c.get("new_due_at"))
        c["past_due"] = bool(due and due < now)
        for key in ("due_at", "old_due_at", "new_due_at"):
            if key in c:
                c[key] = format_due(c[key])

    #Pass only changes to LLM for triage & concise compose
    prompt = (
        f"Detected Canvas changes:\n{json.dumps(triggers, indent=2)}\n\n"
        "Draft a clear 2-3 sentence notification summarizing these changes for a tired student. "
        "Refer to courses by course_name. Explicitly label items as NEW or CHANGED (with old -> new date), "
        "and say PAST DUE for any item where past_due is true. "
        "Only describe the listed changes; a full upcoming/past-due list follows separately, "
        "so do not make claims about any other assignments (e.g. never say nothing is past due)."
    )

    print("\n--- Agent Digest ---")
    try:
        print(query_nrp(prompt))
    except Exception as e:
        print(f"LLM call failed: {e}")
    print()
    print(build_report(assignments_data, now))

if __name__ == "__main__":
    #Windows consoles default to cp1252, which can't print some characters the LLM returns
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    is_offline = "--offline" in sys.argv
    run_agent(offline=is_offline)
