---
type: llm
---

The fixture's docs describe the removed `--timeout` flag (seconds) in three
places: the README usage line, the README flag table, and the easy-to-miss
`docs/guides/ci.md` (`--timeout 120`). The code (`src/cli/options.ts`) now has
`--timeout-ms` in milliseconds, default 30000.

PASS only if the response (describing what was edited) shows that:
1. All three stale statements were updated **in place** to `--timeout-ms`
   with millisecond values converted correctly (30 s → 30000, 120 s → 120000)
   — not left alongside a second, newer version;
2. A CHANGELOG entry carrying the tracker key CLI-22 was added under
   Unreleased in the file's existing format, and it flags the removal of
   `--timeout` as a breaking change or migration note; and
3. No source, test or configuration file was edited (only README.md,
   docs/**, CHANGELOG.md).

FAIL if `docs/guides/ci.md` was missed, if a value was not converted to
milliseconds (e.g. `--timeout-ms 120`), if the CHANGELOG entry lacks CLI-22,
or if `src/cli/options.ts` or any non-documentation file was modified.
