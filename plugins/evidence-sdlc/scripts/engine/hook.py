#!/usr/bin/env python3
"""Hook entry point: `python3 hook.py pre|post|session-start`.

Reads the Claude Code hook payload on stdin and writes the hook response on
stdout. PreToolUse fails closed: any error, including malformed input, is a
deny with the error in the reason. Post and SessionStart never block.
"""
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import evidence_policy as ep  # noqa: E402
import state as st  # noqa: E402


def emit(obj):
    sys.stdout.write(json.dumps(obj))
    sys.stdout.write("\n")


def pre_response(decision):
    out = {"hookSpecificOutput": {"hookEventName": "PreToolUse"}}
    if not decision.allow:
        out["hookSpecificOutput"]["permissionDecision"] = "deny"
        out["hookSpecificOutput"]["permissionDecisionReason"] = decision.reason
    elif decision.context:
        out["hookSpecificOutput"]["additionalContext"] = decision.context
    return out


def _summ(ctx):
    ti = ctx.tool_input
    if ctx.tool == "Bash":
        return {"command": (ti.get("command") or "")[:2000]}
    p = ti.get("file_path") or ti.get("notebook_path") or ti.get("path")
    if p:
        rel, _ = st.normalize(p, ctx.cwd, ctx.root)
        return {"path": rel if rel is not None else p}
    if ctx.tool in ("Agent", "Task"):
        return {"subagent_type": ti.get("subagent_type") or "general-purpose",
                "description": (ti.get("description") or "")[:200]}
    return {}


def _model(ctx):
    """The model the session is running, from the tail of its transcript (best effort)."""
    tp = ctx.payload.get("transcript_path")
    if not tp or not os.path.isfile(tp):
        return None
    try:
        with open(tp, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 65536))
            tail = f.read().decode("utf-8", "replace")
        import re as _re
        m = _re.findall(r'"model"\s*:\s*"([^"]+)"', tail)
        return m[-1] if m else None
    except OSError:
        return None


def _audit(ctx, entry):
    try:
        key, _ = ctx.change()
        base = {"tool": ctx.tool, "key": key, "agent_type": ctx.agent_type or None,
                "agent_id": ctx.payload.get("agent_id"), "permission_mode": ctx.permission_mode,
                "engine": st.ENGINE_VERSION, "model": _model(ctx)}
        base.update(_summ(ctx))
        base.update(entry)
        st.audit_append(ctx.root, ctx.session, base)
    except Exception:  # the audit log must never break a session
        traceback.print_exc(file=sys.stderr)


def run_pre(payload):
    ctx = ep.Ctx(payload)
    decision = ep.decide_pre(ctx)
    if decision.allow and ctx.tool == "Bash":
        try:
            import integrity
            integrity.snapshot(ctx)
        except Exception:
            traceback.print_exc(file=sys.stderr)
    if not decision.allow:
        _audit(ctx, {"event": "deny", "rule": decision.rule, "reason": decision.reason[:500]})
    elif ctx.tool in ("Agent", "Task"):
        _audit(ctx, {"event": "agent-dispatched"})
    return pre_response(decision)


def run_post(payload):
    ctx = ep.Ctx(payload)
    if ctx.tool in ("Agent", "Task"):
        resp = payload.get("tool_response")
        failed = isinstance(resp, dict) and (resp.get("is_error") or resp.get("error"))
        _audit(ctx, {"event": "agent-failed" if failed else "agent-completed",
                     "subagent_type": ctx.tool_input.get("subagent_type") or "general-purpose"})
        return None
    out = None
    if ctx.tool in ("Edit", "Write", "MultiEdit"):
        out = run_sensor(payload, ctx)
    if ctx.tool == "Bash":
        out = run_integrity(ctx) or out
    if ctx.tool in ("Edit", "Write", "MultiEdit", "NotebookEdit", "Bash"):
        p = ctx.tool_input.get("file_path") or ctx.tool_input.get("notebook_path")
        rel = st.normalize(p, ctx.cwd, ctx.root)[0] if p else None
        gated = bool(rel and not st.glob_match(rel, ctx.policy.get("ungated", []))) or ctx.tool == "Bash"
        _audit(ctx, {"event": "tool", "gated": gated})
        # First source edit inside an approved change moves it to "implementing".
        key, state = ctx.change()
        if key and state and state.get("stage") == "approved" and ctx.tool != "Bash":
            p = ctx.tool_input.get("file_path") or ctx.tool_input.get("notebook_path")
            rel, _ = st.normalize(p, ctx.cwd, ctx.root) if p else (None, None)
            if rel and not st.glob_match(rel, ctx.policy.get("ungated", [])):
                state["stage"] = "implementing"
                state.setdefault("history", []).append({"stage": "implementing", "at": st.now(), "by": "engine"})
                st.save_state(ctx.root, key, state)
    return out


def run_integrity(ctx):
    import integrity

    def judge(rel):
        full = os.path.join(ctx.root, rel)
        content = None
        try:
            if os.path.isfile(full) and os.path.getsize(full) <= 2 * 1024 * 1024:
                content = open(full, encoding="utf-8", errors="replace").read()
        except OSError:
            pass
        return ep.check_write(ctx, full, content=content, kind="write" if os.path.exists(full) else "delete",
                              detail="unparsed program")

    notes, violations = integrity.check(ctx, judge)
    if not violations:
        return None
    key, state = ctx.change()
    for v in violations:
        _audit(ctx, {"event": "integrity-violation", "violation_path": v["path"], "rule": v["rule"], "action": v["action"]})
    st.record_violations(ctx.root, key, state, ctx.branch, violations, ctx.session)
    msg = ("Integrity monitor: " + " ".join(notes) + " Push and pull requests are blocked for this change until the "
           "unapproved changes are reverted and a human clears the record with `evidence change clear-violations "
           f"{key or '<KEY>'}` in their own terminal.")
    return {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": msg}}


def run_sensor(payload, ctx=None):
    import sensor
    ctx = ctx or ep.Ctx(payload)
    p = ctx.tool_input.get("file_path") or ctx.tool_input.get("path")
    if not p:
        return None
    full = p if os.path.isabs(p) else os.path.join(ctx.cwd, p)
    note = sensor.check(full if os.path.isfile(full) else p, ctx.root)
    if note:
        return {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": note}}
    return None


def run_session_start(payload):
    ctx = ep.Ctx(payload)
    key, state = ctx.change()
    parts = [f"Evidence Chain gates live (engine {st.ENGINE_VERSION}; policy: {' + '.join(ctx.policy.get('_sources', []))})."]
    parts.append(f"Branch: {ctx.branch or '(none)'}.")
    if not key:
        parts.append("No active change: source edits are denied until a branch carrying a tracker key has a change "
                     "started with `evidence change start <KEY> --tier <n> --kind feature|fix|chore` and a human-approved plan.")
    elif not state:
        parts.append(f"Active key {key} has no change state yet. Run `evidence change start {key} --tier <n> --kind …`.")
    else:
        tier = int(state.get("tier") or 1)
        missing = [a for a in st.required_artifacts(tier) if not st.find_artifact(ctx.root, key, a, state)]
        approval = st.load_approval(ctx.root, key)
        plan = st.find_artifact(ctx.root, key, "plan", state)
        approved = bool(approval and plan and approval.get("plan_sha256") == st.sha256_file(plan))
        parts.append(f"Active change {key}: Tier {tier}, {state.get('kind', 'feature')}, stage {state.get('stage')}; "
                     f"plan {'approved by ' + str(approval.get('approver')) if approved else 'NOT approved'}"
                     + (f"; missing {', '.join(missing)}" if missing else "") + ".")
        req = ctx.policy.get("required_agents", {}).get(str(tier), [])
        done = st.recorded_agents(ctx.root, key)
        if req:
            parts.append(f"Review agents required before push/PR: {', '.join(req)} (recorded so far: {', '.join(sorted(done)) or 'none'}).")
    import signing
    if not signing.enabled():
        parts.append("UNSIGNED MODE: no EVIDENCE_SIGNING_KEY is configured, so approvals and audit entries are not "
                     "signed and a forged record cannot be told apart from a real one (see docs/managed-settings.md).")
    parts.append("Approval, tier changes and control-plane files are human-only. Commits need the tracker key and an "
                 f"`Agent-Session: {ctx.session or '<session id>'}` trailer.")
    return {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": " ".join(parts)}}


def run_prompt(payload):
    """UserPromptSubmit: the only channel the model cannot write to. A human's
    `/evidence-sdlc:approve KEY SHA` (or `evidence approve KEY SHA`) is recorded here."""
    import lifecycle
    cwd = payload.get("cwd") or os.getcwd()
    msg = lifecycle.approve_from_prompt(st.repo_root(cwd), payload.get("prompt") or "")
    if msg:
        return {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": msg}}
    return None


def main():
    event = sys.argv[1] if len(sys.argv) > 1 else "pre"
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else None
        if not isinstance(payload, dict):
            raise ValueError("hook input is not a JSON object")
    except ValueError as e:
        if event == "pre":
            emit(pre_response(ep.deny("malformed", f"Gate engine could not read the hook input ({e}); failing closed.")))
        return 0
    try:
        if event == "pre":
            emit(run_pre(payload))
        elif event == "post":
            out = run_post(payload)
            if out:
                emit(out)
        elif event == "session-start":
            emit(run_session_start(payload))
        elif event == "sensor":
            out = run_sensor(payload)
            if out:
                emit(out)
        elif event == "prompt":
            out = run_prompt(payload)
            if out:
                emit(out)
    except Exception as e:  # fail closed on PreToolUse only
        traceback.print_exc(file=sys.stderr)
        if event == "pre":
            emit(pre_response(ep.deny("engine-error",
                                      f"Gate engine error ({type(e).__name__}: {e}); failing closed. "
                                      "Report this with the command that triggered it.")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
