"""Deterministic relevance hints, not semantic proof or model-generated guidance."""
import hashlib
import re

PATTERNS = {
    "instructions": r"\bagents\.md\b|\bclaude\.md\b|\bgemini\.md\b|\bcustom instructions?\b|\bsystem prompts?\b",
    "prompting": r"\bprompt(?:ing|s)?\b|\binstructions?\b|\bfew.shot\b",
    "context": r"\bcontext\b|\bcompaction\b|\bmemory\b|\btoken budget\b",
    "skills-tools": r"\bskills?\b|\btool(?:s| calls?| calling)?\b|\bmcp\b|\bhooks?\b",
    "verification": r"\btests?\b|\bverification\b|\bevals?\b|\breview\b|\bvalidation\b",
    "reasoning": r"\breasoning\b|\bthinking\b|\beffort\b|\btemperature\b",
    "security": r"\bpermissions?\b|\bsandbox\b|\bsecurity\b|\bapproval\b|\bcredentials?\b",
    "migration": r"\bdeprecat\w*\b|\bmigrat\w*\b|\bremov\w*\b|\bretir\w*\b|\bno longer\b|\breplac\w*\b",
}
COMPILED = {k: re.compile(v, re.I) for k, v in PATTERNS.items()}
HEX = re.compile(r"[0-9a-f]{32}\Z")


def topic_signals(content):
    """Hash matching lines as a multiset; retain no excerpts. Order-only changes are ignored."""
    result = {}
    lines = content.splitlines()
    for name, pattern in COMPILED.items():
        matched = sorted(line for line in lines if pattern.search(line))
        if matched:
            value = hashlib.sha256("\n".join(matched).encode("utf-8")).hexdigest()[:32]
            result[name] = [len(matched), value]
    return result


def validate_signals(value):
    return isinstance(value, dict) and all(
        k in PATTERNS and isinstance(v, list) and len(v) == 2
        and type(v[0]) is int and v[0] > 0 and isinstance(v[1], str) and HEX.fullmatch(v[1])
        for k, v in value.items()
    )


def signal_changes(before, after):
    if before is None or after is None:
        return None  # Phase 1 baseline: do not manufacture topic-level history.
    return [
        {"topic": key, "before": before.get(key, [0])[0], "after": after.get(key, [0])[0]}
        for key in PATTERNS if before.get(key) != after.get(key)
    ]


def proposal_lines(event, practices, source):
    """Propose bounded review actions; never infer a recommendation from a keyword."""
    topics = event.get("topic_changes")
    impacted = sorted(p["id"] for p in practices.values() if event["id"] in p["evidence"])
    lines = ["  - Candidate only / 未採択. Scope: " + source.get("target", "unknown") + "."]
    if topics is None:
        lines.append("  - Topic baseline unavailable; inspect the official source (classification unknown).")
    elif topics:
        labels = ", ".join(f"{t['topic']} ({t['before']}→{t['after']})" for t in topics)
        lines.append("  - Relevance hints / 関連候補: " + labels + ". Counts are matching lines, not rules.")
        if any(t["topic"] == "migration" for t in topics):
            lines.append("  - Check migration, removal or supersession; no deprecation has been established.")
    else:
        lines.append("  - No changed tracked topic; relevance remains unknown, not proven irrelevant.")
    if impacted:
        lines.append("  - Review linked practices: " + ", ".join(impacted) + ".")
        lines.append("  - Decision options: keep, amend, narrow scope, deprecate or supersede after evidence review.")
    else:
        lines.append("  - Check whether new scoped guidance merits a registry candidate; no linked practice yet.")
    lines.append("  - Evidence fingerprints: " + event["before"] + " → " + event["after"] + ".")
    return lines
