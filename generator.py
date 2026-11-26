"""Offline, evidence-linked instruction drafts; never install or overwrite instructions."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ACTIVE = {"recommended", "conditional"}
PLACEMENTS = {"instruction", "configuration", "author-guidance"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_generation(targets, practices):
    data = json.loads((ROOT / "registry/generation.json").read_text(encoding="utf-8"))
    require(data["schema_version"] == 1, "unsupported generation schema")
    for key, row in data["harnesses"].items():
        require(key in targets and targets[key]["kind"] == "harness", "invalid generator harness")
        require(all(isinstance(row[k], str) and row[k].strip() for k in ("native_file", "en", "ja")),
                "invalid harness metadata")
    frameworks = data["frameworks"]
    require(len(frameworks) == len(set(frameworks)), "duplicate framework")
    require(all(k in targets and targets[k]["kind"] == "common" and k != "common"
                for k in frameworks), "invalid framework")
    seen = set()
    for row in data["placements"]:
        key = row["id"]
        require(key in practices and key not in seen, "unknown or duplicate placement")
        seen.add(key)
        require(row["placement"] in PLACEMENTS, "invalid placement")
        if row["placement"] == "instruction":
            require(practices[key]["category"] not in {"reasoning", "tools", "integration", "migration"},
                    "API or migration guidance cannot be a standing instruction")
            require(all(isinstance(row["instruction"][lang], str)
                        and row["instruction"][lang].strip()
                        and "\n" not in row["instruction"][lang]
                        and "\r" not in row["instruction"][lang] for lang in ("en", "ja")),
                    "invalid instruction text")
        if row["placement"] == "configuration":
            require(row["configuration_kind"] in {"api-or-runtime", "permissions", "integration"},
                    "invalid configuration kind")
    return data


def select(targets, practices, data, harness, model, framework):
    require(harness in data["harnesses"], "unsupported harness")
    require(model is None or (model in targets and targets[model]["kind"] in {"model", "family"}),
            "unknown model or model family")
    require(framework is None or framework in data["frameworks"], "unsupported framework")
    layers = [("common", "common"), ("harness", harness)]
    if model:
        layers.append(("model", model))
    if framework:
        layers.append(("framework", framework))
    by_target = {target: layer for layer, target in layers}
    placements = {row["id"]: row for row in data["placements"]}
    selected = []
    for key, practice in practices.items():
        target = practice["target"]
        if target not in by_target:
            continue
        row = placements.get(key)
        layer = by_target[target]
        if practice["status"] not in ACTIVE or practice["local_eval"] in {"mixed", "contradicted"}:
            disposition = "excluded-status-or-evaluation"
        elif row is None:
            disposition = "unclassified"
        elif row["placement"] == "instruction" and practice["status"] == "conditional" and layer != "framework":
            disposition = "author-guidance"
        else:
            disposition = row["placement"]
        selected.append((layer, practice, row, disposition))
    return layers, selected


def bilingual(language, en, ja):
    return ja if language == "ja" else en


def registry_digest(sources, targets, practices, data):
    blob = json.dumps([sources, targets, practices, data], sort_keys=True,
                      ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def generate(sources, targets, practices, data, harness, model=None, framework=None, language="ja"):
    require(language in {"ja", "en"}, "unsupported language")
    layers, selected = select(targets, practices, data, harness, model, framework)
    tr = lambda en, ja: bilingual(language, en, ja)
    heading = {"common": tr("Shared guidance", "共通指示"),
               "harness": tr("Harness-specific", "実行基盤固有"),
               "model": tr("Model-specific", "モデル固有"),
               "framework": tr("Workflow framework", "フレームワーク")}
    profile = " / ".join(targets[target]["name"] for _, target in layers)
    draft = ["# AGENTS.md — " + tr("draft, not installed", "生成候補・未適用"), "",
             tr("Complete the project-specific fields and reconcile existing instructions before adoption.",
                "採用前にプロジェクト固有情報を記入し、既存指示と整合させる。"), "",
             "## " + tr("Project-specific fields (owner to complete)", "プロジェクト固有情報（Ownerが記入）"), "",
             tr("- Purpose and architecture: [fill in]\n- Setup, test and lint commands: [fill in]\n"
                "- Critical constraints and approval boundaries: [fill in]\n- Definition of done: [fill in]",
                "- 目的・アーキテクチャ：[要記入]\n- セットアップ・テスト・Lintコマンド：[要記入]\n"
                "- 重要制約・承認境界：[要記入]\n- 完了条件：[要記入]"), ""]
    config = ["# " + tr("Configuration advisory (not executable)", "設定候補（実行用設定ではない）"), "",
              profile, "", tr("Check installed harness, model version and endpoint before applying. "
                              "These settings are not AGENTS.md instructions or permission grants.",
                              "適用前に実行基盤のバージョン、モデル、接続先を確認する。"
                              "以下はAGENTS.md指示でも権限付与でもない。"), ""]
    evidence = ["# " + tr("Selection and evidence", "選択結果と根拠"), "", profile, "",
                "Registry SHA-256: " + registry_digest(sources, targets, practices, data), "",
                tr("Candidate only. No model/harness compatibility or local effectiveness is asserted.",
                   "生成候補のみ。モデルと実行基盤の互換性・ローカルでの有効性は保証しない。"), "",
                tr("Suggested native entry point: ", "適用先候補：") + data["harnesses"][harness]["native_file"],
                data["harnesses"][harness][language], "",
                tr("No implicit family or sibling-model inheritance.", "モデルファミリー・別モデルの暗黙継承なし。"), ""]
    warnings = []
    if model and not any(p["target"] == model and d == "instruction" for _, p, _, d in selected):
        warnings.append(tr("No selected model-specific standing instructions; do not invent or inherit them.",
                           "選択モデル固有の常設指示は未登録または対象外。推測や暗黙継承は行わない。"))
    if model and targets[model]["kind"] == "family":
        warnings.append(tr("A family was explicitly selected; verify each practice against the exact model.",
                           "モデルファミリーを明示選択。各指示の対象モデルを別途確認する。"))
    if warnings:
        evidence.extend(warnings + [""])
    seen_text = set()
    for layer, target in layers:
        entries = []
        for item_layer, p, row, disposition in selected:
            if item_layer != layer or disposition != "instruction":
                continue
            text = row["instruction"][language]
            if text not in seen_text:
                entries.append("- " + text)
                seen_text.add(text)
        if entries:
            draft.extend(["## " + heading[layer], "", *entries, ""])
    for layer, p, row, disposition in selected:
        if disposition == "configuration":
            config.extend([f"## {p['id']} — {p['target']} ({p['status']})", "", p[language], "",
                           "Scope: " + p["scope"], "",
                           tr("Evidence: ", "根拠：") + ", ".join(sources[s]["url"] for s in p["evidence"]), ""])
        evidence.extend([f"## {p['id']} — {disposition}", "",
                         f"Target: {p['target']} | Layer: {layer} | Status: {p['status']} "
                         f"| Local evaluation: {p['local_eval']}", "", p[language], "",
                         "Scope: " + p["scope"], ""])
        if disposition == "instruction":
            evidence.extend([tr("Draft instruction: ", "生成指示：") + row["instruction"][language], ""])
        for sid in p["evidence"]:
            source = sources[sid]
            evidence.append(f"- [{sid}]({source['url']}) — inspected {source['checked']}")
        evidence.append("")
    if not any(d == "configuration" for _, _, _, d in selected):
        config.extend([tr("No applicable configuration records were selected.",
                          "選択条件に合う設定レコードはありません。"), ""])
    return {"AGENTS.draft.md": "\n".join(draft) + "\n",
            "CONFIGURATION.md": "\n".join(config) + "\n",
            "EVIDENCE.md": "\n".join(evidence) + "\n"}


def write_bundle(directory, documents):
    """Only a new directory; exclusive file creation. No implicit adoption."""
    directory = Path(directory)
    require(set(documents) == {"AGENTS.draft.md", "CONFIGURATION.md", "EVIDENCE.md"},
            "unexpected output names")
    directory.mkdir(exist_ok=False)
    for name, content in documents.items():
        with (directory / name).open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
