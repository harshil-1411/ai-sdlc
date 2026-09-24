# Records retention: agent sessions and SDLC artifacts

Owner: QA/RA with Legal and Information Security. Decide this deliberately — the default
is whatever the tooling happens to do, which is not a policy.

## What records exist

| Record | System of record | Contains |
| --- | --- | --- |
| Artifact chain (intent/spec/plan/diff/PR) | Git | The development record. Retain per existing source-control retention. |
| Test-evidence artifacts (screenshots, video, signed manual-test attestations) | `validation/evidence/<tracker-key>/` (or the project's own declared location, per the evidence profile in `evidence-package`) | Screenshots, video and signed attestations captured at execution time for manual and regulated test runs — this is validation evidence, not a development record |
| Session transcripts | Claude Code / Compliance API export | The full working conversation, including reasoning and discarded approaches |
| Gate audit log | `.evidence/audit/<session>.jsonl` in the repo, committed with the change | One hash-chained entry per agent Edit/Write/MultiEdit/NotebookEdit/Bash call, per gate **deny (with rule and reason)**, per review-agent dispatch/completion, and per approval. Fields: ts, session, user, tool, path/command, key, agent_type, agent_id, permission_mode, engine version. Verify integrity with `evidence audit verify` (engine cases V2A-02*). Agents cannot write it directly (control plane, cases V2G-09*). |
| Commit attribution | Git | Every agent commit carries an `Agent-Session: <session_id>` trailer (engine cases V2A-03*) — `git log --grep 'Agent-Session:'` maps commits to audit logs |
| Approval records | `.evidence/changes/<KEY>/approval.json`, committed | Approver, method (prompt / terminal / GitHub), and the plan sha256 approved |
| Telemetry (OpenTelemetry export) | Your observability stack — **owner action** | `managed-settings.json` ships the OTel env block (`CLAUDE_CODE_ENABLE_TELEMETRY=1`, OTLP metrics and logs exporters, `OTEL_LOG_USER_PROMPTS=0`) with a placeholder `OTEL_EXPORTER_OTLP_ENDPOINT`. Nothing is exported until you set the endpoint to your collector. Content is what Claude Code's own telemetry emits; the gate audit log above is the record of gate verdicts. |
| Eval runs | CI (manual dispatch) and `plugins/*/evals/SUMMARY.md` | Configuration acceptance evidence |
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
5. **What is the audit trail.** State plainly: **git history, the committed
   hash-chained gate audit log (`.evidence/audit/*.jsonl`, checked with
   `evidence audit verify`) and the approval records are the audit trail; the
   OpenTelemetry export, once you point it at a collector, is the off-box copy;
   transcripts are working papers.** Without this sentence, someone will eventually be
   asked to produce transcripts as validation evidence. Be clear about one limit: the
   in-repo log is **tamper-evident, not tamper-proof** — someone with shell access
   outside the agent can rewrite the whole chain consistently. Tamper resistance comes
   from shipping records off the machine (OTel collector, or the log retained as a CI
   artifact), which is an owner action.
6. **Retention period and access for test-evidence artifacts.** Unlike session
   transcripts, these can be genuine validation evidence — a shorter retention period
   is not automatically defensible the way it is for transcripts, and may need to
   match the retention period of the regulated record the test proved rather than the
   shorter development-record period.

## Do not

Do not treat transcripts as the traceability record. They are unstructured, long, and
contain rejected approaches. The traceability matrix is derived from the artifact chain.
