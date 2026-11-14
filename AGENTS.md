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
