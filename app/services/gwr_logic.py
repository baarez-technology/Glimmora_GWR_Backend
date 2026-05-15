"""
Server-side port of src/lib/gwr.ts logic.
Single source of truth for rest accrual and submission health.
"""
from dataclasses import dataclass, field
from typing import List, Optional


def _hhmm_to_minutes(hhmm: str) -> int:
    """Convert "HH:MM" to total minutes since midnight."""
    parts = hhmm.split(":")
    return int(parts[0]) * 60 + int(parts[1])


def _duration_minutes(start: str, end: str) -> int:
    """Duration in minutes, handling cross-midnight (end < start)."""
    s = _hhmm_to_minutes(start)
    e = _hhmm_to_minutes(end)
    if e < s:
        e += 24 * 60  # cross-midnight
    return max(0, e - s)


@dataclass
class LogbookRow:
    type: str  # "activity" | "rest"
    sequence: int
    start_hhmm: str
    end_hhmm: str
    notes: Optional[str] = None


@dataclass
class LogbookResult:
    entries: List[dict] = field(default_factory=list)
    total_activity_minutes: int = 0
    total_rest_minutes: int = 0
    accrued_rest_minutes: int = 0
    rest_balance_minutes: int = 0
    violations: List[str] = field(default_factory=list)


def compute_logbook(activity_rows: List[LogbookRow], rest_rows: List[LogbookRow]) -> LogbookResult:
    """
    GWR rest accrual rule: 5 minutes rest accrued per full uninterrupted hour of activity.
    Rest balance = accrued - used.
    """
    result = LogbookResult()

    total_activity = sum(_duration_minutes(r.start_hhmm, r.end_hhmm) for r in activity_rows)
    total_rest = sum(_duration_minutes(r.start_hhmm, r.end_hhmm) for r in rest_rows)

    # Accrued rest: 5 min per full 60-min activity block
    accrued = (total_activity // 60) * 5

    result.total_activity_minutes = total_activity
    result.total_rest_minutes = total_rest
    result.accrued_rest_minutes = accrued
    result.rest_balance_minutes = accrued - total_rest

    # Build combined entry list
    for row in sorted(activity_rows, key=lambda r: r.sequence):
        mins = _duration_minutes(row.start_hhmm, row.end_hhmm)
        result.entries.append({
            "type": "activity",
            "sequence": row.sequence,
            "start_hhmm": row.start_hhmm,
            "end_hhmm": row.end_hhmm,
            "duration_minutes": mins,
            "notes": row.notes,
        })

    for row in sorted(rest_rows, key=lambda r: r.sequence):
        mins = _duration_minutes(row.start_hhmm, row.end_hhmm)
        result.entries.append({
            "type": "rest",
            "sequence": row.sequence,
            "start_hhmm": row.start_hhmm,
            "end_hhmm": row.end_hhmm,
            "duration_minutes": mins,
            "notes": row.notes,
        })

    # Violations
    if result.rest_balance_minutes < 0:
        result.violations.append(
            f"Rest deficit: used {total_rest} min but only accrued {accrued} min."
        )

    return result


@dataclass
class AttemptHealthInput:
    witness_count: int
    witness_completed_count: int
    evidence_count: int
    evidence_indexed_count: int
    statement_count: int
    logbook_violations: List[str]


def compute_submission_health(data: AttemptHealthInput) -> dict:
    """
    Server-side port of computeSubmissionHealth from src/lib/gwr.ts.
    Returns a score 0-100 and per-category flags.
    """
    issues = []
    score = 100

    witnesses_ok = data.witness_count >= 2 and data.witness_completed_count == data.witness_count
    if data.witness_count < 2:
        issues.append("At least 2 witnesses required.")
        score -= 25
    elif data.witness_completed_count < data.witness_count:
        pending = data.witness_count - data.witness_completed_count
        issues.append(f"{pending} witness(es) have not submitted their statement.")
        score -= 15

    evidence_ok = data.evidence_indexed_count >= 3
    if data.evidence_count == 0:
        issues.append("No evidence uploaded.")
        score -= 30
    elif data.evidence_indexed_count < 3:
        issues.append("At least 3 indexed evidence items are recommended.")
        score -= 10

    logbook_ok = len(data.logbook_violations) == 0
    for v in data.logbook_violations:
        issues.append(v)
        score -= 10

    statements_ok = data.statement_count > 0
    if data.statement_count == 0:
        issues.append("No statements submitted.")
        score -= 20

    return {
        "score": max(0, score),
        "witnesses_ok": witnesses_ok,
        "evidence_ok": evidence_ok,
        "logbook_ok": logbook_ok,
        "statements_ok": statements_ok,
        "issues": issues,
    }
