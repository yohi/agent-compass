"""Verify published agent endpoints against the manifest; no write or API key."""
import argparse
import hashlib
import json
from urllib.request import Request, build_opener, HTTPRedirectHandler
from pathlib import Path
import sys

BASE = "https://yohi.github.io/agent-compass/"
MAX = 4 * 1024 * 1024


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("portal redirect refused")


def fetch(path):
    if path.startswith("/") or ".." in path.split("/") or ":" in path or "\\" in path:
        raise ValueError("invalid portal path")
    request = Request(BASE + path, headers={"Cache-Control": "no-cache", "User-Agent": "AgentCompass-health"})
    with build_opener(NoRedirect()).open(request, timeout=20) as response:
        raw = response.read(MAX + 1)
    if len(raw) > MAX:
        raise ValueError("portal body too large")
    return raw


def verify(get=fetch, expected=None):
    raw = get("api/v1/manifest.json")
    manifest = json.loads(raw)
    if manifest["schema_version"] != 1 or manifest["base_url"] != BASE:
        raise ValueError("manifest schema/base mismatch")
    if expected is not None and raw != expected:
        raise ValueError("published snapshot differs from expected build")
    files = manifest["files"]
    for path in ("llms.txt", "llms.ja.txt", "api/v1/targets.json",
                 "knowledge/common.md", "knowledge/harnesses/opencode.md",
                 "knowledge/models/kimi-k3.md", "skills/agent-compass/SKILL.md"):
        content = get(path)
        entry = files[path]
        if len(content) != entry["bytes"] or hashlib.sha256(content).hexdigest() != entry["sha256"]:
            raise ValueError("endpoint digest mismatch: " + path)
    html = get("")
    if b"Agent Compass" not in html or b"./app.js" not in html:
        raise ValueError("unexpected portal index")
    print("Published portal manifest and 7 agent endpoints verified: " + manifest["registry_sha256"])
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-manifest", type=Path)
    args = parser.parse_args()
    try:
        verify(expected=args.expected_manifest.read_bytes() if args.expected_manifest else None)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("Portal health failed: " + type(exc).__name__, file=sys.stderr)
        sys.exit(1)
