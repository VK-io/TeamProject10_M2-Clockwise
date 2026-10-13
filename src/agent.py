import sys
import json
from pathlib import Path
from src.canvas_client import fetch_active_courses, fetch_course_assignments
from src.state import compute_diff_and_update
from src.llm import query_nrp

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

    #Run state snapshot and diff
    changes = compute_diff_and_update(assignments_data, db_path=db_path)

    #Core Value Prop: Silence if nothing changed
    if not changes:
        print("no material changes")
        return

    #Pass only changes to LLM for triage & concise compose
    prompt = (
        "You are an agent named Clockwise, a concise, encouraging academic assistant."
        f"Detected Canvas changes:\n{json.dumps(changes, indent=2)}\n\n"
        "Draft a clear 2-3 sentence notification summarizing these changes for a tired student. "
        "Sort them by due date, flag anything due within 48 hours."
        "Explicitly label items as NEW or CHANGED (with old -> new date)."
        "Never invent assignments or dates. If Canvas returned nothing, say so!."
    )
    
    try:
        digest = query_nrp(prompt)
        print("\n--- Agent Digest ---")
        print(digest)
    except Exception as e:
        print(f"LLM call failed: {e}")

if __name__ == "__main__":
    is_offline = "--offline" in sys.argv
    run_agent(offline=is_offline)