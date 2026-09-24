"""Secret detection for content an agent is about to write or commit.

Findings carry a rule id, a line number and a fingerprint (sha256 of the matched
value). The matched value itself is never returned or logged. Allowlisting is by
fingerprint in .evidence/secrets-allowlist.json, which is a control-plane file the
agent cannot write.
"""
import hashlib
import math
import re

RULES = [
    ("aws-access-key-id", re.compile(r"\b((?:AKIA|ASIA|ABIA|ACCA)[0-9A-Z]{16})\b")),
    ("aws-secret-access-key", re.compile(r"(?i)aws.{0,20}?(?:secret|sk).{0,20}?['\"=:\s]([A-Za-z0-9/+]{40})\b")),
    ("github-token", re.compile(r"\b((?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,255})\b")),
    ("github-fine-grained-pat", re.compile(r"\b(github_pat_[A-Za-z0-9_]{60,255})\b")),
    ("gitlab-token", re.compile(r"\b(glpat-[A-Za-z0-9_\-]{20,})\b")),
    ("slack-token", re.compile(r"\b(xox[abprs]-[A-Za-z0-9-]{10,})\b")),
    ("slack-webhook", re.compile(r"(https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[A-Za-z0-9]{20,})")),
    ("stripe-secret-key", re.compile(r"\b((?:sk|rk)_(?:live|test)_[A-Za-z0-9]{20,})\b")),
    ("google-api-key", re.compile(r"\b(AIza[0-9A-Za-z_\-]{35})\b")),
    ("gcp-service-account-key", re.compile(r"(\"private_key_id\"\s*:\s*\"[a-f0-9]{40}\")")),
    ("anthropic-api-key", re.compile(r"\b(sk-ant-[A-Za-z0-9_\-]{20,})\b")),
    ("openai-api-key", re.compile(r"\b(sk-(?:proj-)?[A-Za-z0-9_\-]{32,})\b")),
    ("npm-token", re.compile(r"\b(npm_[A-Za-z0-9]{36})\b")),
    ("sendgrid-key", re.compile(r"\b(SG\.[A-Za-z0-9_\-]{22}\.[A-Za-z0-9_\-]{43})\b")),
    ("twilio-key", re.compile(r"\b(SK[0-9a-fA-F]{32})\b")),
    ("private-key-block", re.compile(r"(-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY(?: BLOCK)?-----)")),
    ("jwt", re.compile(r"\b(eyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,})\b")),
    ("connection-string-password", re.compile(r"\b((?:postgres(?:ql)?|mysql|mariadb|mongodb(?:\+srv)?|redis|amqps?|mssql|sqlserver)://[^:\s/@]+:([^@\s/]{6,})@)")),
    ("azure-storage-key", re.compile(r"(AccountKey=[A-Za-z0-9+/=]{60,})")),
]

# key = "value" style assignments of credentials. Only flagged when the value
# looks random (entropy) and is not an obvious placeholder or a reference to an
# environment variable / secret store.
_ASSIGN = re.compile(
    r"(?i)\b([A-Za-z0-9_.\-]*(?:password|passwd|pwd|secret|token|api[_-]?key|apikey|access[_-]?key|"
    r"private[_-]?key|client[_-]?secret|auth[_-]?token|signing[_-]?key)[A-Za-z0-9_.\-]*)\s*[:=]\s*['\"]([^'\"\s]{12,})['\"]"
)
_PLACEHOLDER = re.compile(
    r"(?i)^(?:x+|\*+|changeme|change[-_]?me|example|placeholder|your[-_].*|<.*>|\$\{.*\}|\$\(.*\)|%\(.*\)s|"
    r"dummy|test|testing|fake|redacted|none|null|todo|replace[-_]?me|xxx.*|\{\{.*\}\})$"
)


def _entropy(s):
    if not s:
        return 0.0
    counts = {}
    for ch in s:
        counts[ch] = counts.get(ch, 0) + 1
    n = len(s)
    return -sum(c / n * math.log2(c / n) for c in counts.values())


def fingerprint(value):
    return hashlib.sha256(value.encode("utf-8", "replace")).hexdigest()[:24]


def scan(text, allowlist=()):
    """Return a list of findings: {rule, line, fingerprint}. Never the value."""
    if not text:
        return []
    allow = set(allowlist or ())
    findings = []
    seen = set()
    lines = text.splitlines() or [text]
    for lineno, line in enumerate(lines, 1):
        for rule, rx in RULES:
            for m in rx.finditer(line):
                value = m.group(1)
                fp = fingerprint(value)
                if fp in allow or (rule, fp) in seen:
                    continue
                seen.add((rule, fp))
                findings.append({"rule": rule, "line": lineno, "fingerprint": fp})
        for m in _ASSIGN.finditer(line):
            value = m.group(2)
            if _PLACEHOLDER.match(value) or value.startswith(("$", "os.environ", "process.env", "ENV[")):
                continue
            if _entropy(value) < 3.2 or len(set(value)) < 8:
                continue
            fp = fingerprint(value)
            if fp in allow or ("generic-credential", fp) in seen:
                continue
            seen.add(("generic-credential", fp))
            findings.append({"rule": "generic-credential", "line": lineno, "fingerprint": fp})
    return findings
