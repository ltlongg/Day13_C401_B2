from __future__ import annotations

STATE: dict[str, bool] = {
    "rag_slow": False,
    "tool_fail": False,
    "llm_fault": False,
}


def enable(name: str) -> None:
    """Bat incident theo ten da chot trong integration contract."""
    if name not in STATE:
        raise KeyError(f"Unknown incident: {name}")
    STATE[name] = True


def disable(name: str) -> None:
    """Tat incident theo ten da chot trong integration contract."""
    if name not in STATE:
        raise KeyError(f"Unknown incident: {name}")
    STATE[name] = False


def is_enabled(name: str) -> bool:
    """Helper cho thanh vien D hook incident vao flow thuc te."""
    if name not in STATE:
        raise KeyError(f"Unknown incident: {name}")
    return STATE[name]


def status() -> dict[str, bool]:
    """Tra ve snapshot hien tai de /health hoac /incidents dung khi debug."""
    return dict(STATE)
