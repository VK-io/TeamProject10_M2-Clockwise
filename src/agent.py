import sys
import json
from pathlib import Path
from src.canvas_client import fetch_active_courses, fetch_course_assignments
from src.llm import query_nrp

def run_agent(offline: bool = False):
    assignments_data = []

    if offline:
        fixtures_dir = Path("tests/fixtures")
        assignments_file = fixtures_dir / "assignments.json"

        if not assignments_file.exists():
            print("Error: Offline fixtures not found in tests/fixtures/")
            sys.exit(1)

        with open(assignments_file) as f:
            assignments_data = json.load(f)
        print(f"[OFFLINE] Loaded {len(assignments_data)} assignment(s) from fixture.")

    else:
        # Live Canvas fetch
        try:
            courses = fetch_active_courses()
            print(f"Discovered {len(courses)} active course(s). Fetching assignments...")
            for course in courses:
                course_assignments = fetch_course_assignments(course["id"])
                for a in course_assignments:
                    a["course_name"] = course["name"]
                assignments_data.extend(course_assignments)
        except Exception as e:
            print(f"Canvas fetch failed: {e}")
            sys.exit(1)

    if not assignments_data:
        print("No assignments found.")
        return

    # Pass assignments to NRP via llm.py
    prompt = f"Here is the student's current assignment data:\n{json.dumps(assignments_data, indent=2)}\n\nSummarize the pending deadlines in 2-3 concise sentences."
    print("\nSending payload to NRP (gpt-oss)...")
    
    try:
        summary = query_nrp(prompt)
        print("\n--- Agent Summary ---")
        print(summary)
    except Exception as e:
        print(f"LLM call failed: {e}")

if __name__ == "__main__":
    is_offline = "--offline" in sys.argv
    run_agent(offline=is_offline)