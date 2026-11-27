# Discovery registration / 新モデル・情報源登録

Use discovery issue #2 and its complete candidate archive. An observed link
or model token does not prove a release, official recommendation or availability.

Select a currently observed candidate from registry/discovery.json, review
the official source and exact model identity/scope, then run **Prepare discovery
registration** on master as the repository owner. Supply JSON (illustrative,
not claims about any actual released model):

```json
{
  "index": "google-models",
  "candidate_kind": "model-mention",
  "candidate_value": "gemini-example",
  "target_id": "gemini-example",
  "target_name": "Gemini Example",
  "source_id": "gemini-example-card",
  "source_url": "https://aistudio.google.com/docs/models/gemini-example",
  "source_kind": "official-docs",
  "source_format": "html",
  "lifecycle": "unknown",
  "evidence_quote": "short exact text from the normalized official source"
}
```

For model mentions, target ID equals the discovered token. For a link,
candidate_kind is link, candidate_value equals source_url, and target is
the existing index target or an existing model in the index's prefix scope.
Source must be the registered index itself (model mention only) or a freshly
observed allowlisted link. Publisher comes from the index. Evidence quote
must occur in normalized source text, be 8–150 characters and at most 20
whitespace-delimited words. An explicit lifecycle claim must include the
exact model ID in that quote and be semantically reviewed by the owner.
Check evidence_reviewed only after reviewing the source.

Lifecycle: unknown, preview, generally-available, deprecated, retired.
Existing lifecycle is not erased by adding a source with unknown status.
Optional lifecycle fields record inspection date, evidence source ID,
source hash and quote hash/location. Legacy targets have no lifecycle
assertion. These are owner-reviewed snapshots, not live availability.
Source IDs and existing target identities cannot be repurposed. Duplicate
URLs for the same exact target are rejected. A source may be separately
registered for another exact target by explicit selection.

The workflow verifies the current index, source, literal evidence and
scope, validates/tests registry changes, and creates one draft PR with
the actual target/source diff, regenerated BEST_PRACTICES.md and a
registrations/ receipt. No direct master update, automatic merge or
automatic release assertion. Existing identical PRs are reused; an
interrupted branch must match expected bytes before reuse. GitHub Actions
must have permission to create PRs.

After manual merge, the existing monitor and Gemini maintenance inventory
the registered source and generate practice candidates. Adopt supported
practices using Prepare knowledge adoption or the separately enabled
controlled-adoption policy (AUTO_ADOPTION.md). Registration itself remains manual. There is no second API key,
ledger or quota path. Deliberately do not invoke Gemini before registration:
the owner establishes source identity/scope first, then existing maintenance
handles semantic extraction. New lifecycle changes require another
owner-selected registration against current evidence. No model is removed
automatically. This is owner-dispatched registration support, not unattended
classification of every discovery candidate.
