import os
import re
import json
from crewai import Agent, Crew, Process, Task
from langchain_community.chat_models import ChatOllama
from agents.attendance_tools import (
    create_session_tool, mark_attendance_tool, summary_tool, export_csv_tool
)


def make_llm():
    """Create LLM instance - uses Ollama by default, can be configured via env"""
    # Check if Ollama model is specified, otherwise use default
    model = os.getenv("OLLAMA_MODEL", "llama3.1")
    # Ensure Ollama is running: `ollama serve` (normally auto-starts)
    return ChatOllama(model=model, temperature=0.2)


llm = make_llm()

supervisor = Agent(
    name="Supervisor",
    role="Understands teacher requests and routes to the right tool",
    goal="Classify intent and craft a valid JSON payload for the chosen tool.",
    backstory="You are precise. If fields are missing, ask minimally.",
    llm=llm,
    verbose=True
)

attendance_agent = Agent(
    name="AttendanceAgent",
    role="Executes attendance operations via tools",
    goal="Call the right tool and return short confirmations.",
    backstory="Never guess IDs; keep answers short.",
    tools=[create_session_tool, mark_attendance_tool, summary_tool, export_csv_tool],
    llm=llm,
    verbose=True
)

ROUTER = """
Decide which tool to use and build JSON for it.

TOOLS:
- create_session: {"teacher_id": int, "class_id": int, "subject_id": int, "date_str": "YYYY-MM-DD|today|DD-MM-YYYY"}
- mark_attendance: {"session_id": int?,"teacher_id": int?,"class_id": int?,"subject_id": int?,"date_str": str?,"present_rolls": "1,2,5-10 except 7"}
- summary: {"subject_id": int}
- export_csv: {"subject_id": int}

Output strictly:
TOOL=<create_session|mark_attendance|summary|export_csv|ASK>
<JSON>
"""


def build_crew():
    """Build and return the attendance crew"""
    router_task = Task(
        description=ROUTER,
        expected_output="TOOL=...\\n{...}",
        agent=supervisor
    )
    exec_task = Task(
        description=(
            "If TOOL=ASK -> return that JSON. Else call the tool with the JSON payload. "
            "Respond briefly with key info; include filename for export_csv."
        ),
        expected_output="JSON response",
        agent=attendance_agent
    )
    return Crew(
        agents=[supervisor, attendance_agent],
        tasks=[router_task, exec_task],
        process=Process.sequential,
        verbose=True
    )
