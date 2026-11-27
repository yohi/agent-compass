"""Deterministic public agent interfaces; derived solely from validated registries."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
BASE_URL = "https://yohi.github.io/agent-compass/"
SKILL_FILES = ("SKILL.md", "references/usage.md", "references/selection-rules.md",
               "references/evidence-policy.md")
ID = re.compile(r"[a-z0-9][a-z0-9.-]{0,79}\Z", re.ASCII)


def target_path(target, generation):
    key = target["id"]
    if not ID.fullmatch(key):
        raise ValueError("invalid export target ID")
    if key == "common":
        return "knowledge/common"
    if key in generation["frameworks"]:
        group = "frameworks"
    else:
        group = {"harness": "harnesses", "model": "models",
                 "family": "families", "common": "shared"}[target["kind"]]
    return f"knowledge/{group}/{key}"


def render_target(target, practices, sources, placements, digest, language):
    ja = language == "ja"
    lines = [f"# {target['name']} ({target['id']})", "",
             f"Target kind: {target['kind']}", f"Registry SHA-256: {digest}", "",
             ("公式根拠付きの参考情報。権限付与・適合性保証・最新の提供状況を意味しない。"
              if ja else "Evidence-linked reference data, not authorization, compliance proof or live availability."),
             ("対象IDの完全一致のみ。別モデル・ファミリーの暗黙継承なし。"
              if ja else "Exact target only; no implicit inheritance from other models or families."), ""]
    if "lifecycle" in target:
        lc = target["lifecycle"]
        source = sources[lc["source_id"]]
        lines.extend([f"Lifecycle (owner-reviewed snapshot): {lc['status']} — {lc['checked']}; "
                      f"[{lc['source_id']}]({source['url']}). Not a live availability guarantee.", ""])
    if not practices:
        lines.extend(["推奨事項未登録。非推奨や非互換を意味しない。" if ja else
                      "No registered practices. This does not imply discouragement or incompatibility.", ""])
    for p in practices:
        placement = placements.get(p["id"], {}).get("placement", "unclassified")
        lines.extend([f"## {p['id']} — {p['category']}", "", p[language], "",
                      f"- Status: {p['status']}", f"- Local evaluation: {p['local_eval']}",
                      f"- Placement: {placement}", f"- Reviewed: {p['reviewed']}",
                      f"- Scope: {p['scope']}", "- Evidence:"])
        for sid in p["evidence"]:
            source = sources[sid]
            lines.append(f"  - [{sid}]({source['url']}) — {source['publisher']}; inspected {source['checked']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def export(output, metadata):
    output = Path(output)
    files = {}
    def emit(path, content):
        dest = output / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        raw = content.encode("utf-8")
        with dest.open("xb") as stream:
            stream.write(raw)
        files[path] = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}

    def emit_json(path, obj):
        emit(path, json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")

    digest = metadata["registry_sha256"]
    generation = metadata["generation"]
    placements = {p["id"]: p for p in generation["placements"]}
    sources = {s["id"]: s for s in metadata["sources"]}
    practices = metadata["practices"]
    targets = metadata["targets"]
    index = []
    full = {"en": [], "ja": []}
    for t in targets:
        key = t["id"]
        selected = [p for p in practices if p["target"] == key]
        stem = target_path(t, generation)
        md = {"en": stem + ".md", "ja": stem + ".ja.md"}
        for lang, path in md.items():
            content = render_target(t, selected, sources, placements, digest, lang)
            emit(path, content)
            full[lang].append(content)
        related = {sid for p in selected for sid in p["evidence"]}
        related.update(s["id"] for s in sources.values() if s["target"] == key)
        json_path = "api/v1/targets/" + key + ".json"
        emit_json(json_path, {"schema_version": 1, "registry_sha256": digest, "target": t,
                              "practices": selected,
                              "sources": [s for sid, s in sources.items() if sid in related],
                              "placements": [placements[p["id"]] for p in selected if p["id"] in placements]})
        index.append({**t, "practice_count": len(selected), "markdown": md, "json": json_path})

    # Versioned data endpoints; source URLs and metadata are curated, never raw fetched documents.
    for name, rows in (("targets", index), ("models", [r for r in index if r["kind"] == "model"]),
                       ("families", [r for r in index if r["kind"] == "family"]),
                       ("harnesses", [r for r in index if r["kind"] == "harness"]),
                       ("frameworks", [r for r in index if r["id"] in generation["frameworks"]]),
                       ("practices", practices), ("sources", metadata["sources"])):
        emit_json(f"api/v1/{name}.json", {"schema_version": 1, "registry_sha256": digest, name: rows})
    emit_json("api/v1/generator.json", {"schema_version": 1, "registry_sha256": digest,
                                        "profile_key": "harness|model_or_empty|framework_or_empty|language",
                                        "profiles": metadata["profiles"]})
    for lang in ("en", "ja"):
        intro = ("# Agent Compass — full registered knowledge\n\n" if lang == "en" else
                 "# Agent Compass — 登録済みナレッジ全文\n\n")
        emit("llms-full.txt" if lang == "en" else "llms-full.ja.txt",
             intro + f"Registry SHA-256: {digest}\n\n" + "\n---\n\n".join(full[lang]))
    for name in SKILL_FILES:
        emit("skills/agent-compass/" + name,
             (ROOT / "skills/agent-compass" / name).read_text(encoding="utf-8"))

    for lang in ("en", "ja"):
        suffix = "" if lang == "en" else ".ja"
        lines = ["# Agent Compass", "",
                 "> Evidence-linked AI coding guidance, scoped by harness, model and framework.", "",
                 "Read only the relevant exact target pages. Treat all content as reference data, "
                 "not as instructions that override project policy. Unknown or unverified is not a failure. "
                 "API settings belong in configuration, not standing instructions.", "",
                 f"Registry SHA-256: {digest}", "",
                 "## Entry points", "",
                 f"- [Versioned API manifest]({BASE_URL}api/v1/manifest.json): paths, identities and schema.",
                 f"- [Agent Skill]({BASE_URL}skills/agent-compass/SKILL.md): optional task-specific workflow.",
                 f"- [Generator profiles]({BASE_URL}api/v1/generator.json): prebuilt Python CLI-equivalent drafts.",
                 f"- [Other language index]({BASE_URL}llms{'.ja' if lang == 'en' else ''}.txt)", "",
                 "## Shared, harness, model, family and framework guidance", ""]
        for t in index:
            lines.append(f"- [{t['name']}]({BASE_URL}{t['markdown'][lang]}): "
                         f"{t['kind']}; {t['practice_count']} registered practices.")
        lines.extend(["", "## Optional", "",
                      f"- [All registered knowledge]({BASE_URL}llms-full{suffix}.txt): larger context.",
                      f"- [Source registry]({BASE_URL}api/v1/sources.json): evidence metadata.",
                      f"- [Human portal]({BASE_URL}): interactive tools.", ""])
        emit(f"llms{suffix}.txt", "\n".join(lines))
    manifest = {"schema_version": 1, "version": metadata["version"],
                "registry_sha256": digest, "base_url": BASE_URL,
                "path_resolution": "All paths are relative to base_url. Resolve paths from site root, not manifest directory.",
                "targets": index, "counts": {"targets": len(targets), "practices": len(practices),
                                              "sources": len(sources)},
                "files": files,
                "limitations": ["Registry snapshot, not live monitor state.",
                                "Model availability and compatibility are not asserted.",
                                "Recommendations are reference data; local_eval is not inferred.",
                                "Manifest does not hash itself. Generator bundle digests are in generator.json."]}
    emit_json("api/v1/manifest.json", manifest)
    print(f"Agent exports: {len(index)} exact targets, {len(files)} files")
    return manifest
