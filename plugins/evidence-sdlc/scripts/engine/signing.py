"""Keyed integrity for Evidence Chain records.

The gate engine and the agent's shell run as the same OS user, so any file the
engine can write, a determined agent can write too. What the agent cannot do is
produce a valid signature without the key. The organisation provides
EVIDENCE_SIGNING_KEY to the Claude Code process (managed-settings `env`) and hides
it from the agent's commands (managed-settings `sandbox.credentials.envVars` deny,
and a Read/sandbox file deny on the managed-settings file itself). Hooks run
outside the sandbox and can sign; sandboxed Bash cannot.

Without a key the framework runs in UNSIGNED mode: records are still checked for
consistency, but a forged record cannot be told apart from a real one, and the
session-start message says so.
"""
import hashlib
import hmac
import json
import os

ENV = "EVIDENCE_SIGNING_KEY"


def key():
    k = os.environ.get(ENV, "")
    return k.encode() if len(k) >= 32 else None


def enabled():
    return key() is not None


def _canon(obj):
    body = {k: v for k, v in obj.items() if k != "sig"}
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode()


def sign(obj):
    k = key()
    if not k:
        return obj
    obj = dict(obj)
    obj["sig"] = hmac.new(k, _canon(obj), hashlib.sha256).hexdigest()
    return obj


def verify(obj):
    """True if signed with the current key; None if no key is configured (unsigned mode)."""
    k = key()
    if not k:
        return None
    sig = obj.get("sig")
    if not isinstance(sig, str):
        return False
    return hmac.compare_digest(sig, hmac.new(k, _canon(obj), hashlib.sha256).hexdigest())
