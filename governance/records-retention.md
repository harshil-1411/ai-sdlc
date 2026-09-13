# Records retention: agent sessions and SDLC artifacts

Owner: QA/RA with Legal and Information Security. Decide this deliberately — the default
is whatever the tooling happens to do, which is not a policy.

## What records exist

| Record | System of record | Contains |
| --- | --- | --- |
| Artifact chain (intent/spec/plan/diff/PR) | Git | The development record. Retain per existing source-control retention. |
| Test-evidence artifacts (screenshots, video, signed manual-test attestations) | `validation/evidence/<tracker-key>/` (or the project's own declared location, per the evidence profile in `evidence-package`) | Screenshots, video and signed attestations captured at execution time for manual and regulated test runs — this is validation evidence, not a development record |
| Session transcripts | Claude Code / Compliance API export | The full working conversation, including reasoning and discarded approaches |
| Telemetry (OpenTelemetry export) | Observability stack | Tool calls, hook allow/block verdicts with timestamps, session attribution |
| Local agent edit log | `.claude/logs/` in the repo | Convenience only — not a system of record |
| Eval runs | CI | Configuration acceptance evidence |
| Plugin-generated logs | Wherever the plugin writes them, typically under the user's home directory | Some plugins keep their own debug or finding logs locally. Inventory them; they are not covered by your other retention rules by default |

## Third-party plugin data flows

Any plugin that performs analysis by calling a model endpoint is a data flow out of the
development environment, and any plugin that writes a local log is a record you did not
plan for. Both need to appear in your data-flow documentation and your retention policy.
Establish for each approved plugin: what leaves the machine, what is written locally,
where, and whether it rotates. See `docs/third-party-tooling.md`.

## The decisions to make and write down

1. **Retention period for transcripts.** They are development records, not regulated
   records. A shorter period than source control is defensible and probably right.
   Long retention creates discovery exposure without adding validation value — the
   committed artifact chain is the evidence, not the conversation that produced it.
2. **Access.** Who can read another engineer's transcripts, and under what process?
   Default to restricted; a transcript can contain half-formed reasoning that reads
   badly out of context.
3. **Legal hold.** Confirm transcripts are within scope of your hold process and that
   the export mechanism can satisfy a hold. Test it once.
4. **Deletion.** Confirm the deletion path exists and works before you need it.
5. **What is the audit trail.** State plainly: **git history and the telemetry export
   are the audit trail; transcripts are working papers.** Without this sentence,
   someone will eventually be asked to produce transcripts as validation evidence.
6. **Retention period and access for test-evidence artifacts.** Unlike session
   transcripts, these can be genuine validation evidence — a shorter retention period
   is not automatically defensible the way it is for transcripts, and may need to
   match the retention period of the regulated record the test proved rather than the
   shorter development-record period.

## Do not

Do not treat transcripts as the traceability record. They are unstructured, long, and
contain rejected approaches. The traceability matrix is derived from the artifact chain.
