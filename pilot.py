"""Pinned public-project audit and one bounded A/B case preparation; no model execution."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

import auditor
import compass
import generator

ROOT = Path(__file__).resolve().parent
HEX = re.compile(r"[a-f0-9]{40}\Z")
REPO = re.compile(r"yohi/[a-z0-9-]+\Z")
MAX_BYTES = auditor.MAX_INPUT_BYTES


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def blob_sha(raw):
    return hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("pilot redirects are not allowed")


def fetch_pinned(project, path, expected_blob):
    require(REPO.fullmatch(project["repo"]) and HEX.fullmatch(project["commit"])
            and HEX.fullmatch(expected_blob), "invalid pinned source")
    require(path in {"AGENTS.md", "tests/core/evidence-provenance.test.ts"}, "unapproved pilot path")
    url = f"https://raw.githubusercontent.com/{project['repo']}/{project['commit']}/{path}"
    with build_opener(NoRedirect()).open(Request(url, headers={"User-Agent": "AgentCompass-pilot"}),
                                         timeout=20) as response:
        require(urlsplit(response.geturl()).hostname == "raw.githubusercontent.com", "unexpected host")
        raw = response.read(MAX_BYTES + 1)
    require(len(raw) <= MAX_BYTES and blob_sha(raw) == expected_blob, "pinned blob mismatch")
    raw.decode("utf-8")
    return raw


def load_manifest():
    data = compass.read_json(ROOT / "registry/pilot.json")
    require(data["schema_version"] == 1, "invalid pilot schema")
    ids = set()
    for p in data["projects"]:
        require(p["id"] not in ids and REPO.fullmatch(p["repo"])
                and HEX.fullmatch(p["commit"]) and HEX.fullmatch(p["blob"]), "invalid project")
        ids.add(p["id"])
    require(data["case"]["project"] in ids, "invalid case project")
    return data


def evaluate(project, raw, registry):
    sources, targets, practices, generation, rules = registry
    require(blob_sha(raw) == project["blob"], "pinned blob mismatch")
    text = raw.decode("utf-8-sig")
    profile = project["profile"]
    report = auditor.audit(text, hashlib.sha256(raw).hexdigest(), len(raw), sources, targets,
                           practices, generation, rules, **profile)
    draft = generator.generate(sources, targets, practices, generation, **profile, language="en")
    draft_text = draft["AGENTS.draft.md"]
    # Compare properties, not a quality score. Generic draft lacks project constraints.
    return {"project": project["id"], "commit": project["commit"], "blob": project["blob"],
            "profile": profile, "input": report["input"],
            "registry_sha256": report["registry_sha256"],
            "verdict": report["verdict"], "findings": report["findings"],
            "omitted_findings": report["omitted_findings"],
            "literal_coverage": report["literal_coverage"],
            "generic_draft": {"lines": len(draft_text.splitlines()), "bytes": len(draft_text.encode()),
                              "sha256": hashlib.sha256(draft_text.encode()).hexdigest(),
                              "replacement_allowed": False},
            "model_effectiveness": "NOT_RUN"}


def variant(raw, case):
    text = raw.decode("utf-8")
    old, new = case["replace_before"], case["replace_after"]
    require(text.count(old) == 1 and new != old, "case replacement anchor not unique")
    return text.replace(old, new, 1).encode("utf-8")


def registry():
    s, t, p = compass.load_registry()
    return s, t, p, generator.load_generation(t, p), auditor.load_rules(p)


def prepare(directory, project, case, raw, evidence_raw):
    require(blob_sha(raw) == project["blob"] and blob_sha(evidence_raw) == case["evidence"]["blob"],
            "case input identity mismatch")
    candidate = variant(raw, case)
    # This is an experimental variant in a new folder, not installed in the target repository.
    dest = Path(directory)
    dest.mkdir(exist_ok=False)
    manifest = {"case": case["id"], "project": project, "task": case["prompt"],
                "rubric": case["rubric"], "evidence": case["evidence"], "metrics": case["metrics"],
                "baseline_sha256": hashlib.sha256(raw).hexdigest(),
                "candidate_sha256": hashlib.sha256(candidate).hexdigest(),
                "execution_status": "NOT_RUN",
                "adoption_status": "EXPERIMENT_ONLY"}
    files = {"baseline.AGENTS.md": raw, "candidate.AGENTS.md": candidate,
             "TASK.md": (case["prompt"] + "\n").encode(),
             "manifest.json": (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()}
    for name, content in files.items():
        with (dest / name).open("xb") as stream:
            stream.write(content)
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-dir", type=Path, help="new directory for the single experimental A/B case")
    args = parser.parse_args(argv)
    data = load_manifest()
    reg = registry()
    reports = []
    for p in data["projects"]:
        raw = fetch_pinned(p, "AGENTS.md", p["blob"])
        reports.append(evaluate(p, raw, reg))
        if p["id"] == data["case"]["project"]:
            case_project, case_raw = p, raw
    case = data["case"]
    evidence = case["evidence"]
    evidence_raw = fetch_pinned(case_project, evidence["path"], evidence["blob"])
    candidate = variant(case_raw, case)
    print(json.dumps({"reports": reports,
                      "case": {"id": case["id"], "baseline_sha256": hashlib.sha256(case_raw).hexdigest(),
                               "candidate_sha256": hashlib.sha256(candidate).hexdigest(),
                               "evidence_blob": blob_sha(evidence_raw),
                               "execution_status": "NOT_RUN"}}, ensure_ascii=False, indent=2))
    if args.prepare_dir:
        prepare(args.prepare_dir, case_project, case, case_raw, evidence_raw)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Pilot failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(2)
