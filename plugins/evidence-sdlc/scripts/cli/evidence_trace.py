#!/usr/bin/env python3
"""evidence -- derive, gap-check and export the traceability chain from what is
actually committed, instead of assembling it by hand.

Standard library only. No network access, except `gh` calls made by
`tracker ...` and by `export --github`, both of which are explicit opt-ins. No
writes outside the working directory except the file `evidence export --write`
is asked to write.

Subcommands: doctor, scan, gaps, export, tracker. See cli/README.md.
"""
import argparse
import csv
import datetime
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

CSV_COLUMNS = [
    "tracker_key", "requirement_id", "requirement_summary", "spec_commit",
    "implementing_commits", "test_case_id", "automated_test", "test_run_id",
    "result", "evidence_link", "risk_tier", "revalidation",
    "approved_by", "agent_sessions",
]

CSV_REQUIRED_COLUMN = "requirement_id"

DEFAULT_TRACKER_PATTERN = r"[A-Z][A-Z0-9]+-[0-9]+"
DEFAULT_REQ_PATTERN = r"REQ-[A-Za-z0-9]+-[0-9]+"
DEFAULT_TEST_DIR_SEGMENTS = {"tests", "__tests__", "qa"}
DEFAULT_TEST_BASENAME_PATTERNS = [
    re.compile(r"^test_"), re.compile(r"_test\."),
    re.compile(r"\.test\."), re.compile(r"\.spec\."), re.compile(r"_spec\."),
    re.compile(r"(?:Test|Tests|IT)\.(?:java|kt|scala|cs)$"), re.compile(r"\.feature$"),
    re.compile(r"\.bats$"),
]
# Eval cases are tests too (this repository dogfoods itself: `claude plugin eval`
# cases under plugins/<name>/evals/<case>/). Only prompt.md frontmatter
# `covers: [...]` ties a case to a requirement.
DEFAULT_EVAL_GLOBS = ["plugins/*/evals/*/prompt.md"]
# Where results are looked for when there is no .evidence/adapter.yml at all
# (this framework's own layout). An adapter's test_results_location replaces it.
DEFAULT_RESULTS_LOCATIONS = ["plugins/*/evals/results"]
# Directories never walked, whatever .evidenceignore says.
ALWAYS_PRUNED_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".tox"}
MAX_SCAN_BYTES = 2 * 1024 * 1024
STALE_DAYS = 183  # ~6 months
KNOWN_PROFILES = ["stack.md", "deployment.md", "toolchain.md", "design-system.md", "compliance.md"]
CONTROL_SET_REL = Path("plugins/evidence-compliance/skills/regulatory-controls/references")
OWNER_PLACEHOLDER_RE = re.compile(r"^\s*>?\s*Owner:\s*(UNASSIGNED\b|<[^>]*>|\[ASK\])", re.IGNORECASE | re.MULTILINE)
SESSION_TRAILER_RE = re.compile(r"^(Agent-Session|Claude-Session):\s*(\S.*?)\s*$", re.MULTILINE)

# Gap categories, in print order. BLOCKING always fails `gaps`; STRICT_BLOCKING
# additionally fails it under --strict ("every requirement is PROVEN").
GAP_CATEGORIES = [
    "NO COVERAGE", "FAILED", "MISSING-CHILD", "SELF-ASSERTED", "UNPROVEN",
    "UNVERIFIED-RESULT", "ORPHANED", "UNTRACED", "DUPLICATE-ID",
]
BLOCKING = {"NO COVERAGE", "FAILED", "MISSING-CHILD"}
STRICT_BLOCKING = BLOCKING | {"SELF-ASSERTED", "UNPROVEN", "UNVERIFIED-RESULT", "DUPLICATE-ID"}


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def find_repo_root():
    """Walk up from cwd to find a git repo root; fall back to cwd."""
    d = Path.cwd()
    for candidate in [d, *d.parents]:
        if (candidate / ".git").exists():
            return candidate
    return d


def run_git(root, *args):
    try:
        out = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True, text=True, timeout=30,
        )
        if out.returncode != 0:
            return None
        return out.stdout
    except (OSError, subprocess.SubprocessError):
        return None


def is_git_repo(root):
    return (root / ".git").exists()


def read_text(path):
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def rel_posix(root, p):
    return p.relative_to(root).as_posix()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# a deliberately minimal adapter-file reader. Supports flat `key: value` lines,
# `key:` + indented `- item` lists, inline `[a, b]` lists, and surrounding
# quotes on values. Not a YAML parser.
# ---------------------------------------------------------------------------

def _unquote(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


def load_adapter(root):
    path = root / ".evidence" / "adapter.yml"
    if not path.exists():
        return None, None
    text = read_text(path)
    if text is None:
        return None, path
    data = {}
    current_list_key = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if line.lstrip().startswith("- ") and line.startswith(" ") and current_list_key:
            data.setdefault(current_list_key, []).append(_unquote(line.strip()[2:]))
            continue
        if ":" in line and not line.startswith(" "):
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if value.startswith("[") and value.endswith("]"):
                data[key] = [_unquote(v) for v in value[1:-1].split(",") if v.strip()]
                current_list_key = None
            elif value:
                data[key] = _unquote(value)
                current_list_key = None
            else:
                current_list_key = key
                data.setdefault(key, [])
    return data, path


def adapter_get(adapter, key, default):
    if not adapter:
        return default
    return adapter.get(key, default)


def as_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def csv_header_ok(fieldnames):
    """A traceability.csv is only usable if its header actually names the join
    key every other check depends on. csv.DictReader does not raise on a
    missing or wrong column -- it silently returns None for it -- so without
    this check, a genuinely malformed file doesn't fail loudly; it quietly
    manufactures rows like requirement_id="?"."""
    return bool(fieldnames) and CSV_REQUIRED_COLUMN in fieldnames


# ---------------------------------------------------------------------------
# .evidenceignore -- gitignore-style globs, deliberately simple:
#   blank lines and `#` comments ignored; `!` negation NOT supported (reported);
#   a pattern containing `/` (other than a trailing one) is anchored to the repo
#   root, otherwise it matches at any depth; a trailing `/` matches directories
#   only; `*` does not cross `/`, `**` does; `?` is one non-`/` character.
# ---------------------------------------------------------------------------

def _glob_to_regex(pat):
    dir_only = pat.endswith("/")
    anchored = pat.startswith("/") or "/" in pat.rstrip("/")
    pat = pat.strip("/")
    out = []
    i = 0
    while i < len(pat):
        if pat.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pat.startswith("/**", i) and i + 3 == len(pat):
            out.append("(?:/.*)?")
            i += 3
        elif pat.startswith("**", i):
            out.append(".*")
            i += 2
        elif pat[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pat[i] == "?":
            out.append("[^/]")
            i += 1
        elif pat[i] == "[":
            j = pat.find("]", i + 1)
            if j == -1:
                out.append(re.escape(pat[i]))
                i += 1
            else:
                out.append(pat[i:j + 1])
                i = j + 1
        else:
            out.append(re.escape(pat[i]))
            i += 1
    prefix = "^" if anchored else r"^(?:.*/)?"
    suffix = r"/.*$" if dir_only else r"(?:/.*)?$"
    return re.compile(prefix + "".join(out) + suffix)


class IgnoreRules:
    def __init__(self, patterns=(), unsupported=()):
        self.patterns = list(patterns)
        self.regexes = [_glob_to_regex(p) for p in self.patterns]
        self.unsupported = list(unsupported)

    def ignored(self, rel, is_dir=False):
        if not self.regexes:
            return False
        probe = rel + "/" + "_" if is_dir else rel
        return any(r.match(rel) or r.match(probe) for r in self.regexes)


def load_ignore(root):
    path = root / ".evidenceignore"
    text = read_text(path) if path.exists() else None
    if not text:
        return IgnoreRules()
    pats, unsupported = [], []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("!"):
            unsupported.append(line)
            continue
        pats.append(line)
    return IgnoreRules(pats, unsupported)


def walk_files(root, ignore):
    """Every file under root, pruning ALWAYS_PRUNED_DIRS and ignored dirs."""
    for dirpath, dirnames, filenames in os.walk(root):
        d = Path(dirpath)
        rel_d = "" if d == root else rel_posix(root, d)
        keep = []
        for name in dirnames:
            if name in ALWAYS_PRUNED_DIRS:
                continue
            rel = f"{rel_d}/{name}" if rel_d else name
            if ignore.ignored(rel, is_dir=True):
                continue
            keep.append(name)
        dirnames[:] = sorted(keep)
        for name in sorted(filenames):
            rel = f"{rel_d}/{name}" if rel_d else name
            if ignore.ignored(rel):
                continue
            yield d / name, rel


# ---------------------------------------------------------------------------
# structural coverage (REQ-V2C-04)
#
# A requirement ID counts as covered only when it is carried by test SYNTAX --
# something a test framework itself reads -- not by prose near a test. Each
# match is a "binding" (req_id, test_name), where test_name is the test the tag
# belongs to; bindings are what ingested results are matched against.
#   1. decorator / annotation with the ID in its arguments:
#        @pytest.mark.req("REQ-X-01")  @req("REQ-X-01")  @Tag("REQ-X-01")
#   2. a test-framework call whose title string carries the ID:
#        it("REQ-X-01: ...")  test('... REQ-X-01 ...')  describe(...)
#        bats `@test "REQ-X-01 ..."`, shell harness `check_* "REQ-X-01: ..."`,
#        Python harness `case("REQ-X-01 ...")` / `check(f"REQ-X-01 ...")`
#   3. a Playwright tag option:  { tag: ['@REQ-X-01'] }
#   4. a declared test name carrying the ID token:  def test_REQ_X_01_foo
#   5. a Gherkin tag line:  @REQ-X-01  (bound to the following Scenario)
#   6. an eval case prompt.md frontmatter line:  covers: [REQ-X-01]
# A comment line (`#`, `//`, `/*`, `*`, `--`) never counts, whatever it says.
# ---------------------------------------------------------------------------

COMMENT_PREFIXES = ("#", "//", "/*", "*", "--", "<!--")
DECORATOR_RE = re.compile(r"^\s*@([\w.]+)\s*\((.*)$")
DECL_RE = re.compile(
    r"^\s*(?:export\s+)?(?:(?:public|private|protected|internal|static|final|override|suspend|async)\s+)*"
    r"(?:def|function|func|fn|fun|void|class|sub)\s+([A-Za-z_]\w*)"
)
TITLE_CALL_RE = re.compile(
    r"(?:^|[^\w.])(?:it|test|describe|context|specify|scenario|Scenario|case|check|"
    r"(?:it|test|describe)\.(?:only|skip|each\([^)]*\)|concurrent))\s*\(\s*[fr]?(['\"`])(.*?)\1"
)
BATS_RE = re.compile(r"^\s*@test\s+(['\"])(.*?)\1")
HARNESS_RE = re.compile(r"^\s*(?:check_\w+|assert_\w+|expect_\w+|run_case\w*|run_test\w*)\s+(['\"])(.*?)\1")
PW_TAG_RE = re.compile(r"\btag\s*:\s*(\[[^\]]*\]|['\"][^'\"]*['\"])")
GHERKIN_TAGS_RE = re.compile(r"^\s*(?:@[\w.:-]+\s*)+$")
GHERKIN_SCENARIO_RE = re.compile(r"^\s*Scenario(?: Outline)?:\s*(.+)$")
EXCLUDED_DECORATORS = {"pytest.mark.parametrize", "parametrize", "ParameterizedTest", "MethodSource"}


def _ids_in(text, req_pattern):
    return [m.group(0) for m in req_pattern.finditer(text)]


def _ids_in_identifier(name, req_pattern):
    """IDs written as an identifier token, e.g. test_REQ_X_01_foo -> REQ-X-01."""
    dashed = name.replace("_", "-")
    ids = _ids_in(dashed, req_pattern)
    if not ids:
        ids = _ids_in(dashed.upper(), req_pattern)
    return ids


def _next_test_name(lines, start, limit=8):
    for j in range(start, min(len(lines), start + limit)):
        line = lines[j]
        m = TITLE_CALL_RE.search(line)
        if m:
            return m.group(2)
        m = DECL_RE.match(line)
        if m:
            return m.group(1)
        m = GHERKIN_SCENARIO_RE.match(line)
        if m:
            return m.group(1).strip()
    return None


def find_structural_bindings(text, req_pattern):
    """[(req_id, test_name), ...] for every structural tag in a test file."""
    lines = text.splitlines()
    out = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith(COMMENT_PREFIXES):
            continue
        # 1. decorator / annotation
        m = DECORATOR_RE.match(line)
        if m and m.group(1) not in EXCLUDED_DECORATORS and m.group(1).split(".")[-1] not in EXCLUDED_DECORATORS:
            args = m.group(2)
            k = i
            while ")" not in args and k + 1 < len(lines) and k < i + 3:
                k += 1
                args += " " + lines[k]
            ids = _ids_in(args.split(")")[0], req_pattern)
            if ids:
                name = _next_test_name(lines, k + 1) or f"<line {i + 1}>"
                out += [(rid, name) for rid in ids]
            continue
        # 5. Gherkin tag line
        if GHERKIN_TAGS_RE.match(line):
            ids = _ids_in(line, req_pattern)
            if ids:
                name = _next_test_name(lines, i + 1) or f"<line {i + 1}>"
                out += [(rid, name) for rid in ids]
            continue
        # 2. test-framework call titles (and bats / shell-harness labels)
        title = None
        for rx in (BATS_RE, HARNESS_RE):
            mm = rx.match(line)
            if mm:
                title = mm.group(2)
                break
        if title is None:
            mm = TITLE_CALL_RE.search(line)
            if mm:
                title = mm.group(2)
        if title is not None:
            ids = set(_ids_in(title, req_pattern))
            # 3. Playwright tag option on the same line
            for tm in PW_TAG_RE.finditer(line):
                ids |= {x for x in _ids_in(tm.group(1), req_pattern)
                        if f"@{x}" in tm.group(1)}
            out += [(rid, title) for rid in sorted(ids)]
            if ids:
                continue
        else:
            for tm in PW_TAG_RE.finditer(line):
                ids = [x for x in _ids_in(tm.group(1), req_pattern) if f"@{x}" in tm.group(1)]
                if ids:
                    name = _next_test_name(lines, max(0, i - 2)) or f"<line {i + 1}>"
                    out += [(rid, name) for rid in ids]
        # 4. declared test name carrying the ID token
        dm = DECL_RE.match(line)
        if dm:
            name = dm.group(1)
            if name.lower().startswith("test") or name.lower().endswith("test") or "req" in name.lower():
                out += [(rid, name) for rid in _ids_in_identifier(name, req_pattern)]
    return out


def find_eval_covers(text, req_pattern):
    """covers: [...] in a prompt.md's leading `---` frontmatter block only."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return []
    ids = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"^\s*covers\s*:\s*(.*)$", line)
        if m:
            ids += _ids_in(m.group(1), req_pattern)
    return ids


# ---------------------------------------------------------------------------
# result ingestion (REQ-V2C-02): JUnit XML and `claude plugin eval`
# aggregate-result.json. A result is {kind, name, classname, file, case_path,
# status: passed|failed|skipped, props, ts, run_id, source}.
# ---------------------------------------------------------------------------

def _file_ts(p):
    try:
        return datetime.datetime.fromtimestamp(p.stat().st_mtime, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    except OSError:
        return ""


def parse_junit(path, text, source):
    if re.search(r"<!DOCTYPE|<!ENTITY", text):
        raise ValueError("DOCTYPE/ENTITY declarations are refused")
    root_el = ET.fromstring(text)
    if root_el.tag == "testsuites":
        suites = list(root_el.iter("testsuite"))
    elif root_el.tag == "testsuite":
        suites = list(root_el.iter("testsuite"))
    else:
        return None
    results = []
    for suite in suites:
        ts = suite.get("timestamp") or _file_ts(path)
        run_id = f"{suite.get('name') or path.name}@{ts}"
        for case in suite.findall("testcase"):
            if case.find("failure") is not None or case.find("error") is not None:
                status = "failed"
            elif case.find("skipped") is not None:
                status = "skipped"
            else:
                status = "passed"
            props = [p.get("value", "") + " " + p.get("name", "")
                     for p in case.iter("property")]
            results.append({
                "kind": "junit", "name": case.get("name", ""),
                "classname": case.get("classname", ""), "file": case.get("file", ""),
                "case_path": "", "status": status, "props": props,
                "ts": ts, "run_id": run_id, "source": source,
            })
    return results


def parse_eval_json(root, data, source):
    if not (isinstance(data, dict) and isinstance(data.get("cases"), list) and "suite" in data):
        return None
    suite = data.get("suite") or {}
    threshold = suite.get("threshold", 1)
    try:
        threshold = float(threshold)
    except (TypeError, ValueError):
        threshold = 1.0
    if threshold > 1:
        threshold = 1.0
    suite_root = suite.get("root") or ""
    try:
        suite_rel = Path(suite_root).resolve().relative_to(root.resolve()).as_posix()
    except (ValueError, OSError):
        suite_rel = f"plugins/{Path(suite_root).name}" if suite_root else ""
    ts = data.get("startedAt") or ""
    results = []
    for case in data["cases"]:
        if not isinstance(case, dict):
            continue
        runs = (case.get("arms") or {}).get("with") or []
        agg = case.get("aggregates") or {}
        if not runs or all(isinstance(r, dict) and r.get("error") for r in runs):
            status = "skipped"  # infrastructure error: neither a pass nor a failure
        else:
            status = "passed" if float(agg.get("passRate", 0) or 0) >= threshold else "failed"
        case_dir = case.get("dir") or ""
        results.append({
            "kind": "eval", "name": case.get("name", ""), "classname": "",
            "file": "", "case_path": f"{suite_rel}/{case_dir}".strip("/"),
            "status": status, "props": [], "ts": ts,
            "run_id": f"eval@{ts}", "source": source,
        })
    return results


def discover_result_files(root, locations):
    files, missing = [], []
    for loc in locations:
        loc = (loc or "").strip()
        if not loc or loc.lower() == "none" or loc.startswith("[ASK]"):
            continue
        p = Path(loc)
        if not p.is_absolute():
            p = root / loc
        if any(ch in loc for ch in "*?["):
            matches = sorted(root.glob(loc)) if not Path(loc).is_absolute() else []
        else:
            matches = [p] if p.exists() else []
        if not matches:
            missing.append(loc)
        for m in matches:
            if m.is_file():
                files.append(m)
            elif m.is_dir():
                for dp, dn, fn in os.walk(m):
                    dn[:] = [d for d in dn if d not in ALWAYS_PRUNED_DIRS]
                    for n in fn:
                        if n.endswith(".xml") or n.endswith(".json"):
                            files.append(Path(dp) / n)
    seen, uniq = set(), []
    for f in files:
        if f not in seen:
            seen.add(f)
            uniq.append(f)
    return uniq, missing


def ingest_results(root, locations):
    """-> (results_latest, files_parsed, files_unparseable, missing_locations)"""
    files, missing = discover_result_files(root, locations)
    all_results, parsed, bad = [], 0, []
    for f in files:
        try:
            source = f.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            source = str(f)
        try:
            if f.stat().st_size > 50 * 1024 * 1024:
                bad.append(source)
                continue
        except OSError:
            bad.append(source)
            continue
        text = read_text(f)
        if text is None:
            bad.append(source)
            continue
        res = None
        try:
            if f.suffix == ".xml":
                res = parse_junit(f, text, source)
            else:
                res = parse_eval_json(root, json.loads(text), source)
        except (ET.ParseError, ValueError, TypeError, AttributeError):
            res = None
            bad.append(source)
            continue
        if res is None:
            continue  # not a results file at all (some other xml/json)
        parsed += 1
        all_results += res
    # latest wins per test identity
    latest = {}
    for r in all_results:
        key = (r["kind"], r["case_path"] or r["classname"], r["name"])
        if key not in latest or r["ts"] >= latest[key]["ts"]:
            latest[key] = r
    return list(latest.values()), parsed, bad, missing


def _file_compatible(result, test_path):
    f = (result.get("file") or "").replace("\\", "/").lstrip("./")
    if f:
        return test_path.endswith(f) or f.endswith(test_path)
    cls = result.get("classname") or ""
    if cls and " " not in cls and re.search(r"[./:]", cls):
        stem = Path(test_path).stem
        parts = re.split(r"[./:]+", cls)
        return stem in parts or stem.split(".")[0] in parts
    return True


def _id_token_in(rid, *texts):
    alt = rid.replace("-", "_").lower()
    for t in texts:
        if not t:
            continue
        if rid in t or alt in t.lower():
            return True
    return False


def results_for_requirement(rid, graph):
    """Latest ingested results that belong to a test structurally covering rid."""
    matched = []
    bindings = [(t["path"], name, t.get("kind", "test"))
                for t in graph["tests"] for (r, name) in t["bindings"] if r == rid]
    if not bindings:
        return matched
    for res in graph["results"]:
        hit = False
        if res["kind"] == "eval":
            for path, name, kind in bindings:
                if kind == "eval" and res["case_path"] == str(Path(path).parent.as_posix()):
                    hit = True
                    break
        else:
            if _id_token_in(rid, res["name"], res["classname"], *res["props"]):
                hit = True
            else:
                base = res["name"].split("[")[0].strip()
                for path, name, kind in bindings:
                    if kind == "eval" or not name:
                        continue
                    if (base == name or res["name"] == name or res["name"].endswith(" " + name)) \
                            and _file_compatible(res, path):
                        hit = True
                        break
        if hit:
            matched.append(res)
    return matched


# ---------------------------------------------------------------------------
# doctor (REQ-V2C-05, REQ-V2O-03)
# ---------------------------------------------------------------------------

def _control_set_dirs(root):
    cands = [root / CONTROL_SET_REL]
    env = os.environ.get("EVIDENCE_CONTROLS_DIR")
    if env:
        cands.insert(0, Path(env))
    here = Path(__file__).resolve()
    for p in here.parents:
        cands.append(p / CONTROL_SET_REL)
        cands.append(p / "evidence-compliance/skills/regulatory-controls/references")
    seen = []
    for c in cands:
        if c.is_dir() and c not in seen:
            seen.append(c)
    return seen


def referenced_control_sets(compliance_text, stems):
    """Control-set stems named in table rows under '## Applicable frameworks'."""
    refs = set()
    in_section = False
    for line in compliance_text.splitlines():
        if line.startswith("## "):
            in_section = line.strip().lower().startswith("## applicable frameworks")
            continue
        if not in_section or not line.lstrip().startswith("|"):
            continue
        for stem in stems:
            if re.search(rf"(?<![\w-]){re.escape(stem)}(?:\.md)?(?![\w-])", line, re.IGNORECASE):
                refs.add(stem)
    return refs


def gate_canary():
    """Live canary: the shipped gate engine must deny an unapproved source write
    and allow a documentation write, in a throwaway repository."""
    import subprocess
    import tempfile
    hook = Path(__file__).resolve().parent.parent / "engine" / "hook.py"
    label = "gate engine live canary (denies an unapproved source write, allows a docs write)"
    if not hook.is_file():
        return (label, "WARN", f"engine not found at {hook}; run doctor from the evidence-sdlc plugin")
    env = {k: v for k, v in os.environ.items()
           if k not in ("EVIDENCE_ACTIVE_CHANGE", "EVIDENCE_ISSUE_KEY_PATTERN", "EVIDENCE_ORG_POLICY")}
    try:
        with tempfile.TemporaryDirectory(prefix="evidence-canary-") as d:
            subprocess.run(["git", "init", "-q", "-b", "feature/no-key"], cwd=d, check=True, capture_output=True)
            results = {}
            for name, path in (("src", "src/__canary__.py"), ("docs", "docs/__canary__.md")):
                payload = json.dumps({"session_id": "doctor", "cwd": d, "tool_name": "Write",
                                      "tool_input": {"file_path": path, "content": "x"}})
                r = subprocess.run([sys.executable, str(hook), "pre"], input=payload, cwd=d, capture_output=True,
                                   text=True, env=env, timeout=30)
                results[name] = '"permissionDecision": "deny"' in r.stdout
    except (OSError, subprocess.SubprocessError) as e:
        return (label, "FAIL", f"canary could not run: {e}")
    if results.get("src") and not results.get("docs"):
        return (label, "PASS", "engine denied src/__canary__.py and allowed docs/__canary__.md")
    return (label, "FAIL", f"unexpected engine decisions: source denied={results.get('src')}, "
                           f"docs denied={results.get('docs')} -- the gates are not behaving; do not rely on them")


def cmd_doctor(root, args):
    checks = []  # (label, status PASS|WARN|FAIL, detail)

    py = shutil.which("python3")
    checks.append(("python3 resolves on PATH", "PASS" if py else "FAIL",
                   f"found at {py}" if py else
                   "not found -- the gate engine and this CLI need python3 on PATH"))

    checks.append(gate_canary())

    here = Path(__file__).resolve()
    siblings = {"evidence-discovery", "evidence-sdlc", "evidence-quality", "evidence-compliance", "evidence-integrations"}
    found = set()
    for base in list(here.parents)[:6]:
        for name in siblings:
            if (base / name / ".claude-plugin" / "plugin.json").is_file():
                found.add(name)
    missing = sorted(siblings - found - {"evidence-sdlc"})
    checks.append(("Evidence Chain sibling plugins present (soft dependencies)",
                   "PASS" if not missing else "WARN",
                   "all five present" if not missing else
                   "not found next to this plugin: " + ", ".join(missing) +
                   " -- features that read their output degrade (install all five for the full chain)"))

    scripts = sorted(root.glob("plugins/*/scripts/*.sh"))
    jq_call = re.compile(r"(?:^|[\s|;(`$])jq\s", re.MULTILINE)
    jq_needed = any(jq_call.search(read_text(s) or "") for s in scripts)
    jq_path = shutil.which("jq")
    if jq_path:
        checks.append(("jq resolves on PATH", "PASS", f"found at {jq_path}"))
    else:
        checks.append(("jq resolves on PATH", "FAIL" if jq_needed else "WARN",
                       "not found -- " + ("gate scripts in this repo call jq; install it"
                                          if jq_needed else "no gate script here calls jq, informational")))

    unreadable = [rel_posix(root, s) for s in scripts if not os.access(s, os.R_OK)]
    checks.append((
        f"every plugins/*/scripts/*.sh is readable ({len(scripts)} found)",
        "FAIL" if unreadable else "PASS",
        "all readable" if not unreadable else
        "unreadable: " + ", ".join(unreadable) + " -- fix with `chmod +r <path>`",
    ))

    hook_files = sorted(root.glob("plugins/*/hooks/hooks.json"))
    bad_hooks, missing_cmds = [], []
    for hf in hook_files:
        plugin_root = hf.parent.parent
        text = read_text(hf)
        try:
            data = json.loads(text) if text is not None else None
        except json.JSONDecodeError as e:
            bad_hooks.append(f"{rel_posix(root, hf)}: {e}")
            continue
        for cmd, hook_args in _iter_hook_commands(data):
            if hook_args:
                # Exec form: the script is whichever arg is a path. The arg after
                # `-c` is inline shell code (e.g. `bash -c '... exec python3 "$0"'
                # <script>`), never a path, whatever slashes it contains.
                candidates = []
                skip_next = False
                for a in hook_args:
                    if skip_next:
                        skip_next = False
                        continue
                    if a == "-c":
                        skip_next = True
                        continue
                    a = a.replace("${CLAUDE_PLUGIN_ROOT}", str(plugin_root))
                    if "/" in a and not any(ch.isspace() for ch in a):
                        candidates.append(a)
            else:
                resolved = cmd.replace("${CLAUDE_PLUGIN_ROOT}", str(plugin_root))
                for interp in ("bash ", "python3 ", "sh "):
                    if resolved.startswith(interp):
                        resolved = resolved[len(interp):]
                        break
                resolved = resolved.strip().strip('"')
                candidates = [resolved.split()[0].strip('"')] if resolved.split() else [resolved]
            for script_path in candidates:
                if not Path(script_path).exists():
                    missing_cmds.append(f"{rel_posix(root, hf)} -> {script_path}")
    detail_parts = []
    if bad_hooks:
        detail_parts.append("invalid JSON: " + "; ".join(bad_hooks))
    if missing_cmds:
        detail_parts.append("missing script(s) referenced: " + "; ".join(missing_cmds))
    ok = not detail_parts
    checks.append((
        f"every hooks.json parses and every command it references exists ({len(hook_files)} files)",
        "PASS" if ok else "FAIL",
        "all good" if ok else " | ".join(detail_parts) + " -- fix the path or the hooks.json entry",
    ))

    ctx_dir = root / ".evidence" / "context"
    if not ctx_dir.exists():
        checks.append((".evidence/context/ present", "FAIL",
                       "missing entirely -- run stack-discovery, toolchain-discovery, "
                       "design-system-discovery and compliance-discovery"))
    else:
        present = {p.name for p in ctx_dir.glob("*.md")}
        missing_profiles = [p for p in KNOWN_PROFILES if p not in present]
        checks.append((".evidence/context/ present", "PASS",
                       f"{len(present)}/{len(KNOWN_PROFILES)} known profiles present"))
        checks.append((
            "every known profile present",
            "WARN" if missing_profiles else "PASS",
            ("missing: " + ", ".join(missing_profiles) +
             " -- run the matching *-discovery skill") if missing_profiles else "all present",
        ))

    csv_path_doctor = root / "validation" / "traceability.csv"
    if csv_path_doctor.exists():
        reader = csv.DictReader(io.StringIO(read_text(csv_path_doctor) or ""))
        header_ok = csv_header_ok(reader.fieldnames)
        checks.append((
            "validation/traceability.csv header is valid", "PASS" if header_ok else "FAIL",
            "header contains requirement_id, parseable" if header_ok else
            f"header does not contain 'requirement_id' (found: {reader.fieldnames}) -- "
            "every downstream command will treat this file as unreadable, not as zero rows -- "
            "fix the header by hand or regenerate it with `evidence export`",
        ))

    ask_by_file = {}
    if ctx_dir.exists():
        for p in sorted(ctx_dir.glob("*.md")):
            n = (read_text(p) or "").count("[ASK]")
            if n:
                ask_by_file[p.name] = n
    ask_count = sum(ask_by_file.values())
    checks.append((
        "unresolved [ASK] count across profiles",
        "WARN" if ask_count else "PASS",
        (f"{ask_count} unresolved (" + ", ".join(f"{k}: {v}" for k, v in ask_by_file.items()) +
         ") -- each blocks any downstream skill that depends on that area")
        if ask_count else "0 unresolved",
    ))

    stale = []
    if ctx_dir.exists():
        today = datetime.date.today()
        for p in ctx_dir.glob("*.md"):
            head = "\n".join((read_text(p) or "").splitlines()[:6])
            dates = re.findall(r"\b(\d{4}-\d{2}-\d{2})\b", head)
            if not dates:
                continue
            try:
                oldest = min(datetime.date.fromisoformat(d) for d in dates)
            except ValueError:
                continue
            age = (today - oldest).days
            if age > STALE_DAYS:
                stale.append(f"{p.name} ({age} days old)")
    checks.append((
        "profile staleness (established/re-verify date over ~6 months old)",
        "WARN" if stale else "PASS",
        "none stale" if not stale else "STALE: " + ", ".join(stale) + " -- re-run discovery",
    ))

    compliance = ctx_dir / "compliance.md"
    set_dirs = _control_set_dirs(root)
    if compliance.exists() and set_dirs:
        sets = {}
        for d in set_dirs:
            for p in sorted(d.glob("*.md")):
                if p.name in ("README.md", "SKILL.md"):
                    continue
                sets.setdefault(p.stem, p)
        refs = referenced_control_sets(read_text(compliance) or "", list(sets))
        unowned = sorted(f"{s}.md" for s in refs if OWNER_PLACEHOLDER_RE.search(read_text(sets[s]) or ""))
        checks.append((
            "control sets referenced by compliance.md have a named owner",
            "WARN" if unowned else "PASS",
            ("unassigned owner in: " + ", ".join(unowned) +
             " -- name an owner before relying on the set") if unowned else
            (f"{len(refs)} referenced, all owned" if refs else "no control set referenced under '## Applicable frameworks'"),
        ))

    adapter, adapter_path = load_adapter(root)
    if adapter:
        locs = as_list(adapter.get("test_results_location"))
        _, missing = discover_result_files(root, locs)
        checks.append((
            ".evidence/adapter.yml test_results_location resolves",
            "WARN" if missing else "PASS",
            ("not found: " + ", ".join(missing) + " -- results cannot be ingested, so nothing can be PROVEN")
            if missing else (", ".join(locs) if locs else "not set (no results will be ingested)"),
        ))

    ignore = load_ignore(root)
    if ignore.unsupported:
        checks.append((".evidenceignore patterns supported", "WARN",
                       "negation is not supported, ignored: " + ", ".join(ignore.unsupported)))

    fails = sum(1 for _, s, _ in checks if s == "FAIL")
    warns = sum(1 for _, s, _ in checks if s == "WARN")
    print("evidence doctor")
    print("=" * 60)
    for label, status, detail in checks:
        print(f"[{status}] {label}")
        print(f"       {detail}")
    print("=" * 60)
    print(f"RESULT: {fails} FAIL, {warns} WARN.")
    if fails:
        print("Critical check(s) failed -- fix these before trusting any gate in this repo.")
        return 1
    if warns and getattr(args, "strict", False):
        print("--strict: WARN counts as failure.")
        return 1
    return 0


def _iter_hook_commands(hooks_data):
    if not isinstance(hooks_data, dict):
        return
    for event_list in hooks_data.get("hooks", {}).values():
        if not isinstance(event_list, list):
            continue
        for group in event_list:
            for hook in group.get("hooks", []) if isinstance(group, dict) else []:
                cmd = hook.get("command") if isinstance(hook, dict) else None
                if cmd:
                    yield cmd, (hook.get("args") if isinstance(hook, dict) else None)


# ---------------------------------------------------------------------------
# graph -- the in-memory model shared by scan/gaps/export
# ---------------------------------------------------------------------------

def is_test_path(rel, test_dir_segments):
    parts = rel.split("/")
    if any(seg in test_dir_segments for seg in parts[:-1]):
        return True
    return any(pat.search(parts[-1]) for pat in DEFAULT_TEST_BASENAME_PATTERNS)


def build_graph(root, adapter, results_paths=None):
    tracker_pattern = re.compile(adapter_get(adapter, "tracker_pattern", DEFAULT_TRACKER_PATTERN))
    req_pattern = re.compile(adapter_get(adapter, "requirement_pattern", DEFAULT_REQ_PATTERN))
    requirements_source = adapter_get(adapter, "requirements_source", "file_glob")
    ignore = load_ignore(root)

    graph = {
        "requirements": {},   # req_id -> {summary, spec_file, spec_commit, tracker_key}
        "tests": [],          # {path, kind, req_ids: set, bindings: [(req_id, test_name)]}
        "commits": [],        # {sha, subject, tracker_keys: set, pairs: set, sessions: [..]}
        "traceability_rows": [],
        "results": [],        # latest ingested result per test identity
        "results_files": 0,
        "results_unparseable": [],
        "results_missing": [],
        "adapter_used": bool(adapter),
        "requirements_source": requirements_source,
        "skipped_files": 0,
        "spec_files_scanned": 0,
        "test_source_desc": "",
        "csv_malformed": False,
        "duplicate_requirements": {},
        "ignore_patterns": ignore.patterns,
    }

    spec_files = []
    if requirements_source != "tracker":
        spec_globs = as_list(adapter_get(adapter, "spec_glob", ["intent/*/spec.md"]))
        spec_files = sorted({p for g in spec_globs for p in root.glob(g)})
        if not adapter:
            spec_files += sorted(p for p, _ in walk_files(root, ignore)
                                 if p.name == "spec.md" and "intent" not in p.relative_to(root).parts)
        spec_files = [p for p in spec_files if not ignore.ignored(rel_posix(root, p))]
    graph["spec_files_scanned"] = len(spec_files)
    req_id_occurrences = {}
    for spec in spec_files:
        text = read_text(spec)
        if text is None:
            graph["skipped_files"] += 1
            continue
        spec_rel = rel_posix(root, spec)
        for line in text.splitlines():
            if "|" not in line or not req_pattern.search(line):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            # A row defines the ID held by a cell that IS an ID (first such
            # cell); a mention inside prose ("untested REQ-CLI-04..07") is a
            # reference, not a definition.
            idx = next((i for i, c in enumerate(cells) if req_pattern.fullmatch(c.strip("`* "))), None)
            if idx is None:
                continue
            req_id = cells[idx].strip("`* ")
            req_id_occurrences.setdefault(req_id, []).append(spec_rel)
            if req_id in graph["requirements"]:
                continue
            summary = cells[idx + 1] if len(cells) > idx + 1 else ""
            spec_commit = None
            if is_git_repo(root):
                log = run_git(root, "log", "--format=%H", "--follow", "--", spec_rel)
                if log:
                    lines = [l for l in log.splitlines() if l]
                    if lines:
                        spec_commit = lines[-1]
            tracker_key = None
            if spec_commit:
                msg = run_git(root, "log", "-1", "--format=%s%n%b", spec_commit) or ""
                tm = tracker_pattern.search(msg)
                if tm:
                    tracker_key = tm.group(0)
            if not tracker_key:
                tm = re.search(r"^Tracker:\s*(\S+)", text, re.MULTILINE)
                if tm and tracker_pattern.fullmatch(tm.group(1)):
                    tracker_key = tm.group(1)
            graph["requirements"][req_id] = {
                "summary": summary, "spec_file": spec_rel,
                "spec_commit": spec_commit, "tracker_key": tracker_key,
            }
    graph["duplicate_requirements"] = {
        rid: files for rid, files in req_id_occurrences.items() if len(files) > 1
    }

    test_dir_segments = set(as_list(adapter_get(adapter, "test_dir_segments", sorted(DEFAULT_TEST_DIR_SEGMENTS))))
    eval_globs = as_list(adapter_get(adapter, "eval_glob", DEFAULT_EVAL_GLOBS))
    eval_regexes = [_glob_to_regex("/" + g) for g in eval_globs]
    graph["test_source_desc"] = (
        f"test-location conventions (directories named {sorted(test_dir_segments)}, "
        f"basenames test_*/*_test.*/.test./.spec., eval cases {eval_globs}) "
        f"with a structural tag (decorator/marker, test title, name token, eval covers:)"
        + (f", excluding .evidenceignore {ignore.patterns}" if ignore.patterns else "")
    )
    for p, rel in walk_files(root, ignore):
        is_eval = any(r.match(rel) for r in eval_regexes)
        if not is_eval and not is_test_path(rel, test_dir_segments):
            continue
        try:
            if p.stat().st_size > MAX_SCAN_BYTES:
                graph["skipped_files"] += 1
                continue
        except OSError:
            graph["skipped_files"] += 1
            continue
        text = read_text(p)
        if text is None:
            graph["skipped_files"] += 1
            continue
        if is_eval:
            case = p.parent.name
            bindings = [(rid, case) for rid in find_eval_covers(text, req_pattern)]
            kind = "eval"
        else:
            bindings = find_structural_bindings(text, req_pattern)
            kind = "test"
        graph["tests"].append({
            "path": rel, "kind": kind,
            "req_ids": {b[0] for b in bindings}, "bindings": bindings,
        })

    pair_re = re.compile(rf"(?:{tracker_pattern.pattern})/(?:{tracker_pattern.pattern})")
    if is_git_repo(root):
        log = run_git(root, "log", "--format=%H%x1f%s%x1f%b%x1e") or ""
        for entry in log.split("\x1e"):
            entry = entry.strip("\n")
            if not entry:
                continue
            parts = entry.split("\x1f")
            sha = parts[0] if parts else ""
            subject = parts[1] if len(parts) > 1 else ""
            body = parts[2] if len(parts) > 2 else ""
            if not sha:
                continue
            msg = subject + "\n" + body
            keys = set(tracker_pattern.findall(msg)) if not tracker_pattern.groups else \
                {m.group(0) for m in tracker_pattern.finditer(msg)}
            pairs = {m.group(0) for m in pair_re.finditer(msg)}
            sessions = [f"{k}: {v}" for k, v in SESSION_TRAILER_RE.findall(body)]
            graph["commits"].append({
                "sha": sha[:10], "full_sha": sha, "subject": subject,
                "tracker_keys": keys, "pairs": pairs, "sessions": sessions,
            })

    csv_path = root / "validation" / "traceability.csv"
    if csv_path.exists():
        reader = csv.DictReader(io.StringIO(read_text(csv_path) or ""))
        if csv_header_ok(reader.fieldnames):
            graph["traceability_rows"] = list(reader)
        else:
            graph["csv_malformed"] = True

    locations = []
    if adapter is not None and "test_results_location" in adapter:
        locations += as_list(adapter.get("test_results_location"))
    elif adapter is None:
        locations += DEFAULT_RESULTS_LOCATIONS
    locations += list(results_paths or [])
    (graph["results"], graph["results_files"],
     graph["results_unparseable"], missing) = ingest_results(root, locations)
    # the built-in default is best-effort; only explicitly named locations count as missing
    graph["results_missing"] = [m for m in missing if m not in DEFAULT_RESULTS_LOCATIONS]
    return graph


def requirement_status(graph):
    """rid -> {'status': PROVEN|FAILED|NONE, 'results': [...]}"""
    out = {}
    rids = set(graph["requirements"]) | {r.get("requirement_id") for r in graph["traceability_rows"]
                                         if r.get("requirement_id")}
    for rid in rids:
        res = results_for_requirement(rid, graph)
        if any(r["status"] == "failed" for r in res):
            st = "FAILED"
        elif any(r["status"] == "passed" for r in res):
            st = "PROVEN"
        else:
            st = "NONE"
        out[rid] = {"status": st, "results": res}
    return out


# ---------------------------------------------------------------------------
# matrix enrichment (REQ-V2C-03): implementing commits, agent sessions, approvals
# ---------------------------------------------------------------------------

def commits_for_key(graph, key, exclude_sha=None):
    if not key:
        return []
    return [c for c in graph["commits"]
            if (key in c["tracker_keys"] or any(p.split("/")[0] == key or p.endswith("/" + key) for p in c["pairs"]))
            and not (exclude_sha and c["full_sha"].startswith(exclude_sha[:7]))]


def read_local_approval(root, key):
    """-> display string or None. Verifies plan_sha256 against the plan on disk."""
    if not key or "/" in key or ".." in key:
        return None
    p = root / ".evidence" / "changes" / key / "approval.json"
    if not p.exists():
        return None
    try:
        data = json.loads(read_text(p) or "")
    except json.JSONDecodeError:
        return f"INVALID approval.json ({rel_posix(root, p)})"
    if not isinstance(data, dict):
        return f"INVALID approval.json ({rel_posix(root, p)})"
    approver = data.get("approver") or "?"
    method = data.get("method") or "?"
    when = data.get("approved_at") or "?"
    label = f"{approver} ({method}, {when})"
    if data.get("key") and data.get("key") != key:
        return label + " [INVALID: key mismatch]"
    plan = data.get("plan_path")
    if plan:
        pp = root / plan
        if not pp.is_file():
            return label + " [STALE: plan missing]"
        if data.get("plan_sha256") and sha256_file(pp) != data.get("plan_sha256"):
            return label + " [STALE: plan changed since approval]"
    return label


def gh_argv():
    fake = os.environ.get("EVIDENCE_GH")
    if fake:
        return [fake]
    real = shutil.which("gh")
    return [real] if real else None


def run_gh(args, timeout=60):
    argv = gh_argv()
    if not argv:
        return None, "", "gh not found on PATH (set EVIDENCE_GH or install the GitHub CLI)"
    try:
        out = subprocess.run(argv + list(args), capture_output=True, text=True, timeout=timeout)
        return out.returncode, out.stdout, out.stderr
    except (OSError, subprocess.SubprocessError) as e:
        return None, "", str(e)


def github_approvals(key, cache):
    if key in cache:
        return cache[key]
    rc, out, _ = run_gh(["pr", "list", "--search", key, "--state", "all",
                         "--json", "number,title,reviews"])
    items = []
    if rc == 0:
        try:
            prs = json.loads(out or "[]")
        except json.JSONDecodeError:
            prs = []
        for pr in prs if isinstance(prs, list) else []:
            if key not in (pr.get("title") or ""):
                continue
            for rv in pr.get("reviews") or []:
                if (rv.get("state") or "").upper() == "APPROVED":
                    login = ((rv.get("author") or {}).get("login")) or "?"
                    item = f"github:{login} (PR #{pr.get('number')})"
                    if item not in items:
                        items.append(item)
    cache[key] = items
    return items


# ---------------------------------------------------------------------------
# scan
# ---------------------------------------------------------------------------

def resolve_repos(value):
    """--repos A,B (explicit participants) or --repos DIR (sibling repos under DIR).
    -> (repos, explicit)"""
    parts = [v.strip() for v in value.split(",") if v.strip()]
    if len(parts) > 1 or (parts and (Path(parts[0]) / ".git").exists()):
        repos = [Path(p).resolve() for p in parts]
        return [r for r in repos if (r / ".git").exists()], True
    base = Path(parts[0]) if parts else Path(".")
    if not base.exists():
        return [], False
    return sorted(c for c in base.iterdir() if c.is_dir() and (c / ".git").exists()), False


def find_sibling_repos(repos_dir):
    return resolve_repos(repos_dir)[0]


def parent_key(tracker_key):
    """PARENT/CHILD -> PARENT, per traceability-ids' cross-repo convention."""
    return tracker_key.split("/")[0] if tracker_key else tracker_key


def cmd_scan(root, args):
    if getattr(args, "repos", None):
        repos, _ = resolve_repos(args.repos)
        if not repos:
            print(f"No git repositories found for --repos {args.repos}.")
            return 0
        print("evidence scan --repos")
        print("=" * 60)
        graphs = {}
        for r in repos:
            adapter, _ = load_adapter(r)
            graphs[r.name] = build_graph(r, adapter, getattr(args, "results", None))
            g = graphs[r.name]
            print(f"[{r.name}] requirements={len(g['requirements'])} tests={len(g['tests'])} "
                  f"commits={len(g['commits'])} traceability_rows={len(g['traceability_rows'])}")
        print()
        by_parent = {}
        for name, g in graphs.items():
            for c in g["commits"]:
                for pair in c["pairs"]:
                    by_parent.setdefault(parent_key(pair), set()).add(name)
                for k in c["tracker_keys"]:
                    by_parent.setdefault(parent_key(k), set()).add(name)
        joined = {p: rs for p, rs in by_parent.items() if len(rs) > 1}
        print(f"Parent keys joining more than one repository: {len(joined)}")
        for p, rs in sorted(joined.items()):
            print(f"  {p}: {', '.join(sorted(rs))}")
        if not joined:
            print("  none -- no tracker key (or PARENT/CHILD pair) appeared in more than")
            print("  one repository's commit history")
        return 0

    adapter, adapter_path = load_adapter(root)
    graph = build_graph(root, adapter, getattr(args, "results", None))

    print("evidence scan")
    print("=" * 60)
    print(f"Repository: {root}")
    print(f"Adapter: {adapter_path if adapter else 'none found -- using built-in defaults for this framework' + chr(39) + 's own layout'}")
    if graph["ignore_patterns"]:
        print(f".evidenceignore: {', '.join(graph['ignore_patterns'])}")
    print()

    if graph["requirements_source"] == "tracker":
        print("Requirements live in an issue tracker per .evidence/adapter.yml")
        print("(requirements_source: tracker). This CLI cannot scan a tracker's API --")
        print("it can only report what's derivable locally. Export the tracker's")
        print("requirements to a local file and point spec_glob at it, or provide")
        print("validation/traceability.csv directly.")
        print()

    if not graph["requirements"] and not graph["traceability_rows"] and graph["requirements_source"] != "tracker":
        print("Nothing to trace: no requirement IDs found in any spec.md, and no")
        print("validation/traceability.csv exists yet. This is a clean report, not an")
        print("error -- either this repository has not run intent-capture/spec-and-design")
        print("yet, or its requirements live somewhere this scan does not know to look")
        print("(configure .evidence/adapter.yml).")
        return 0

    print(f"Requirements found: {len(graph['requirements'])}")
    for req_id, info in sorted(graph["requirements"].items()):
        print(f"  {req_id}  (spec: {info['spec_file']}, spec_commit: {info['spec_commit'] or '[NEEDS VERIFICATION]'})")
    print()

    print(f"Test files scanned: {len(graph['tests'])}")
    tagged = [t for t in graph["tests"] if t["req_ids"]]
    print(f"  of which carry a structural requirement tag: {len(tagged)}")
    for t in tagged:
        print(f"  {t['path']} -> {', '.join(sorted(t['req_ids']))}")
    if graph["skipped_files"]:
        print(f"  ({graph['skipped_files']} file(s) could not be read and were skipped, not silently treated as empty)")
    print()

    print(f"Ingested results: {len(graph['results'])} test result(s) from {graph['results_files']} file(s)")
    for bad in graph["results_unparseable"]:
        print(f"  UNPARSEABLE: {bad}")
    for m in graph["results_missing"]:
        print(f"  NOT FOUND: {m}")
    print()

    print(f"Commits scanned: {len(graph['commits'])}")
    keyed = [c for c in graph["commits"] if c["tracker_keys"]]
    print(f"  of which carry a tracker key: {len(keyed)}")
    print(f"  of which carry an Agent-Session/Claude-Session trailer: {sum(1 for c in graph['commits'] if c['sessions'])}")
    print()

    if graph.get("csv_malformed"):
        print("validation/traceability.csv: EXISTS BUT UNREADABLE -- header does not")
        print("  contain 'requirement_id'. Its rows were not counted. Run `evidence doctor`.")
    else:
        print(f"validation/traceability.csv rows: {len(graph['traceability_rows'])}")
        if not graph["traceability_rows"]:
            print("  none -- run `evidence export` once requirements have evidence to cite")
    return 0


# ---------------------------------------------------------------------------
# gaps
# ---------------------------------------------------------------------------

def csv_row_corroborated(root, row):
    """A traceability.csv row naming a requirement and a test_case_id is only
    coverage if automated_test names at least one existing file whose content
    contains the test_case_id or the requirement_id verbatim. (This is the
    manual/legacy path; it never makes a requirement PROVEN -- only an ingested
    result does.)"""
    test_case_id = (row.get("test_case_id") or "").strip()
    rid = (row.get("requirement_id") or "").strip()
    automated_test = (row.get("automated_test") or "").strip()
    if not test_case_id or not rid or not automated_test:
        return False
    for rel in (p.strip() for p in automated_test.split(",")):
        if not rel:
            continue
        p = root / rel
        if not p.is_file():
            continue
        text = read_text(p)
        if text is None:
            continue
        if test_case_id in text or rid in text:
            return True
    return False


def covered_ids(root, graph):
    structural = set()
    for t in graph["tests"]:
        structural |= t["req_ids"]
    covered = set(structural)
    for row in graph["traceability_rows"]:
        rid = row.get("requirement_id")
        if rid and row.get("test_case_id") and csv_row_corroborated(root, row):
            covered.add(rid)
    return structural, covered


def compute_gaps(root, graph):
    structural_covered, covered_req_ids = covered_ids(root, graph)
    status = requirement_status(graph)

    csv_claims = {}
    for row in graph["traceability_rows"]:
        rid = row.get("requirement_id")
        if rid and row.get("test_case_id"):
            csv_claims[rid] = row

    no_coverage = []
    for rid in sorted(set(graph["requirements"]) - covered_req_ids):
        if rid in csv_claims:
            row = csv_claims[rid]
            no_coverage.append(
                f"{rid} (validation/traceability.csv claims test_case_id="
                f"'{row.get('test_case_id')}' in automated_test='{row.get('automated_test') or '(empty)'}', "
                f"but that claim could not be independently verified against the "
                f"named file's actual content -- treated as uncovered, not assumed correct)"
            )
        else:
            no_coverage.append(rid)

    failed = []
    for rid in sorted(covered_req_ids):
        st = status.get(rid)
        if st and st["status"] == "FAILED":
            srcs = sorted({f"{r['name']} [{r['source']}]" for r in st["results"] if r["status"] == "failed"})
            failed.append(f"{rid}: ingested result FAILED -- {'; '.join(srcs)}")

    proven = sorted(rid for rid in covered_req_ids if status.get(rid, {}).get("status") == "PROVEN")

    self_asserted, unproven = [], []
    result_recorded_for = set()
    for row in graph["traceability_rows"]:
        rid = row.get("requirement_id") or "?"
        result = (row.get("result") or "").strip()
        if result:
            result_recorded_for.add(rid)
        st = status.get(rid, {}).get("status", "NONE")
        if st in ("PROVEN", "FAILED"):
            continue
        if result.upper().startswith("PASS"):
            self_asserted.append(
                f"{rid}: result='{result}' in validation/traceability.csv, but no ingested "
                f"test result corroborates it")
        else:
            unproven.append(f"{rid}: result={result or '(none)'}")

    unverified_result = sorted(
        rid for rid in covered_req_ids
        if status.get(rid, {}).get("status", "NONE") == "NONE" and rid not in result_recorded_for
    )

    known_req_ids = set(graph["requirements"])
    orphaned = sorted({
        f"{t['path']} -> {rid}"
        for t in graph["tests"] for rid in t["req_ids"] if rid not in known_req_ids
    })

    untraced = [c["sha"] + " " + c["subject"] for c in graph["commits"] if not c["tracker_keys"]]

    duplicate_ids = []
    for rid, files in sorted(graph.get("duplicate_requirements", {}).items()):
        seen = []
        for f in files:
            if f not in seen:
                seen.append(f)
        if len(seen) > 1:
            duplicate_ids.append(
                f"{rid}: defined in {', '.join(seen)} -- only {seen[0]}'s summary was kept as canonical")
        else:
            duplicate_ids.append(
                f"{rid}: appears {len(files)} times within {seen[0]} -- likely a copy-paste error")

    return {
        "NO COVERAGE": no_coverage,
        "FAILED": failed,
        "MISSING-CHILD": [],
        "SELF-ASSERTED": self_asserted,
        "UNPROVEN": unproven,
        "UNVERIFIED-RESULT": unverified_result,
        "ORPHANED": orphaned,
        "UNTRACED": untraced,
        "DUPLICATE-ID": duplicate_ids,
        "_PROVEN": proven,
    }


def _print_gaps(label_prefix, gaps, strict=False, skip_empty_missing_child=True):
    """Print every category; return the list of categories that block."""
    blocking_set = STRICT_BLOCKING if strict else BLOCKING
    blockers = []
    proven = gaps.get("_PROVEN", [])
    print(f"{label_prefix}PROVEN ({len(proven)}) -- covered, and a covering test passed in an ingested result")
    print("  " + (", ".join(proven) if proven else "none"))
    print()
    for label in GAP_CATEGORIES:
        if label == "MISSING-CHILD" and skip_empty_missing_child and not gaps[label]:
            continue
        items = gaps[label]
        tag = " [blocking]" if label in blocking_set else ""
        print(f"{label_prefix}{label} ({len(items)}){tag}")
        if not items:
            print("  none")
        else:
            for i in items[:50]:
                print(f"  - {i}")
            if len(items) > 50:
                print(f"  ... and {len(items) - 50} more")
        print()
        if label in blocking_set and items:
            blockers.append(label)
    return blockers


def assessment_basis_line(root, graph):
    req_source = (
        "an issue tracker (unavailable locally, per requirements_source: tracker)"
        if graph["requirements_source"] == "tracker"
        else f"{graph['spec_files_scanned']} spec file(s)"
    )
    basis = (
        f"Assessment basis: {len(graph['requirements'])} requirements from {req_source}, "
        f"{len(graph['tests'])} tests parsed from {graph['test_source_desc'] or 'test-location conventions'}, "
        f"{graph['skipped_files']} unparseable file(s) skipped, "
        f"{len(graph['results'])} ingested test result(s) from {graph['results_files']} results file(s)"
        + (f" ({len(graph['results_unparseable'])} results file(s) unparseable)" if graph["results_unparseable"] else "")
        + "."
    )
    if graph["results_missing"]:
        basis += f" WARNING: results location(s) not found: {', '.join(graph['results_missing'])}."
    if graph.get("csv_malformed"):
        basis += (
            " WARNING: validation/traceability.csv exists but its header does "
            "not contain 'requirement_id' -- its rows were NOT read (treated "
            "as unreadable, not as zero rows). Run `evidence doctor` for detail."
        )
    return basis


def missing_child_gaps(graphs, explicit, only_parent=None):
    """REQ-V2X-02: every PARENT seen in a PARENT/CHILD pair must have a child
    chain (a commit carrying PARENT/<CHILD>) in every participating repo."""
    if not explicit:
        return []
    chains = {}  # parent -> {repo: set(children)}
    plain = {}   # parent -> set(repo) where the parent appears without a child
    for name, g in graphs.items():
        for c in g["commits"]:
            for pair in c["pairs"]:
                p, _, child = pair.partition("/")
                chains.setdefault(p, {}).setdefault(name, set()).add(child)
    for name, g in graphs.items():
        for c in g["commits"]:
            for k in c["tracker_keys"]:
                if k in chains:
                    plain.setdefault(k, set()).add(name)
    out = []
    for p in sorted(chains):
        if only_parent and p != only_parent:
            continue
        for name in graphs:
            if name in chains[p]:
                continue
            have = "; ".join(f"{n}: {', '.join(sorted(ch))}" for n, ch in sorted(chains[p].items()))
            note = " (parent key present, but no PARENT/CHILD pair)" if name in plain.get(p, set()) else ""
            out.append(f"{p}: no child chain in {name}{note} -- child chains seen: {have}")
    return out


def cmd_gaps(root, args):
    strict = getattr(args, "strict", False)
    results_paths = getattr(args, "results", None)
    if getattr(args, "repos", None):
        repos, explicit = resolve_repos(args.repos)
        if not repos:
            print(f"No git repositories found for --repos {args.repos}.")
            return 0
        print("evidence gaps --repos")
        print("=" * 60)
        graphs, roots_by_name, blockers = {}, {}, []
        for r in repos:
            adapter, _ = load_adapter(r)
            graphs[r.name] = build_graph(r, adapter, results_paths)
            roots_by_name[r.name] = r
            print(f"--- {r.name} ---")
            print(assessment_basis_line(r, graphs[r.name]))
            print()
            blockers += _print_gaps("", compute_gaps(r, graphs[r.name]), strict)

        req_repos = {}
        for name, g in graphs.items():
            _, covered = covered_ids(roots_by_name[name], g)
            referenced = set(g["requirements"]) | {
                row.get("requirement_id") for row in g["traceability_rows"] if row.get("requirement_id")}
            for rid in referenced:
                req_repos.setdefault(rid, {})[name] = rid in covered
        cross_repo_gaps = []
        for rid, per_repo in sorted(req_repos.items()):
            if len(per_repo) < 2:
                continue
            covered_in = sorted(n for n, ok in per_repo.items() if ok)
            missing_in = sorted(n for n, ok in per_repo.items() if not ok)
            if covered_in and missing_in:
                cross_repo_gaps.append(f"{rid}: covered in {', '.join(covered_in)}; NOT covered in {', '.join(missing_in)}")

        print("--- CROSS-REPO COVERAGE GAPS ---")
        print(f"({len(cross_repo_gaps)})")
        print("  none" if not cross_repo_gaps else "\n".join(f"  - {i}" for i in cross_repo_gaps))
        print()
        mc = missing_child_gaps(graphs, explicit, getattr(args, "parent", None))
        print(f"--- MISSING-CHILD ({len(mc)}) [blocking] ---")
        if not explicit:
            print("  not assessed -- list the participating repositories explicitly (--repos A,B)")
        else:
            print("  none" if not mc else "\n".join(f"  - {i}" for i in mc))
        print()
        if blockers or cross_repo_gaps or mc:
            print("RESULT: blocking gap(s) exist across the participating repositories.")
            return 1
        print("RESULT: no blocking gaps.")
        return 0

    adapter, _ = load_adapter(root)
    graph = build_graph(root, adapter, results_paths)

    print("evidence gaps")
    print("=" * 60)

    all_known_reqs = set(graph["requirements"]) | {
        row.get("requirement_id") for row in graph["traceability_rows"] if row.get("requirement_id")
    }
    if not all_known_reqs:
        print("No requirements found.")
        print(f"Scanned: {graph['spec_files_scanned']} spec file(s), {len(graph['commits'])} commits, "
              f"{len(graph['tests'])} test files.")
        print("Nothing to assess -- this is not a coverage result.")
        print("If this repository should have requirement IDs, check .evidence/adapter.yml.")
        return 2

    print(assessment_basis_line(root, graph))
    print()
    gaps = compute_gaps(root, graph)
    blockers = _print_gaps("", gaps, strict)

    if blockers:
        print(f"RESULT: blocking gap(s): {', '.join(blockers)}"
              + (" (--strict)" if strict else "") + " -- this must block a release gate.")
        return 1
    print("RESULT: no blocking gaps" + (" (--strict: every requirement PROVEN)." if strict else
                                        " (no NO COVERAGE / FAILED items)."))
    return 0


# ---------------------------------------------------------------------------
# export (REQ-V2C-03, REQ-V2C-06, REQ-V2O-04) -- merge, never rewrite
# ---------------------------------------------------------------------------

LIST_COLUMNS = {"automated_test": ", ", "implementing_commits": " ",
                "agent_sessions": "; ", "approved_by": "; "}
SOFT_DERIVED = {"see automated_test / spec_commit"}


def _split(col, value):
    sep = LIST_COLUMNS[col].strip()
    return [x.strip() for x in value.split(sep) if x.strip()] if sep else value.split()


def merge_cell(row, col, derived, rid, conflicts):
    """Fill empty cells; union list columns; NEVER overwrite a non-empty scalar
    cell -- a differing derived value is recorded as a conflict instead."""
    derived = (derived or "").strip()
    existing = (row.get(col) or "").strip()
    if not derived:
        return
    if not existing:
        row[col] = derived
        return
    if col in LIST_COLUMNS:
        items = _split(col, existing)
        for d in _split(col, derived):
            if col == "implementing_commits":
                if any(d.startswith(e) or e.startswith(d) for e in items):
                    continue
            elif d in items:
                continue
            items.append(d)
        row[col] = LIST_COLUMNS[col].join(items)
        return
    if col == "spec_commit" and (existing.startswith(derived) or derived.startswith(existing)):
        return  # same commit, abbreviated differently
    if existing != derived and derived not in SOFT_DERIVED:
        conflicts.append((rid, col, existing, derived))


def derive_row(root, graph, req_id, info, status, gh_cache, use_github):
    d = {"requirement_id": req_id, "requirement_summary": info["summary"],
         "spec_commit": info["spec_commit"] or "", "tracker_key": info["tracker_key"] or ""}
    matching = [t for t in graph["tests"] if req_id in t["req_ids"]]
    if matching:
        d["automated_test"] = ", ".join(sorted(t["path"] for t in matching))
    key = info["tracker_key"]
    commits = commits_for_key(graph, key, exclude_sha=info["spec_commit"])
    d["implementing_commits"] = " ".join(c["sha"] for c in reversed(commits))
    sessions = []
    for c in reversed(commits):
        for s in c["sessions"]:
            if s not in sessions:
                sessions.append(s)
    d["agent_sessions"] = "; ".join(sessions)
    approvals = []
    local = read_local_approval(root, key)
    if local:
        approvals.append(local)
    if use_github and key:
        approvals += github_approvals(key, gh_cache)
    d["approved_by"] = "; ".join(approvals)
    st = status.get(req_id, {"status": "NONE", "results": []})
    if st["status"] in ("PROVEN", "FAILED"):
        want = "failed" if st["status"] == "FAILED" else "passed"
        rs = [r for r in st["results"] if r["status"] == want]
        d["result"] = ("FAIL" if want == "failed" else "PASS") + f" (ingested: {len(rs)} result(s))"
        d["test_run_id"] = ", ".join(sorted({r["run_id"] for r in rs}))
        d["evidence_link"] = ", ".join(sorted({r["source"] for r in rs}))
    return d, bool(matching)


def cmd_export(root, args):
    adapter, _ = load_adapter(root)
    graph = build_graph(root, adapter, getattr(args, "results", None))

    existing, order = {}, []
    csv_path = root / "validation" / "traceability.csv"
    existing_csv_malformed = False
    extra_cols = []
    if csv_path.exists():
        reader = csv.DictReader(io.StringIO(read_text(csv_path) or ""))
        if csv_header_ok(reader.fieldnames):
            extra_cols = [c for c in reader.fieldnames if c and c not in CSV_COLUMNS]
            for i, row in enumerate(reader):
                rid = row.get("requirement_id") or f"__row{i}"
                if rid in existing:  # never drop a duplicate row
                    rid = f"{rid}__dup{i}"
                existing[rid] = row
                order.append(rid)
        else:
            existing_csv_malformed = True

    if existing_csv_malformed:
        print(f"WARNING: {csv_path.relative_to(root)} exists but its header does not "
              "contain 'requirement_id' -- treating it as unreadable, not as zero "
              "existing rows.", file=sys.stderr)
        if args.write or getattr(args, "conflicts_only", False):
            print("Refusing to write: overwriting it now would silently destroy "
                  "whatever it currently holds and could not be verified. Fix the "
                  "header by hand, or move the file aside and re-run this command "
                  "to regenerate it from scratch.", file=sys.stderr)
            return 1

    status = requirement_status(graph)
    conflicts, appended = [], 0
    gh_cache = {}
    use_github = getattr(args, "github", False)
    for req_id, info in graph["requirements"].items():
        is_new = req_id not in existing
        row = existing.get(req_id) or {col: "" for col in CSV_COLUMNS}
        derived, structural = derive_row(root, graph, req_id, info, status, gh_cache, use_github)
        covered = structural or csv_row_corroborated(root, row)
        if not covered:
            reason = "NO COVERAGE"
            if (row.get("test_case_id") or "").strip():
                reason = (f"NO COVERAGE (test_case_id '{row['test_case_id']}' in "
                          f"automated_test '{row.get('automated_test') or '(empty)'}' could not be "
                          f"independently verified)")
            derived["evidence_link"] = reason
        elif "evidence_link" not in derived:
            derived["evidence_link"] = "see automated_test / spec_commit"
        row["requirement_id"] = req_id
        for col in CSV_COLUMNS:
            if col == "requirement_id":
                continue
            merge_cell(row, col, derived.get(col, ""), req_id, conflicts)
        existing[req_id] = row
        if is_new:
            order.append(req_id)
            appended += 1

    rows = [existing[rid] for rid in order]
    columns = CSV_COLUMNS + extra_cols

    if getattr(args, "conflicts_only", False):
        print_conflicts(conflicts, sys.stdout)
        return 1 if conflicts else 0

    basis = assessment_basis_line(root, graph)
    fmt = args.format
    if fmt == "csv":
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") or "" for col in columns})
        output = buf.getvalue()
        print(basis, file=sys.stderr)
    else:
        lines = [basis, "", "| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
        for row in rows:
            lines.append("| " + " | ".join((row.get(col, "") or "").replace("|", "/") for col in columns) + " |")
        output = "\n".join(lines) + "\n"

    if args.write:
        out_path = root / "validation" / f"traceability.{'csv' if fmt == 'csv' else 'md'}"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
        print(f"Wrote {out_path.relative_to(root)} ({len(rows)} rows: {appended} appended, "
              f"{len(rows) - appended} kept; no row deleted, no non-empty cell overwritten).")
        print_conflicts(conflicts, sys.stdout)
    else:
        sys.stdout.write(output)
        if conflicts:
            print_conflicts(conflicts, sys.stderr)
    return 0


def print_conflicts(conflicts, stream):
    print(f"CONFLICTS ({len(conflicts)}) -- existing value kept; derived value differs:", file=stream)
    if not conflicts:
        print("  none", file=stream)
    for rid, col, old, new in conflicts:
        print(f"  - {rid} {col}: kept '{old}' (derived '{new}')", file=stream)


# ---------------------------------------------------------------------------
# tracker (REQ-V2C-10) -- GitHub Issues via `gh`. Jira: see cli/README.md.
# ---------------------------------------------------------------------------

def tracker_issue_number(adapter, key):
    kind = (adapter_get(adapter, "tracker", "") or "").lower()
    if kind != "github":
        return None, (f"tracker is '{kind or 'unset'}' in .evidence/adapter.yml -- only `tracker: github` "
                      f"is implemented; see cli/README.md for the Jira REST template")
    rx = adapter_get(adapter, "tracker_key_to_issue", r"^(?:GH-|#)?(\d+)$")
    try:
        m = re.search(rx, key)
    except re.error as e:
        return None, f"tracker_key_to_issue is not a valid regex: {e}"
    if not m:
        return None, f"key '{key}' does not match tracker_key_to_issue '{rx}'"
    num = m.group(1) if m.groups() else m.group(0)
    if not num.isdigit():
        return None, f"tracker_key_to_issue captured '{num}', not an issue number"
    return num, None


def cmd_tracker(root, args):
    adapter, _ = load_adapter(root)
    num, err = tracker_issue_number(adapter, args.key)
    if err:
        print(f"evidence tracker: {err}", file=sys.stderr)
        return 2
    if args.tracker_command == "check":
        rc, out, errtxt = run_gh(["issue", "view", num, "--json", "number,title,state,url"])
        if rc is None:
            print(f"evidence tracker: {errtxt}", file=sys.stderr)
            return 2
        if rc != 0:
            print(f"NOT FOUND: {args.key} -> issue #{num} ({errtxt.strip() or 'gh exit ' + str(rc)})")
            return 1
        try:
            data = json.loads(out or "{}")
        except json.JSONDecodeError:
            data = {}
        print(f"FOUND: {args.key} -> issue #{data.get('number', num)} "
              f"[{data.get('state', '?')}] {data.get('title', '')} {data.get('url', '')}".rstrip())
        return 0
    if args.tracker_command == "link":
        body = f"Evidence link ({args.key}): {args.target}"
        rc, out, errtxt = run_gh(["issue", "comment", num, "--body", body])
        if rc is None:
            print(f"evidence tracker: {errtxt}", file=sys.stderr)
            return 2
        if rc != 0:
            print(f"FAILED to link {args.key} -> issue #{num}: {errtxt.strip()}")
            return 1
        print(f"LINKED: {args.key} -> issue #{num}: {args.target}")
        if out.strip():
            print(out.strip())
        return 0
    return 2


# ---------------------------------------------------------------------------
# main -- each subcommand registers itself; add new ones to SUBCOMMANDS.
# ---------------------------------------------------------------------------

def _add_results_arg(p):
    p.add_argument("--results", metavar="PATH", action="append", default=[],
                   help="JUnit XML / `claude plugin eval` aggregate-result.json file or directory "
                        "to ingest, in addition to test_results_location (repeatable)")


def register_doctor(sub):
    p = sub.add_parser("doctor", help="preflight checks for this repository's gate environment")
    p.add_argument("--strict", action="store_true", help="exit 1 on any WARN, not only on FAIL")
    p.set_defaults(func=cmd_doctor)


def register_scan(sub):
    p = sub.add_parser("scan", help="build and report the traceability graph")
    p.add_argument("--repos", metavar="A,B|DIR",
                   help="comma-separated participating repos, or a directory of sibling repos")
    _add_results_arg(p)
    p.set_defaults(func=cmd_scan)


def register_gaps(sub):
    p = sub.add_parser("gaps", help="report gaps; exit 1 on a blocking category")
    p.add_argument("--repos", metavar="A,B|DIR",
                   help="comma-separated participating repos (checks PARENT/CHILD chains -> MISSING-CHILD), "
                        "or a directory of sibling repos (cross-repo coverage only)")
    p.add_argument("--parent", metavar="KEY", help="with --repos: only check this parent key's child chains")
    p.add_argument("--strict", action="store_true",
                   help="also block on SELF-ASSERTED, UNPROVEN, UNVERIFIED-RESULT and DUPLICATE-ID")
    _add_results_arg(p)
    p.set_defaults(func=cmd_gaps)


def register_export(sub):
    p = sub.add_parser("export", help="merge-write the traceability matrix (never overwrites a filled cell)")
    p.add_argument("--format", choices=["csv", "md"], default="csv")
    p.add_argument("--write", action="store_true",
                   help="write to validation/traceability.<ext> instead of stdout")
    p.add_argument("--conflicts-only", action="store_true",
                   help="print only cells where the existing value differs from the derived one; exit 1 if any")
    p.add_argument("--github", action="store_true",
                   help="also read PR review approvals via `gh` for approved_by")
    _add_results_arg(p)
    p.set_defaults(func=cmd_export)


def register_tracker(sub):
    p = sub.add_parser("tracker", help="check a tracker key / write back a link (GitHub Issues via gh)")
    tsub = p.add_subparsers(dest="tracker_command", required=True)
    c = tsub.add_parser("check", help="verify the key's issue exists")
    c.add_argument("key")
    l = tsub.add_parser("link", help="comment a link or text on the key's issue")
    l.add_argument("key")
    l.add_argument("target", help="URL or text to write back")
    p.set_defaults(func=cmd_tracker)


SUBCOMMANDS = [register_doctor, register_scan, register_gaps, register_export, register_tracker]


def build_parser():
    parser = argparse.ArgumentParser(prog="evidence", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for register in SUBCOMMANDS:
        register(sub)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(find_repo_root(), args)


if __name__ == "__main__":
    sys.exit(main())
