# Updating New Industry

The owner requests that every completed update be validated, committed, pushed to
`main`, and deployed as a matching GitHub release with the Windows installer ZIP
and SHA256SUMS. Install the completed update in the owner's local Frostpunk copy
when the game is closed. Do not stop after making local source changes.

Use `builder/` as the source of truth. Never commit owned game archives,
extracted game assets, save files, local caches, or backup directories. Preserve
the native abilities configuration; the suspended field actions previously
caused a construction crash.

Prefer binary/configuration checks and a bounded startup smoke test over lengthy
manual play. Report the actual validation performed and retain the beta label
until the changed gameplay has had sufficient campaign testing.

The owner requests half-duration research for all mod-added perks and increased
Workshop base research output. Author durations at their original scale; the
builder applies `PERK_RESEARCH_DURATION = 0.5` once after defining all research.
Preserve the base Workshop curve multiplier of 1.5625 (25% above version 3.9)
unless the owner requests another balance change. Keep production-cycle times
separate from research durations.

Difficulty presets and settings live in `configuration.py`. Preserve a user's
persistent config across updates; apply the owner's easiest preset for this
local installation. Public defaults remain standard. Validate all 17 starting
profiles and native difficulty vectors with `builder/validate_configuration.py`.
Configurable research defaults remain 0.5 / 1.5625; user overrides are explicit.

Keep added research in the explicit columns in `builder/research_organization.py`.
Every non-tier research prerequisite must be visible in the same column and
earlier tier; do not restore hidden native/cross-tab gates. Recipe output icons
must match native economy coordinates. Validate civic laws and all icon subjects
with `builder/validate_civic.py`. Preserve the 112 native law records. New laws
use the native on-sign effect vector at layout +67, not the unrelated +50
metadata vector. Preserve original book and law order. Append new laws at the
actual footer located by `law_records`, before the 89 unlabelled society bytes.
Native book slots and unlock predicates must remain byte-identical. Charters
belong in Adaptation / Administration, away from the book centre and native
nodes. The former Civic Charters category is hidden, appended compatibility
data only. Verify Arks core manufacturing in Industry column one.
