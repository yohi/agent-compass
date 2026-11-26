"""Bounded official-index discovery. Candidates are untrusted and never fetched or adopted."""
import argparse
import hashlib
from html.parser import HTMLParser
import json
import re
import sys
from urllib.parse import urljoin, urlsplit, urlunsplit

import compass

TITLE = "Agent Compass — discovery state"
MARKER = "<!-- agent-compass-discovery-v1\n"
MAX_SEEN = 1500  # global; 96-bit candidate identities, no document bodies
MAX_REPORT = 12   # summary only; complete candidates archived separately
ARCHIVE_VERSION = 1
COMMENT_LIMIT = 18000
SAFE_PATH = re.compile(r"/[A-Za-z0-9._~/-]{0,240}\Z", re.ASCII)
HINT = re.compile(
    r"model|prompt|agent|skill|instruct|reason|think|tool|migration|changelog|release|"
    r"context|memory|guide|kimi|glm|qwen|deepseek|gemini|claude|gpt", re.I
)
TOKEN = re.compile(r"(?<![A-Za-z0-9_-])[A-Za-z][A-Za-z0-9]*(?:[-.][A-Za-z0-9]+)+(?![A-Za-z0-9_-])")
KEY = re.compile(r"[0-9a-f]{24}\Z")


def load_indexes(targets):
    rows = compass.index(compass.read_json(compass.ROOT / "registry/discovery.json"))
    for key, row in rows.items():
        compass.require(compass.ID.fullmatch(key) and row["target"] in targets, "invalid discovery target")
        host = urlsplit(row["url"]).hostname
        compass.require(host and "." in host and not host.replace(".", "").isdigit(), "invalid index host")
        compass.safe_url(row["url"], {host})
        compass.require(row["format"] in {"html", "text"} and row["publisher"], "invalid index metadata")
        compass.require(isinstance(row["prefixes"], list) and row["prefixes"]
                        and all(SAFE_PATH.fullmatch(p) for p in row["prefixes"]), "invalid path prefixes")
        compass.require(isinstance(row["model_prefixes"], list)
                        and all(re.fullmatch(r"[a-z0-9-]+", p) for p in row["model_prefixes"]),
                        "invalid model prefixes")
    return rows


class Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.extend(v for k, v in attrs if k == "href" and v)


def candidate_url(href, base, index):
    # Never retain queries, fragments, credentials, percent encoding or arbitrary hosts.
    try:
        parsed = urlsplit(urljoin(base, href))
        host = urlsplit(index["url"]).hostname
        compass.safe_url(parsed.geturl(), {host})
        path = parsed.path.rstrip("/") or "/"
        if not SAFE_PATH.fullmatch(path) or any(p in {".", ".."} for p in path.split("/")):
            return None
        if not any(path == p.rstrip("/") or path.startswith(p.rstrip("/") + "/")
                   for p in index["prefixes"]):
            return None
        # GitHub organization indexes: repository roots only, not issues/forks/etc.
        if host == "github.com" and len(path.strip("/").split("/")) != 2:
            return None
        if not HINT.search(path):
            return None
        return urlunsplit(("https", host, path, "", ""))
    except (ValueError, TypeError):
        return None


def identity(kind, value):
    return hashlib.sha256((kind + "\0" + value).encode()).hexdigest()[:24]


class DiscoveryText(compass.TextExtractor):
    """Preserve link boundaries without changing Phase 1 page fingerprints."""

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.append(" ")
        super().handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        super().handle_endtag(tag)
        if tag == "a":
            self.append(" ")


def extract(raw, fmt, base, index, known_urls):
    if fmt == "html":
        visible = DiscoveryText()
        visible.feed(raw)
        content = compass.normalize("".join(visible.main or visible.body), "text")
        parser = Links()
        parser.feed(raw)
        hrefs = parser.links
    else:
        content = compass.normalize(raw, fmt)
        hrefs = re.findall(r"\]\(([^)\s]+)\)", raw)
        hrefs += re.findall(r"https://[A-Za-z0-9.-]+/[A-Za-z0-9._~/-]+", raw)
    candidates = {}
    for href in hrefs:
        url = candidate_url(href, base, index)
        if url and url not in known_urls:
            candidates[identity("link", url)] = ("link", url)
    for match in TOKEN.finditer(content):
        token = match.group().lower()
        if len(token) <= 80 and any(token.startswith(p) for p in index["model_prefixes"]):
            # Require a digit to exclude generic documentation labels.
            if re.search(r"\d", token):
                candidates[identity("model-mention", token)] = ("model-mention", token)
    return candidates


def validate_state(state):
    compass.require(isinstance(state, dict), "invalid discovery state")
    total = 0
    for key, row in state.items():
        compass.require(compass.ID.fullmatch(key) and row["status"] in {"ok", "error"}
                        and isinstance(row["url"], str) and isinstance(row["seen"], list),
                        "invalid discovery record")
        seen = row["seen"]
        compass.require(row.get("archive_version") in (None, ARCHIVE_VERSION), "invalid archive version")
        compass.require(all(isinstance(s, str) and KEY.fullmatch(s) for s in seen)
                        and len(seen) == len(set(seen)), "invalid discovery identities")
        total += len(seen)
    compass.require(total <= MAX_SEEN, "discovery state capacity exceeded")
    return state


def scan(indexes, previous, known_urls, fetcher=compass.fetch_document):
    validate_state(previous)
    state, events = {}, []
    for key, index in indexes.items():
        old = previous.get(key, {})
        old = old if old.get("url") == index["url"] else {}
        seen = set(old.get("seen", []))
        try:
            host = urlsplit(index["url"]).hostname
            raw, fmt, base = fetcher(index, {host})
            candidates = extract(raw, fmt, base, index, known_urls)
            legacy = bool(old) and old.get("archive_version") != ARCHIVE_VERSION
            # Re-observe current legacy candidates once. Identities no longer present cannot
            # be reconstructed from hashes; count them explicitly rather than claiming recovery.
            selected = candidates if legacy else {k: v for k, v in candidates.items() if k not in seen}
            new = sorted(selected.values(), key=lambda pair: (pair[0] != "model-mention", pair[1]))
            record = {"url": index["url"], "status": "ok", "seen": sorted(seen | candidates.keys()),
                      "archive_version": ARCHIVE_VERSION}
            if new or not old or legacy or old.get("status") == "error":
                event_type = "archive_migration" if legacy else (
                    "discovered" if old.get("seen") else "initial_inventory")
                events.append({"id": key, "event": event_type, "count": len(new),
                               "candidates": new,
                               "legacy_unrecovered": len(seen - candidates.keys()) if legacy else 0})
        except (OSError, ValueError, UnicodeError, TimeoutError) as exc:
            record = {"url": index["url"], "status": "error", "seen": sorted(seen),
                      "error": type(exc).__name__, "reason": compass.error_reason(exc)}
            if old.get("archive_version") == ARCHIVE_VERSION:
                record["archive_version"] = ARCHIVE_VERSION
            if (old.get("status") != "error" or old.get("error") != record["error"]
                    or old.get("reason") != record["reason"]):
                events.append({"id": key, "event": "fetch_error", "error": record["error"],
                               "reason": record["reason"]})
        state[key] = record
    for key in sorted(previous.keys() - indexes.keys()):
        events.append({"id": key, "event": "removed"})
    validate_state(state)  # fail closed before overwriting any durable state
    return state, events


def report(indexes, state, events):
    lines = ["## Official index discovery / 公式情報源の発見", "",
             "Candidates are observed links or model mentions, not verified new releases or recommendations.",
             "初回は既存資料も含む。新モデル確定・自動採択は行わない。", "",
             f"Successful indexes: {sum(r['status']=='ok' for r in state.values())}/{len(state)}.", ""]
    for event in events:
        key = event["id"]
        if key not in indexes:
            lines.append(f"- {key}: removed")
            continue
        idx = indexes[key]
        lines.append(f"- [{key}]({idx['url']}) ({idx['target']}): {event['event']}")
        if "error" in event:
            lines.append("  - " + event["error"] + ": " + event.get("reason", "unknown"))
        if "candidates" in event:
            lines.append(f"  - {event['count']} candidates to archive; review scope and official evidence.")
            if event.get("legacy_unrecovered"):
                lines.append(f"  - {event['legacy_unrecovered']} legacy identities not currently rediscovered "
                             "(possibly filtered or removed); original values unknown.")
            for kind, value in event["candidates"][:MAX_REPORT]:
                if kind == "link":
                    lines.append(f"  - [{value}]({value}) — source candidate")
                else:
                    lines.append(f"  - \x60{value}\x60 — model mention; verify exact identity and release status")
            if event["count"] > MAX_REPORT:
                lines.append(f"  - {event['count']-MAX_REPORT} more in complete candidate archive "
                             "(issue comments or local archive).")
    if not events:
        lines.append("No new candidate identities or status transitions.")
    lines += ["", "Outstanding failures: " +
              (", ".join(k for k, v in state.items() if v["status"] == "error") or "none"),
              "Adoption: verify the official source, then add/update a scoped registry record if warranted."]
    return "\n".join(lines) + "\n"


def archive_comments(indexes, events):
    """Complete, bounded candidate batches; each record carries its index and identity."""
    comments = []
    for event in events:
        if not event.get("candidates"):
            continue
        key = event["id"]
        header = f"## Complete candidate archive — {key}\n\nSource: {indexes[key]['url']}\n\n"
        header += "Unverified candidates, not recommendations or release announcements.\n\n"
        lines = []
        for kind, value in event["candidates"]:
            ident = identity(kind, value)
            line = f"- `{ident}` | {kind} | {value}\n"
            compass.require(len(header) + len(line) <= COMMENT_LIMIT, "candidate too large")
            if len(header) + sum(map(len, lines)) + len(line) > COMMENT_LIMIT:
                comments.append(header + "".join(lines))
                lines = []
            lines.append(line)
        if lines:
            comments.append(header + "".join(lines))
    return comments


def read_state(body):
    compass.require(isinstance(body, str) and body.count(MARKER) == 1, "missing discovery state")
    parts = body.split(MARKER, 1)[1].split("\n-->", 1)
    compass.require(len(parts) == 2, "incomplete discovery state")
    return validate_state(json.loads(parts[0]))


def github(repo, indexes, known_urls):
    compass.require(re.fullmatch(r"[\w.-]+/[\w.-]+", repo, re.ASCII), "invalid repository")
    endpoint = f"repos/{repo}/issues"
    pages = compass.gh("--paginate", "--slurp", endpoint + "?state=all&per_page=100")
    issues = [i for page in pages for i in page if "pull_request" not in i
              and i["title"] == TITLE and i["user"]["login"] == "github-actions[bot]"]
    compass.require(len(issues) <= 1, "multiple discovery state issues")
    issue = issues[0] if issues else None
    previous = read_state(issue["body"]) if issue else {}
    state, events = scan(indexes, previous, known_urls)
    message = report(indexes, state, events)
    print(message)
    if issue is None or state != previous:
        body = message + "\n" + MARKER + json.dumps(state, separators=(",", ":")) + "\n-->\n"
        compass.require(len(body) < 60000, "discovery state exceeds safe issue size")
        comments = archive_comments(indexes, events)
        if issue is None:
            # Bootstrap with empty state: an interrupted archive never marks candidates seen.
            issue = compass.gh("--method", "POST", endpoint, payload={
                "title": TITLE, "body": "Archive initialization pending.\n\n" + MARKER + "{}\n-->\n"})
        number = issue["number"]
        for comment in comments:
            compass.gh("--method", "POST", f"{endpoint}/{number}/comments", payload={"body": comment})
        compass.gh("--method", "POST", f"{endpoint}/{number}/comments", payload={"body": message})
        compass.gh("--method", "PATCH", f"{endpoint}/{number}", payload={"body": body})
    return int(any(r["status"] == "error" for r in state.values()))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", help="publish to bot-owned discovery issue")
    parser.add_argument("--state", help="local state file")
    args = parser.parse_args(argv)
    compass.require(bool(args.repo) != bool(args.state), "choose exactly one of --repo or --state")
    sources, targets, _ = compass.load_registry()
    indexes = load_indexes(targets)
    known = {s["url"].rstrip("/") for s in sources.values()}
    known.update(i["url"].rstrip("/") for i in indexes.values())
    if args.repo:
        return github(args.repo, indexes, known)
    from pathlib import Path
    path = Path(args.state)
    previous = compass.read_json(path) if path.exists() else {}
    state, events = scan(indexes, previous, known)
    print(report(indexes, state, events))
    # Append-only local archive, persisted before advancing deduplication state.
    archive = path.with_name(path.name + ".candidates.jsonl")
    with archive.open("a", encoding="utf-8") as stream:
        for event in events:
            for kind, value in event.get("candidates", []):
                stream.write(json.dumps({"index": event["id"], "id": identity(kind, value),
                                         "kind": kind, "value": value}, ensure_ascii=False) + "\n")
    compass.write_json(path, state)
    return int(any(r["status"] == "error" for r in state.values()))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, TypeError, compass.subprocess.SubprocessError) as exc:
        print("Discovery failed: " + type(exc).__name__ + ": " + str(exc), file=sys.stderr)
        sys.exit(2)
