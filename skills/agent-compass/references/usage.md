# Retrieval

Public base: https://yohi.github.io/agent-compass/

Read the manifest first using an allowed fetch tool or a read-only command
such as `curl --fail --silent --show-error https://yohi.github.io/agent-compass/api/v1/manifest.json`.
All manifest paths are relative to the public base, not to api/v1/.

Example (OpenCode + Kimi K3 + explicitly adopted Superpowers):
- knowledge/common.md
- knowledge/harnesses/opencode.md
- knowledge/models/kimi-k3.md
- knowledge/frameworks/superpowers.md

Use .ja.md for Japanese. Families are separate under knowledge/families/.
For structured retrieval, use api/v1/targets/<exact-id>.json; each includes
its practices, referenced sources and placements. Use api/v1/targets.json
for the full target index and paths. Never infer IDs or version compatibility.

For a generated draft, use api/v1/generator.json to look up the exact key
`opencode|kimi-k3|superpowers|ja`. Optional model/framework fields are empty,
not the string "null". Retrieve the indicated bundle from the public base.
The bundle includes AGENTS.draft.md, CONFIGURATION.md, and EVIDENCE.md.
Compare SHA-256 against the index if your tool supports byte verification.
Check that the index and retrieved registry snapshot agree; retry on mismatch.
Do not install or overwrite project instructions automatically.

A local checkout provides `python compass.py show --target opencode`,
`python compass.py generate --harness opencode --model kimi-k3`, and
`python compass.py audit ./AGENTS.md --harness opencode --model kimi-k3`.
These commands use the checkout's registry, which may not be current.
Do not clone or execute remote code unless permitted. Prefer direct retrieval.
