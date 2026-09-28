from fastmcp import FastMCP
from typing import List, Dict, Any
from src.canvas_client import fetch_active_courses, fetch_course_assignments

mcp = FastMCP("CanvasMCP")

@mcp.tool()
def list_courses() -> List[Dict[str, Any]]:
    """Fetch all active courses for the student."""
    return fetch_active_courses()

@mcp.tool()
def list_assignments(course_id: int) -> List[Dict[str, Any]]:
    """Fetch all assignments for a given course ID."""
    return fetch_course_assignments(course_id)

if __name__ == "__main__":
    mcp.run()