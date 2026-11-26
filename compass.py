"""Agent Compass. External text is data, never executable instructions."""
import argparse
from collections import Counter
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from signals import topic_signals, signal_changes, proposal_lines

ROOT = Path(__file__).resolve().parent
MAX_BYTES = 4 * 1024 * 1024
STATUSES = {"candidate", "recommended", "conditional", "discouraged", "deprecated",
            "superseded", "unverified"}
ISSUE_TITLE = "Agent Compass — source monitor state"
MARKER = "<!-- agent-compass-state-v1\n"
ID = re.compile(r"[a-z0-9][a-z0-9.-]{0,79}\Z", re.ASCII)
HASH = re.compile(r"[0-9a-f]{64}\Z")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def index(rows):
    require(isinstance(rows, list), "registry must be a list")
    out = {}
    for row in rows:
        key = row["id"]
        require(isinstance(key, str) and key not in out, "invalid or duplicate id")
        out[key] = row
    return out


def safe_url(url, hosts):
    parsed = urlsplit(url)
    require(parsed.scheme == "https" and parsed.hostname in hosts and
            parsed.username is None and parsed.password is None and
            parsed.port in (None, 443), "unapproved HTTPS endpoint")
    return url


def load_registry():
    sources, targets, practices = (
        index(read_json(ROOT / "registry" / (name + ".json")))
        for name in ("sources", "targets", "practices")
    )
    for key, target in targets.items():
        require(ID.fullmatch(key) and target["kind"] in {"common", "harness", "family", "model"},
                "invalid target")
        require(bool(target["name"]), "missing target name")
    for key, source in sources.items():
        require(ID.fullmatch(key) and source["target"] in targets, "invalid source target")
        require(source["format"] in {"html", "text"}, "invalid source format")
        host = urlsplit(source["url"]).hostname
        require(host and "." in host and not host.replace(".", "").isdigit(), "invalid source host")
        safe_url(source["url"], {host})
        require(all(source[k] for k in ("publisher", "kind", "checked")), "missing source metadata")
    for key, practice in practices.items():
        require(re.fullmatch(r"BP-[0-9]+", key) and practice["target"] in targets,
                "invalid practice target")
        require(practice["status"] in STATUSES and practice["local_eval"] in
                {"not_verified", "supported", "mixed", "contradicted"}, "invalid practice status")
        require(isinstance(practice["evidence"], list) and practice["evidence"] and
                all(s in sources for s in practice["evidence"]), "invalid evidence reference")
        require(all(practice[k] for k in ("en", "ja", "scope", "category", "reviewed")),
                "missing practice metadata")
    return sources, targets, practices


class TextExtractor(HTMLParser):
    SKIP = {"script", "style", "nav", "footer", "header", "aside", "noscript", "svg", "template"}
    BLOCK = {"p", "div", "li", "pre", "h1", "h2", "h3", "h4", "h5", "tr", "br", "section"}
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
            "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.body = []
        self.main = []

    def append(self, value):
        if not any(tag in self.SKIP for tag in self.stack):
            if "body" in self.stack:
                self.body.append(value)
            if "main" in self.stack or "article" in self.stack:
                self.main.append(value)

    def handle_starttag(self, tag, attrs):
        if tag in self.BLOCK:
            self.append("\n")
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        if tag in self.BLOCK:
            self.append("\n")

    def handle_endtag(self, tag):
        if tag in self.stack:
            pos = len(self.stack) - 1 - self.stack[::-1].index(tag)
            del self.stack[pos:]
        if tag in self.BLOCK:
            self.append("\n")

    def handle_data(self, data):
        self.append(data)


def normalize(raw, fmt):
    if fmt == "html":
        parser = TextExtractor()
        parser.feed(raw)
        raw = "".join(parser.main or parser.body)
    lines = [" ".join(line.split()) for line in raw.splitlines()]
    content = "\n".join(line for line in lines if line)
    require(len(content) >= 100, "empty or unexpectedly short source")
    return content


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def fingerprint(content):
    lines = content.splitlines()
    # A bounded sequence of position-based chunks plus a tail aggregate.
    # This detects changes without persisting third-party source text.
    chunks = [digest("\n".join(lines[i:i+24])) for i in range(0, min(len(lines), 24*23), 24)]
    if len(lines) > 24*23:
        chunks.append(digest("\n".join(lines[24*23:])))
    return {"sha256": digest(content), "lines": len(lines), "chunks": chunks}


class RestrictedRedirect(HTTPRedirectHandler):
    def __init__(self, hosts):
        self.hosts = hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        safe_url(newurl, self.hosts)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def error_reason(exc):
    """Stable diagnostic codes; never publish arbitrary exception messages."""
    from urllib.error import HTTPError, URLError
    if isinstance(exc, HTTPError):
        return "http_" + str(exc.code) if 100 <= exc.code <= 599 else "http_error"
    if isinstance(exc, (TimeoutError,)) or (
            isinstance(exc, URLError) and isinstance(exc.reason, TimeoutError)):
        return "timeout"
    if isinstance(exc, UnicodeError):
        return "decode_error"
    if isinstance(exc, ValueError):
        return {
            "unapproved HTTPS endpoint": "endpoint_not_allowed",
            "unsupported content type": "unsupported_content_type",
            "source exceeds size limit": "size_limit",
            "expected text, got HTML": "unexpected_html",
            "empty or unexpectedly short source": "empty_or_short_content",
        }.get(str(exc), "invalid_response")
    return "network_or_io_error"


def fetch_document(source, hosts):
    url = safe_url(source["url"], hosts)
    request = Request(url, headers={"User-Agent": "AgentCompass/0.1 (public documentation monitor)",
                                    "Accept": "text/html,text/plain,text/markdown"})
    with build_opener(RestrictedRedirect(hosts)).open(request, timeout=20) as response:
        safe_url(response.geturl(), hosts)
        content_type = response.headers.get_content_type()
        require(content_type in {"text/html", "text/plain", "text/markdown", "application/markdown"},
                "unsupported content type")
        raw = response.read(MAX_BYTES + 1)
        require(len(raw) <= MAX_BYTES, "source exceeds size limit")
        require(source["format"] != "text" or content_type != "text/html",
                "expected text, got HTML")
        text = raw.decode(response.headers.get_content_charset() or "utf-8", errors="strict")
        fmt = "html" if content_type == "text/html" else "text"
        return text, fmt, response.geturl()


def fetch(source, hosts):
    text, fmt, _ = fetch_document(source, hosts)
    content = normalize(text, fmt)
    return {**fingerprint(content), "topics": topic_signals(content)}


def monitor(sources, previous, fetcher=fetch):
    require(isinstance(previous, dict), "invalid monitor state")
    hosts = {urlsplit(s["url"]).hostname for s in sources.values()}
    state, events = {}, []
    for key, source in sources.items():
        old = previous.get(key, {})
        baseline = old.get("fingerprint") if old.get("url") == source["url"] else None
        try:
            new = fetcher(source, hosts)
            record = {"url": source["url"], "status": "ok", "fingerprint": new}
            if baseline is None:
                events.append({"id": key, "event": "baseline"})
            elif baseline["sha256"] != new["sha256"]:
                changed = sum((Counter(new["chunks"]) - Counter(baseline["chunks"])).values())
                events.append({"id": key, "event": "changed", "before": baseline["sha256"],
                               "after": new["sha256"], "line_delta": new["lines"] - baseline["lines"],
                               "new_chunks": changed,
                               "topic_changes": signal_changes(baseline.get("topics"), new.get("topics"))})
            if old.get("status") == "error":
                events.append({"id": key, "event": "recovered"})
        except (OSError, ValueError, UnicodeError, TimeoutError) as exc:
            # Record only exception class, never remote body, URL params or credentials.
            record = {"url": source["url"], "status": "error", "error": type(exc).__name__,
                      "fingerprint": baseline, "reason": error_reason(exc)}
            if (old.get("status") != "error" or old.get("error") != record["error"]
                    or old.get("reason") != record["reason"]):
                events.append({"id": key, "event": "fetch_error", "error": record["error"],
                               "reason": record["reason"]})
        state[key] = record
    for key in previous.keys() - sources.keys():
        events.append({"id": key, "event": "removed"})
    return state, events


def render(sources, targets, practices):
    out = ["# Best practices / ベストプラクティス", "",
           "Generated from registry/*.json. Provider guidance is not local benchmark evidence.",
           "公式資料に基づく整理。ローカル実測による裏付けは未実施。", ""]
    for key, target in targets.items():
        out += [f"## {target['name']} ({target['kind']})", ""]
        selected = [p for p in practices.values() if p["target"] == key]
        if not selected:
            out += ["No verified recommendation yet; source discovery only. / 推奨事項は未登録。", ""]
        for p in selected:
            links = ", ".join(f"[{sid}]({sources[sid]['url']})" for sid in p["evidence"])
            out += [f"### {p['id']} — {p['status']}", "", p["en"], "", p["ja"], "",
                    "Scope: " + p["scope"], "", "Evidence: " + links, "",
                    "Local evaluation: " + p["local_eval"], ""]
        links = ", ".join(f"[{sid}]({s['url']})" for sid, s in sources.items() if s["target"] == key)
        out += ["Monitored sources: " + links, ""]
    return "\n".join(out) + "\n"


def gh(*args, payload=None):
    cmd = ["gh", "api", *args]
    if payload is not None:
        cmd += ["--input", "-"]
    proc = subprocess.run(cmd, input=None if payload is None else json.dumps(payload),
                          text=True, capture_output=True, check=True, timeout=60)
    return json.loads(proc.stdout) if proc.stdout.strip() else None


def issue_state(body):
    require(isinstance(body, str) and body.count(MARKER) == 1, "missing or ambiguous state")
    payload = body.split(MARKER, 1)[1].split("\n-->", 1)
    require(len(payload) == 2, "incomplete state")
    state = json.loads(payload[0])
    require(isinstance(state, dict), "invalid state")
    for key, record in state.items():
        require(ID.fullmatch(key) and record["status"] in {"ok", "error"}, "invalid state record")
        fp = record.get("fingerprint")
        if fp is not None:
            if "topics" in fp:
                from signals import validate_signals
                require(validate_signals(fp["topics"]), "invalid topic fingerprints")
            require(HASH.fullmatch(fp["sha256"]) and isinstance(fp["lines"], int)
                    and fp["lines"] > 0 and len(fp["chunks"]) <= 24
                    and all(HASH.fullmatch(h) for h in fp["chunks"]), "invalid fingerprint")
        else:
            require(record["status"] == "error", "missing baseline")
    return state


def summary(sources, state, events, practices=None):
    lines = ["## Source monitor", "", "Changes require human interpretation; no practices were adopted.",
             "", f"Successful: {sum(r['status']=='ok' for r in state.values())}/{len(state)}.", ""]
    if not events:
        lines.append("No new transitions (see outstanding failures below).")
    for event in events:
        key = event["id"]
        url = sources.get(key, {}).get("url")
        label = f"[{key}]({url})" if url else key
        line = f"- {label}: {event['event']}"
        if event["event"] == "changed":
            line += f" (line delta {event['line_delta']:+}, new chunks {event['new_chunks']})"
        if event["event"] == "fetch_error":
            line += " (" + event["error"] + ": " + event.get("reason", "unknown") + ")"
        lines.append(line)
        if event["event"] == "changed":
            lines.extend(proposal_lines(event, practices or {}, sources[key]))
    lines += ["", "Outstanding fetch failures: " +
              (", ".join(k for k, r in state.items() if r["status"] == "error") or "none")]
    return "\n".join(lines) + "\n"


def github_monitor(repo, sources, practices=None):
    require(re.fullmatch(r"[\w.-]+/[\w.-]+", repo, re.ASCII), "invalid repository")
    endpoint = f"repos/{repo}/issues"
    pages = gh("--paginate", "--slurp", endpoint + "?state=all&per_page=100")
    issues = [i for page in pages for i in page if "pull_request" not in i and
              i["title"] == ISSUE_TITLE and i["user"]["login"] == "github-actions[bot]"]
    require(len(issues) <= 1, "multiple monitor state issues")
    issue = issues[0] if issues else None
    previous = issue_state(issue["body"]) if issue else {}
    state, events = monitor(sources, previous)
    report = summary(sources, state, events, practices)
    print(report)
    # Do not write on an unchanged run. On failure, retain the previous valid fingerprint.
    if issue is None or state != previous:
        body = report + "\n" + MARKER + json.dumps(state, separators=(",", ":")) + "\n-->\n"
        require(len(body) < 60000, "state exceeds safe issue size")
        if issue is None:
            gh("--method", "POST", endpoint, payload={"title": ISSUE_TITLE, "body": body})
        else:
            number = issue["number"]
            gh("--method", "POST", f"{endpoint}/{number}/comments", payload={"body": report})
            gh("--method", "PATCH", f"{endpoint}/{number}", payload={"body": body})
    return 1 if any(r["status"] == "error" for r in state.values()) else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate")
    rend = sub.add_parser("render")
    rend.add_argument("--check", action="store_true")
    show = sub.add_parser("show")
    show.add_argument("--target", required=True)
    mon = sub.add_parser("monitor")
    mon.add_argument("--state", required=True, type=Path)
    mon.add_argument("--output", required=True, type=Path)
    gen = sub.add_parser("generate", help="generate an offline instruction draft")
    gen.add_argument("--harness", required=True)
    gen.add_argument("--model")
    gen.add_argument("--framework")
    gen.add_argument("--language", choices=("ja", "en"), default="ja")
    gen.add_argument("--output-dir", type=Path, help="new directory for draft, configuration and evidence")
    github = sub.add_parser("github-monitor")
    github.add_argument("--repo", required=True)
    args = parser.parse_args(argv)
    sources, targets, practices = load_registry()
    if args.cmd == "validate":
        from discovery import load_indexes
        indexes = load_indexes(targets)
        from generator import load_generation
        load_generation(targets, practices)
        print(f"{len(sources)} sources, {len(targets)} targets, {len(practices)} practices; "
              f"{len(indexes)} discovery indexes")
    elif args.cmd == "render":
        path = ROOT / "docs" / "BEST_PRACTICES.md"
        content = render(sources, targets, practices)
        if args.check:
            require(path.read_text(encoding="utf-8") == content, "generated documentation is stale")
        else:
            path.write_text(content, encoding="utf-8")
    elif args.cmd == "show":
        require(args.target in targets, "unknown target")
        selected = {k: p for k, p in practices.items() if p["target"] == args.target}
        print(render(sources, {args.target: targets[args.target]}, selected))
    elif args.cmd == "generate":
        from generator import generate, load_generation, write_bundle
        data = load_generation(targets, practices)
        documents = generate(sources, targets, practices, data, args.harness, args.model,
                             args.framework, args.language)
        if args.output_dir is None:
            print(documents["AGENTS.draft.md"], end="")
            print("Draft only; use --output-dir for separate configuration and evidence.", file=sys.stderr)
        else:
            write_bundle(args.output_dir, documents)
            print(f"Draft bundle created: {args.output_dir}")
    elif args.cmd == "monitor":
        require(args.state.resolve() != args.output.resolve(), "state/output must differ")
        previous = read_json(args.state) if args.state.exists() else {}
        state, events = monitor(sources, previous)
        write_json(args.output, {"events": events, "state": state})
        write_json(args.state, state)
        print(summary(sources, state, events, practices))
        return 1 if any(r["status"] == "error" for r in state.values()) else 0
    elif args.cmd == "github-monitor":
        return github_monitor(args.repo, sources, practices)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(f"Agent Compass failed: {type(error).__name__}: {error}", file=sys.stderr)
        sys.exit(2)
