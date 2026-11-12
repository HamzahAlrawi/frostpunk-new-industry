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
