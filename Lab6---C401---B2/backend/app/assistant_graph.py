import re
import time
from typing import Any, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from app.agents.executor import execute_and_respond
from app.fallback.handler import get_fallback_response
from app.general.generator import generate_general_response, should_use_general_chat
from app.incidents import is_enabled
from app.logging_config import get_logger
from app.mock_data.students import get_student_info
from app.rag.generator import generate_rag_response
from app.rag.retrieval import retrieve
from app.router import detect_routes, get_search_query

log = get_logger()


class AssistantState(TypedDict, total=False):
    query: str
    student_id: str | None
    rag_calls: list[dict[str, Any]]
    agent_calls: list[dict[str, Any]]
    results: list[dict[str, Any]]
    response: str
    sources: list
    tool_used: str


TOOL_LABELS = {
    "get_schedule": "lịch học",
    "get_grades": "bảng điểm",
    "get_exam": "lịch thi",
    "get_tuition": "học phí",
}


def _combine_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    if len(results) == 1:
        return results[0]

    combined_response = "\n\n---\n\n".join(result["response"] for result in results)
    all_sources: list = []
    all_tools: list[str] = []
    student_id = None

    for result in results:
        all_sources.extend(result.get("sources", []))
        if result.get("tool_used"):
            all_tools.extend(
                [part.strip() for part in result["tool_used"].split(",") if part.strip()]
            )
        if result.get("student_id"):
            student_id = result["student_id"]

    seen = set()
    unique_sources = []
    for src in all_sources:
        key = src["doc_id"] if isinstance(src, dict) else src
        if key not in seen:
            seen.add(key)
            unique_sources.append(src)

    return {
        "response": combined_response,
        "sources": unique_sources,
        "tool_used": ", ".join(dict.fromkeys(all_tools)),
        "student_id": student_id,
    }


def _extract_student_id(text: str) -> str:
    """Extract a student ID token from free-form text."""
    match = re.search(r"\b([A-Za-z]{1,4}\d{2,6})\b", text)
    if match:
        return match.group(1).upper()
    return text.strip().upper()


def _format_tool_list(tool_calls: list[dict[str, Any]]) -> str:
    labels = [TOOL_LABELS.get(tool_call["name"], tool_call["name"]) for tool_call in tool_calls]
    unique_labels = list(dict.fromkeys(labels))

    if not unique_labels:
        return "thông tin cá nhân"
    if len(unique_labels) == 1:
        return unique_labels[0]
    return ", ".join(unique_labels[:-1]) + f" và {unique_labels[-1]}"


def _build_student_id_prompt(
    state: AssistantState,
    invalid_student_id: str | None = None,
) -> dict[str, Any]:
    results = state.get("results", [])
    tool_text = _format_tool_list(state.get("agent_calls", []))

    if invalid_student_id:
        prompt = (
            f"Không tìm thấy sinh viên với mã số: {invalid_student_id}. "
            f"Vui lòng nhập lại MSSV hợp lệ để mình tra cứu {tool_text}. "
            "Bạn có thể dùng các mã demo như: SV001, SV002, SV003."
        )
    else:
        prompt = (
            f"Để mình tra cứu {tool_text} cho bạn, vui lòng cho mình biết MSSV "
            "(ví dụ: SV001)."
        )

    if results:
        combined = _combine_results(results)
        message = f"{combined['response']}\n\n---\n\n{prompt}"
        tools = [combined.get("tool_used", ""), "needs_student_id"]
        sources = combined.get("sources", [])
    else:
        message = prompt
        tools = ["needs_student_id"]
        sources = []

    tool_used = ", ".join(
        dict.fromkeys(
            part.strip()
            for tool_name in tools
            for part in tool_name.split(",")
            if part.strip()
        )
    )

    return {
        "message": message,
        "sources": sources,
        "tool_used": tool_used,
    }


def route_query_node(state: AssistantState) -> dict[str, Any]:
    query = state["query"]
    route_result = detect_routes(query)

    return {
        "rag_calls": route_result["rag_calls"],
        "agent_calls": route_result["agent_calls"],
        "results": [],
        "response": "",
        "sources": [],
        "tool_used": "",
    }


def run_rag_node(state: AssistantState) -> dict[str, Any]:
    rag_calls = state.get("rag_calls", [])
    if not rag_calls:
        return {}

    results = list(state.get("results", []))
    query = state["query"]

    for rag_call in rag_calls:
        if is_enabled("rag_slow"):
            log.warning(
                "incident_triggered",
                service="assistant",
                incident="rag_slow",
                payload={"query": query[:120]},
            )
            time.sleep(2.5)
        search_query = get_search_query(rag_call, query)
        chunks = retrieve(search_query)
        rag_result = generate_rag_response(search_query, chunks)
        if rag_result:
            results.append(rag_result)

    return {"results": results}


def collect_student_id_node(state: AssistantState) -> dict[str, Any]:
    agent_calls = state.get("agent_calls", [])
    if not agent_calls:
        return {}

    current_student_id = state.get("student_id")
    if current_student_id and get_student_info(current_student_id):
        return {}

    prompt = _build_student_id_prompt(state)

    while True:
        answer = interrupt(prompt)
        student_id = _extract_student_id(str(answer))

        if get_student_info(student_id):
            return {"student_id": student_id}

        prompt = _build_student_id_prompt(state, invalid_student_id=student_id)


def run_agent_tools_node(state: AssistantState) -> dict[str, Any]:
    agent_calls = state.get("agent_calls", [])
    if not agent_calls:
        return {}

    student_id = state.get("student_id")
    if not student_id:
        return {}

    results = list(state.get("results", []))
    agent_result = execute_and_respond(agent_calls, state["query"], student_id)
    results.append(agent_result)
    return {"results": results}


def finalize_response_node(state: AssistantState) -> dict[str, Any]:
    results = state.get("results", [])

    if not results:
        if should_use_general_chat(state["query"]):
            return generate_general_response(state["query"])

        fallback = get_fallback_response()
        return {
            "response": fallback["response"],
            "sources": fallback.get("sources", []),
            "tool_used": fallback.get("tool_used", "fallback"),
        }

    combined = _combine_results(results)
    return {
        "response": combined["response"],
        "sources": combined.get("sources", []),
        "tool_used": combined.get("tool_used", "unknown"),
    }


def build_assistant_graph():
    workflow = StateGraph(AssistantState)
    workflow.add_node("route_query", route_query_node)
    workflow.add_node("run_rag", run_rag_node)
    workflow.add_node("collect_student_id", collect_student_id_node)
    workflow.add_node("run_agent_tools", run_agent_tools_node)
    workflow.add_node("finalize_response", finalize_response_node)

    workflow.add_edge(START, "route_query")
    workflow.add_edge("route_query", "run_rag")
    workflow.add_edge("run_rag", "collect_student_id")
    workflow.add_edge("collect_student_id", "run_agent_tools")
    workflow.add_edge("run_agent_tools", "finalize_response")
    workflow.add_edge("finalize_response", END)

    checkpointer = InMemorySaver()
    return workflow.compile(checkpointer=checkpointer)


assistant_graph = build_assistant_graph()


def _thread_config(thread_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": thread_id}}


def thread_has_pending_interrupt(thread_id: str) -> bool:
    snapshot = assistant_graph.get_state(_thread_config(thread_id))
    return any(task.interrupts for task in snapshot.tasks)


def run_assistant_turn(
    thread_id: str, message: str, student_id: str | None = None
) -> dict[str, Any]:
    config = _thread_config(thread_id)

    if thread_has_pending_interrupt(thread_id):
        result = assistant_graph.invoke(Command(resume=message), config=config)
    else:
        initial_state: dict[str, Any] = {"query": message}
        if student_id:
            initial_state["student_id"] = student_id
        result = assistant_graph.invoke(initial_state, config=config)

    if "__interrupt__" in result:
        interrupt_value = result["__interrupt__"][0].value
        return {
            "response": interrupt_value["message"],
            "sources": interrupt_value.get("sources", []),
            "tool_used": interrupt_value.get("tool_used", "needs_student_id"),
            "requires_student_id": True,
            "student_id": result.get("student_id"),
            "thread_id": thread_id,
        }

    return {
        "response": result["response"],
        "sources": result.get("sources", []),
        "tool_used": result.get("tool_used", "unknown"),
        "requires_student_id": False,
        "student_id": result.get("student_id"),
        "thread_id": thread_id,
    }
