"""Build a public static portal from validated canonical registries."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import re
import shutil

import agent_exports
import auditor
import compass
import generator

ROOT = Path(__file__).resolve().parent
ASSETS = ("index.html", "style.css", "app.js", "audit.js")
ID = re.compile(r"[a-z0-9][a-z0-9.-]{0,79}\Z", re.ASCII)


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n",
                    encoding="utf-8")


def bundle_name(harness, model, framework, language):
    parts = [harness, model or "_", framework or "_", language]
    if any(not ID.fullmatch(p) and p != "_" for p in parts):
        raise ValueError("invalid profile component")
    return "__".join(parts) + ".json"


def build(output):
    sources, targets, practices = compass.load_registry()
    data = generator.load_generation(targets, practices)
    rules = auditor.load_rules(practices)
    output = Path(output)
    # Exclusive directory creation. No cleanup or overwrite of arbitrary paths.
    output.mkdir(exist_ok=False)
    bundles = output / "bundles"
    bundles.mkdir()
    for asset in ASSETS:
        shutil.copyfile(ROOT / "web" / asset, output / asset)
    models = [k for k, v in targets.items() if v["kind"] in {"model", "family"}]
    profiles = {}
    for h, m, f, lang in itertools.product(data["harnesses"], [None, *models],
                                            [None, *data["frameworks"]], ("ja", "en")):
        name = bundle_name(h, m, f, lang)
        docs = generator.generate(sources, targets, practices, data, h, m, f, lang)
        path = bundles / name
        write_json(path, docs)
        profiles["|".join((h, m or "", f or "", lang))] = {
            "path": "bundles/" + name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    metadata = {"schema_version": 1,
                "version": re.search(r'^version = "([^"]+)"', (ROOT / "pyproject.toml").read_text(),
                                     re.M).group(1),
                "registry_sha256": generator.registry_digest(sources, targets, practices, data),
                "sources": list(sources.values()), "targets": list(targets.values()),
                "practices": list(practices.values()), "generation": data,
                "audit": {"advisory_line_count": rules["advisory_line_count"],
                          "rules": rules["rules"], "max_bytes": auditor.MAX_INPUT_BYTES,
                          "max_findings": auditor.MAX_FINDINGS},
                "profiles": profiles}
    write_json(output / "data.json", metadata)
    agent_exports.export(output, metadata)
    (output / ".nojekyll").touch()
    print(f"Built {len(practices)} practices, {len(sources)} sources, "
          f"{len(targets)} targets and {len(profiles)} generator bundles")
    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("_site"))
    build(parser.parse_args().output)
