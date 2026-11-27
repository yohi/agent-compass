# APM distribution / APMによるSkill配布

Agent Compass has one portable Agent Skill: skills/agent-compass/SKILL.md
and its three reference files. APM supports manifestless single-skill
subdirectories. No separate apm.yml, plugin.json, duplicated skill, runtime
script, dependency or MCP server is needed in this package.

Official APM documentation:
- https://microsoft.github.io/apm/consumer/manage-dependencies/
- https://microsoft.github.io/apm/reference/cli/install/
- https://microsoft.github.io/apm/producer/create-a-package/

From an authorized consumer project, select the actual harness:

```sh
apm install yohi/agent-compass/skills/agent-compass --target opencode
# Or --target codex / claude / gemini / cursor / copilot as appropriate.
```

For reproducible installation append #<reviewed-commit-sha> after the
skill subdirectory. Equivalent consumer manifest dependency:

```yaml
dependencies:
  apm:
    - yohi/agent-compass/skills/agent-compass#<reviewed-commit-sha>
```

Merge that entry into the existing consumer manifest, not replace it.
Retain the generated apm.lock.yaml. Do not use global installation, compile
or force unless authorized. Inspect the deployed files and project rules.
APM selects the appropriate deployment paths for the harness.

The skill contains the retrieval procedure and references, not a frozen
copy of the knowledge. At task time it fetches scoped Markdown/JSON from
Pages, verifies scope/status/evidence and preserves project constraints.
Pinning the skill fixes its procedure, not the live registry. Use a pinned
local snapshot when guidance reproducibility is needed.

The repository tests check the standalone package allowlist, frontmatter,
local references and absence of scripts/dependencies. This is static contract
validation, not actual APM installation or harness runtime discovery.
To verify the installed APM version, use a disposable authorized consumer
project, inspect the lockfile and four deployed files, then invoke the skill
for a read-only scoped guidance task. No consumer repository is modified
by Agent Compass CI.
