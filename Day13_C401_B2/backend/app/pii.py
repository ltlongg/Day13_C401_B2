from __future__ import annotations

import hashlib
import re
from typing import Final

PII_PATTERNS: dict[str, str] = {
    "email": r"[\w\.-]+@[\w\.-]+\.\w+",
    "phone_vn": r"(?:\+84|0)[ \.-]?\d{3}[ \.-]?\d{3}[ \.-]?\d{3,4}",
    "cccd": r"\b\d{12}\b",
    "credit_card": r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
    "passport": r"\b(?:[A-Z]{1,2}\d{7,8})\b",
    "address": (
        r"\b(?:so|số)?\s*\d+[a-z0-9/-]*(?:,\s*|\s+)"
        r"(?:duong|đường|pho|phố|hem|hẻm|ngo|ngõ|street|st\.?|road|rd\.?|"
        r"avenue|ave\.?|lane|ln\.?|boulevard|blvd\.?)[^,\n;]*"
        r"(?:,\s*(?:ap|ấp|thon|thôn|to|tổ|kp|khu pho|khu phố|xa|xã|"
        r"phuong|phường|quan|quận|huyen|huyện|tinh|tỉnh|tp\.?|thanh pho|"
        r"thành phố|ward|district|city)[^,\n;]*)*"
    ),
}

COMPILED_PII_PATTERNS: Final[tuple[tuple[str, re.Pattern[str]], ...]] = tuple(
    (name, re.compile(pattern, flags=re.IGNORECASE))
    for name, pattern in PII_PATTERNS.items()
)


def scrub_text(text: str) -> str:
    safe = text
    for name, pattern in COMPILED_PII_PATTERNS:
        safe = re.sub(pattern, f"[REDACTED_{name.upper()}]", safe)
    return safe


def summarize_text(text: str, max_len: int = 80) -> str:
    safe = scrub_text(text).strip().replace("\n", " ")
    return safe[:max_len] + ("..." if len(safe) > max_len else "")


def hash_user_id(user_id: str) -> str:
    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:12]
