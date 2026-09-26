#!/usr/bin/env python3
"""Content presence and function checks for requirements whose deliverable is content: skills, templates,
agents, governance, docs, product metadata. Each check tests the acceptance criterion
written in its spec row, not merely that a file exists; several are functional (they
run the sensor, the plan-rows check, the CLI or the version-bump script).

    python3 tests/content_acceptance_tests.py            # JUNIT_OUT=path.xml for a JUnit report
"""
import glob
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
P = lambda *a: os.path.join(ROOT, *a)  # noqa: E731
sys.path.insert(0, P("plugins", "evidence-sdlc", "scripts", "engine"))
res = []


def read(*a):
    try:
        return open(P(*a), encoding="utf-8").read()
    except OSError:
        return ""


def check(label, ok, detail=""):
    res.append((label, bool(ok), "" if ok else str(detail)[:400]))
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else f" :: {detail}"))


def frontmatter(path):
    t = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n", t, re.S)
    if not m:
        return None
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    return fm


def skill(p, n):
    return read("plugins", p, "skills", n, "SKILL.md")


# ------------------------------------------------------------ PILOT-50
rt = skill("evidence-sdlc", "risk-tiering")
check("REQ-DEBT-01 risk-tiering asks about technical debt before 'When in doubt, tier up'",
      "debt" in rt.lower() and rt.lower().find("debt") < rt.lower().find("when in doubt"))
check("REQ-DEBT-02 debt signals are concrete and already available",
      all(w in rt.lower() for w in ("workaround", "incident", "coverage")))
check("REQ-DEBT-03 debt raises the tier one notch, never lowers it, capped at Tier 3",
      re.search(r"raise", rt, re.I) and re.search(r"never lower|never weaken|only raise", rt, re.I) and "3" in rt)
check("REQ-CKPT-01 plan template has a Mid-flight checkpoint section for Tier 2/3",
      "## Mid-flight checkpoint" in read("plugins", "evidence-sdlc", "templates", "plan.md"))
check("REQ-CKPT-02 planning skill stops at the CHECKPOINT step and re-validates against spec",
      re.search(r"CHECKPOINT.*spec", skill("evidence-sdlc", "codebase-grounded-planning"), re.S))
import sensor  # noqa: E402
with tempfile.TemporaryDirectory() as d:
    os.makedirs(os.path.join(d, "plan"))
    pp = os.path.join(d, "plan", "X-1.md")
    open(pp, "w").write("# Plan\nTracker: X-1\nRisk tier: 2\n\n## Files claimed\n- `src/**`\n\n## Order of work\n1. do it\n")
    note = sensor.check(pp, d) or ""
    check("REQ-CKPT-03 sensor flags a Tier 2 plan with no CHECKPOINT step (advisory)", "CHECKPOINT" in note, note)
    open(pp, "a").write("2. CHECKPOINT: re-check against spec\n")
    check("REQ-CKPT-03 sensor is silent once the CHECKPOINT marker exists", sensor.check(pp, d) is None)
    os.makedirs(os.path.join(d, "plugins", "p", "skills", "newskill"))
    sp = os.path.join(d, "plugins", "p", "skills", "newskill", "SKILL.md")
    open(sp, "w").write("---\nname: newskill\ndescription: x\n---\n")
    check("REQ-EVAL-02 sensor flags a new SKILL.md with no eval case", "no eval case" in (sensor.check(sp, d) or ""))
dod = read("plugins", "evidence-sdlc", "templates", "definition-of-ready-and-done.md")
check("REQ-EVAL-01 DoD requires an eval case when a new skill is introduced",
      "Eval case added under `evals/`" in dod and "evals/" in read("docs", "extending.md"))

# ------------------------------------------------------------ PILOT-51
tsd = skill("evidence-discovery", "test-strategy-discovery")
check("REQ-TSD-01 test-strategy-discovery reads the repository before asking, then asks one batch",
      re.search(r"read before asking", tsd, re.I) and re.search(r"one numbered batch", tsd, re.I))
tpl = read("plugins", "evidence-discovery", "templates", "test-strategy.md")
check("REQ-TSD-02 test-strategy profile template covers scope, targets, environments, matrix, owners, criteria",
      all(h in tpl for h in ("## Test types in scope", "## Non-functional targets", "## Environments",
                             "## Browser and device matrix", "## Entry and exit criteria")) and "[ASK]" in tpl)
check("REQ-TSD-03 nothing is out of scope without a reason and a named decider",
      re.search(r"out of scope silently", tsd, re.I) and "decider" in tsd.lower())
check("REQ-TSD-04 test-strategy and continuous-testing read test-strategy.md",
      "test-strategy.md" in skill("evidence-quality", "test-strategy") and "test-strategy.md" in skill("evidence-quality", "continuous-testing"))
check("REQ-TSD-05 SessionStart profile message names test-strategy.md",
      "test-strategy.md" in read("plugins", "evidence-discovery", "scripts", "require-repo-profile.sh"))
perf = skill("evidence-quality", "performance-testing")
check("REQ-PERF-01 performance-testing covers load, stress, soak, spike and capacity",
      all(w in perf.lower() for w in ("load", "stress", "soak", "spike", "capacity")))
check("REQ-PERF-02 no numeric target in the spec means no test (spec defect, never invented)",
      re.search(r"no target, no test", perf, re.I) and re.search(r"spec defect", perf, re.I))
check("REQ-PERF-03 workload model, baseline, parity gap, thresholds fixed before run, percentiles not averages",
      all(re.search(w, perf, re.I) for w in ("workload model", "baseline", "parity", "before the run", "percentile", "coordinated omission")))
sec = skill("evidence-quality", "security-testing")
check("REQ-SEC-01 security-testing covers SCA, secrets, container/IaC, DAST, fuzzing, pen testing",
      all(re.search(w, sec, re.I) for w in ("SCA|dependency", "secret", "container", "IaC", "DAST", "fuzz", "penetration|pen test")))
check("REQ-SEC-02 suppressions need reason, owner, approver and expiry; baseline vs new",
      all(re.search(w, sec, re.I) for w in ("owner", "approver", "expiry", "baseline")))
check("REQ-SEC-03 active scanning only against profile-named non-production targets",
      re.search(r"production", sec, re.I) and re.search(r"profile", sec, re.I) and re.search(r"written authoris", sec, re.I))
sa = skill("evidence-quality", "static-analysis")
check("REQ-SA-01 static-analysis covers lint, format, type checks, complexity, SAST",
      all(re.search(w, sa, re.I) for w in ("lint", "format", "type check", "complexity", "SAST")))
check("REQ-SA-02 baseline and ratchet; no rule disabled to pass; rule changes are their own change",
      re.search(r"ratchet", sa, re.I) and re.search(r"separate|own change", sa, re.I))
e2e = skill("evidence-quality", "e2e-ui-testing")
check("REQ-E2E-01 e2e-ui-testing covers journeys, locators, waits, data, artifacts, sharding, cross-browser, visual, locale",
      all(re.search(w, e2e, re.I) for w in ("journey", "locator", "wait", "test data|auth", "shard", "cross-browser|browser", "visual", "locali")))
refs = [os.path.basename(x) for x in glob.glob(P("plugins", "evidence-quality", "skills", "e2e-ui-testing", "references", "*.md"))]
check("REQ-E2E-02 Playwright/Selenium/Cypress references, loaded only when the profile names the tool",
      {"playwright.md", "selenium.md", "cypress.md"} <= set(refs) and re.search(r"only (if|when) the profile", e2e, re.I), refs)
a11y = skill("evidence-quality", "accessibility-testing")
check("REQ-A11Y-01 conformance target from profile; automated scans are not enough; manual checks required",
      re.search(r"not sufficient|necessary, not sufficient", a11y, re.I) and all(w in a11y.lower() for w in ("keyboard", "screen reader", "zoom", "contrast")))
ts = skill("evidence-quality", "test-strategy")
check("REQ-COV-01 functional (requirement) coverage is named and uncovered IDs are listed",
      re.search(r"functional.*coverage", ts, re.I | re.S) and re.search(r"uncovered", ts, re.I))
ta = skill("evidence-quality", "test-automation")
check("REQ-FLK-01 flake detection records flaky, never passed; merge gate keeps retries off",
      re.search(r"flaky", ta, re.I) and re.search(r"never (as )?pass", ta, re.I))
check("REQ-TSR-01 test summary report template with a human-signed go/no-go",
      re.search(r"Go / No-go", read("plugins", "evidence-quality", "templates", "test-summary-report.md")))
check("REQ-TSR-02 test-plan section has entry criteria and a non-functional table",
      "Entry criteria" in read("plugins", "evidence-quality", "templates", "test-plan-section.md")
      and "Non-functional" in read("plugins", "evidence-quality", "templates", "test-plan-section.md"))
check("REQ-INT-01 test-strategy routes each test type to its owning skill",
      all(s in ts for s in ("performance-testing", "security-testing", "static-analysis", "e2e-ui-testing", "accessibility-testing")))
check("REQ-DOC-01 docs and metadata list the testing skills",
      "e2e-ui-testing" in read("docs", "skills-reference.md") and "performance" in read("plugins", "evidence-quality", ".claude-plugin", "plugin.json"))
new_cases = [d for d in glob.glob(P("plugins", "*", "evals", "*")) if re.search(
    r"/(test-strategy-discovery|performance-testing|security-testing|static-analysis|e2e-ui-testing|accessibility-testing)-", d)]
check("REQ-TEVAL-01 each PILOT-51 skill has trigger, non-trigger and behavior eval cases",
      len(new_cases) >= 18 and all(os.path.isfile(os.path.join(d, "prompt.md")) for d in new_cases), len(new_cases))

# ------------------------------------------------------------ PILOT-53 content
agents = {os.path.basename(a)[:-3] for a in glob.glob(P("plugins", "evidence-sdlc", "agents", "*.md"))}
check("REQ-V2R-01 architect, code-reviewer, release-manager and docs-writer agents exist",
      {"architect", "code-reviewer", "release-manager", "docs-writer"} <= agents, agents)
ver = read("plugins", "evidence-sdlc", "agents", "verifier.md")
check("REQ-V2R-02 verifier not pinned to haiku; no stale 'other five agents' references",
      "model: haiku" not in ver and not any("other five agents" in read("plugins", "evidence-sdlc", "agents", a + ".md") for a in agents))
check("REQ-V2D-01 ADR template and .evidence/decisions/ referenced by spec-and-design and DoD",
      os.path.isfile(P("plugins", "evidence-sdlc", "templates", "adr.md")) and ".evidence/decisions" in skill("evidence-sdlc", "spec-and-design")
      and ".evidence/decisions" in dod)
rr = skill("evidence-sdlc", "release-readiness")
check("REQ-V2D-02 release-readiness drafts, never signs, never supplies RELEASE_APPROVAL",
      rr and re.search(r"never sign|not sign", rr, re.I) and "RELEASE_APPROVAL" in rr)
tier_forms = [f for f in glob.glob(P("plugins", "*", "skills", "*", "SKILL.md")) + glob.glob(P("plugins", "*", "templates", "*.md"))
              if re.search(r"Risk classification:", read(os.path.relpath(f, ROOT)))]
check("REQ-V2D-03 one tier notation ('Risk tier:'); no 'Risk classification:' left", not tier_forms, tier_forms)
check("REQ-V2D-04 Part 11 / QA/RA wording in risk-tiering and DoD reads from compliance.md",
      "compliance.md" in rt and "compliance.md" in dod and not re.search(r"QA/RA sign-off", rt))
rca = skill("evidence-sdlc", "root-cause-analysis")
check("REQ-V2D-05 RCA has git history/bisect, causal chain, sibling sweep and state-based fix mode",
      all(re.search(w, rca, re.I) for w in ("bisect", "causal|mechanism", "sibling", "change start .*--kind fix", "failing-test")))
descs = {}
for f in glob.glob(P("plugins", "*", "skills", "*", "SKILL.md")):
    fm = frontmatter(f)
    descs[f] = len((fm or {}).get("description", "")) if fm else 10 ** 6
check("REQ-V2D-06 every skill description parses and is 500 characters or fewer",
      all(v <= 500 for v in descs.values()), {os.path.relpath(k, ROOT): v for k, v in descs.items() if v > 500})
check("REQ-V2D-06 'design the schema' trigger belongs to one skill only",
      sum("design the schema" in (frontmatter(f) or {}).get("description", "") for f in descs) <= 1)
check("REQ-V2D-07 contract-testing names tool options chosen from the profile; legacy ranks by churn",
      re.search(r"Pact", skill("evidence-integrations", "contract-testing")) and re.search(r"git log", skill("evidence-sdlc", "legacy-characterization")))
with tempfile.TemporaryDirectory() as d:
    subprocess.run(["git", "init", "-q"], cwd=d)
    for k, body in (("A-1", "| REQ-A-01 | x | unit | Yes | — | test_a | report |\n"), ("B-2", "| REQ-B-01 | no proof |\n")):
        os.makedirs(os.path.join(d, ".evidence", "changes", k))
        json.dump({"key": k, "tier": 1, "stage": "plan", "plan": f"plan/{k}.md"}, open(os.path.join(d, ".evidence", "changes", k, "state.json"), "w"))
        os.makedirs(os.path.join(d, "plan"), exist_ok=True)
        open(os.path.join(d, "plan", f"{k}.md"), "w").write(body)
    out = subprocess.run([sys.executable, P("plugins", "evidence-quality", "scripts", "check-test-plan-rows.py")],
                         input="{}", cwd=d, capture_output=True, text=True).stdout
    check("REQ-V2D-08 plan-rows check reads every active change's plan, not just the first", "REQ-B-01" in out and "REQ-A-01" not in out, out)
check("REQ-V2D-10 stale statements corrected (no 'blocks source edits' claim in require-repo-profile; eval README counts)",
      "blocks source edits only" not in read("plugins", "evidence-discovery", "scripts", "require-repo-profile.sh"))
sar = skill("evidence-sdlc", "secure-api-review")
check("REQ-V2K-04 secure-api-review covers OWASP API1..API10 (2023) and reads org specifics from the profile",
      all(re.search(rf"API{i}\b", sar) for i in range(1, 11)) and re.search(r"stack\.md|compliance\.md", sar))
ms = json.load(open(P("managed-settings.json")))
check("REQ-V2K-02 managed settings drop Bash(git *) and deny git -c/config, force push and gh merge",
      "Bash(git *)" not in ms["permissions"]["allow"] and all(x in ms["permissions"]["deny"] for x in ("Bash(git -c *)", "Bash(git config *)", "Bash(gh pr merge *)")))
check("REQ-V2K-02 managed settings force-enable the five plugins", len(ms.get("enabledPlugins", {})) == 5)
check("REQ-V2A-04 managed settings ship the OTel env block", ms.get("env", {}).get("CLAUDE_CODE_ENABLE_TELEMETRY") == "1")
gov = read("governance", "supplier-audit-packet.md")
check("REQ-V2O-01 governance no longer claims 'no source change is possible'; claims cite engine tests",
      "No source change is possible without an approved plan" not in gov and "engine-tests" in gov)
cm = read("governance", "control-mapping.md")
check("REQ-V2O-02 control mapping covers SOC 2, ISO 27001:2022 and NIST SSDF with statuses",
      all(x in cm for x in ("CC8.1", "A.8.32", "PW.4", "ENFORCED", "OWNER ACTION")) and
      all(os.path.isfile(P("plugins", "evidence-compliance", "skills", "regulatory-controls", "references", f)) for f in ("iso-27001.md", "nist-ssdf.md")))
sets = [f for f in glob.glob(P("plugins", "evidence-compliance", "skills", "regulatory-controls", "references", "*.md")) if not f.endswith("README.md")]
check("REQ-V2O-03 every control set states its owner explicitly (no <name> placeholder)",
      sets and all("Owner: UNASSIGNED" in open(f).read() or re.search(r"Owner: (?!<)\S", open(f).read()) for f in sets)
      and not any("Owner: <name>" in open(f).read() for f in sets))
man = {n: json.load(open(P("plugins", n, ".claude-plugin", "plugin.json"))) for n in os.listdir(P("plugins")) if os.path.isfile(P("plugins", n, ".claude-plugin", "plugin.json"))}
check("REQ-V2P-01 every plugin has a semver version and CHANGELOG has the entry",
      all(re.fullmatch(r"\d+\.\d+\.\d+", m.get("version", "")) for m in man.values()) and "## 2.0.0" in read("CHANGELOG.md"))
with tempfile.TemporaryDirectory() as d:
    subprocess.run(f"git init -q -b main && mkdir -p plugins/x/.claude-plugin && echo '{{\"version\":\"1.0.0\"}}' > plugins/x/.claude-plugin/plugin.json && printf '## 1.0.1\\n' > CHANGELOG.md "
                   "&& git add -A && git -c user.email=t@t -c user.name=t commit -qm base && git checkout -qb f && echo x > plugins/x/a.md "
                   "&& git add -A && git -c user.email=t@t -c user.name=t commit -qm change", shell=True, cwd=d)
    r1 = subprocess.run(["bash", P("scripts", "ci", "check-version-bump.sh"), "main"], cwd=d, capture_output=True, text=True)
    subprocess.run("echo '{\"version\":\"1.0.1\"}' > plugins/x/.claude-plugin/plugin.json && git -c user.email=t@t -c user.name=t commit -qam bump", shell=True, cwd=d)
    r2 = subprocess.run(["bash", P("scripts", "ci", "check-version-bump.sh"), "main"], cwd=d, capture_output=True, text=True)
    check("REQ-V2P-01 version-bump check fails without a bump and passes with one", r1.returncode != 0 and r2.returncode == 0, r1.stdout + r2.stdout)
check("REQ-V2P-02 metadata: homepage, repository, license, keywords, owner email on every plugin",
      all(all(k in m for k in ("homepage", "repository", "license", "keywords")) and re.fullmatch(r"[^@\s]+@[^@\s]+\.[a-z]+", m["author"]["email"])
          and not m["author"]["email"].endswith("@gmail.com") for m in man.values()))
cmds = {os.path.basename(c)[:-3] for c in glob.glob(P("plugins", "evidence-sdlc", "commands", "*.md"))}
ap = frontmatter(P("plugins", "evidence-sdlc", "commands", "approve.md")) or {}
check("REQ-V2P-03 slash commands exist; approve is not model-invocable",
      {"start", "status", "approve", "gaps", "release-report"} <= cmds and ap.get("disable-model-invocation") == "true", cmds)
qh = read("plugins", "evidence-quality", "hooks", "hooks.json")
check("REQ-V2P-04 cross-plugin dependencies are documented soft dependencies (no hard `dependencies` field, which "
      "stops a plugin's skills loading when a sibling is absent); commit gate moved into the sdlc engine",
      not any(m.get("dependencies") for m in man.values()) and "require-issue-key" not in qh
      and re.search(r"soft dependenc", read("docs", "getting-started.md") + read("README.md"), re.I))
ci = read(".github", "workflows", "ci.yml") + read("scripts", "ci", "run-tests.sh")
check("REQ-V2P-05 CI runs engine, lifecycle, sensor, CLI and content suites, version check, strict gaps and plugin validate",
      all(x in ci for x in ("run-tests.sh", "engine-tests.py", "cli-lifecycle-tests.py", "template-sensor-tests.sh", "test_cli_fixtures.sh",
                            "content_acceptance_tests.py", "check-version-bump.sh", "gaps --strict", "plugin validate")))
check("REQ-V2P-05 reference pipelines are real YAML for GitHub Actions, GitLab and CI-hosted agent",
      all(os.path.isfile(P("pipelines", *x)) for x in (("github-actions", "evidence-chain.yml"), ("github-actions", "agent-in-ci.yml"), ("gitlab", "evidence-chain.gitlab-ci.yml"))))
tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split()
check("REQ-V2P-06 README is 250 lines or fewer and personal files are not tracked",
      len(read("README.md").splitlines()) <= 250 and "docs/linkedin-caption.txt" not in tracked and not any(t.endswith(".zip") for t in tracked),
      len(read("README.md").splitlines()))
check("REQ-V2P-07 strictKnownMarketplaces is documented as an owner action with the value to set",
      re.search(r"strictKnownMarketplaces", read("docs", "managed-settings.md")) and re.search(r"owner action", read("docs", "managed-settings.md"), re.I))
msd = read("docs", "managed-settings.md")
check("REQ-SLF-06 managed-settings doc: hook-performed lifecycle calls, key for human terminal actions, commit tail rule",
      "Done by the gate engine" in msd and re.search(r'EVIDENCE_SIGNING_KEY="\$\(python3 .*\\\n\s*evidence change clear-violations', msd)
      and "clear-violations" in msd and re.search(r"at most two appended entries", msd))
REPO = "https://github.com/harshil-1411/ai-sdlc"
leftover = [f for f in subprocess.run(["git", "grep", "-l", "REPLACE-WITH-YOUR-ORG"], cwd=ROOT, capture_output=True, text=True).stdout.split()
            if f not in ("CHANGELOG.md", "tests/content_acceptance_tests.py") and not f.startswith(("intent/", "plan/", "validation/", ".evidence/"))]
check("REQ-P54-01 no REPLACE-WITH-YOUR-ORG placeholder is left; every plugin names the published repository",
      not leftover and all(m.get("repository") == REPO and m.get("homepage") == REPO + "#readme" for m in man.values()),
      leftover)
co = read(".github", "CODEOWNERS")
check("REQ-P54-02 CODEOWNERS has a default owner and covers the control plane and the engine, with no placeholder team",
      re.search(r"^\*\s+@\S+", co, re.M) and all(p in co for p in ("/.evidence/policy.json", "/.claude/", "/managed-settings.json",
                                                                   "/.github/", "/plugins/evidence-sdlc/scripts/engine/"))
      and "@your-org" not in co, co[:300])
mkt = json.load(open(P(".claude-plugin", "marketplace.json")))
mver = {p["name"]: p["version"] for p in mkt.get("plugins", [])}
# Since PILOT-58 (2.1.0) this checks the versions agree at 2.0.2 or later, instead of pinning 2.0.2.
_vers = {m.get("version") for m in man.values()} | set(mver.values())
_ver = next(iter(_vers)) if len(_vers) == 1 else ""
check("REQ-P54-03 every plugin has one version (2.0.2 or later) in plugin.json and marketplace.json, and CHANGELOG has the entry",
      _ver and tuple(int(x) for x in _ver.split(".")) >= (2, 0, 2) and set(mver) == set(man)
      and f"## {_ver}" in read("CHANGELOG.md") and "## 2.0.2" in read("CHANGELOG.md"),
      (mver, {n: m.get("version") for n, m in man.items()}))


def single_slash_rules(settings):
    """Permission rules naming an absolute path with one leading slash, which Claude Code resolves
    relative to the project (only `//path` is absolute)."""
    rules = [r for k in ("allow", "deny", "ask") for r in settings.get("permissions", {}).get(k, [])]
    return [r for r in rules if re.match(r"^\w+\(\s*/[^/]", r)]


old_ms = subprocess.run(["git", "show", "1391408:managed-settings.json"], cwd=ROOT, capture_output=True, text=True).stdout
deny = ms.get("permissions", {}).get("deny", [])
check("REQ-P54-04 managed-settings permission rules use // for absolute paths, the managed directories are denied to "
      "Read, and the pre-fix template is caught",
      not single_slash_rules(ms) and any(r.startswith("Read(//Library/Application Support/ClaudeCode") for r in deny)
      and any(r.startswith("Read(//etc/claude-code") for r in deny) and bool(old_ms) and single_slash_rules(json.loads(old_ms)),
      (single_slash_rules(ms), single_slash_rules(json.loads(old_ms)) if old_ms else "old template unavailable"))
gov = read("governance", "supplier-audit-packet.md")
check("REQ-P54-05 managed-settings doc states the // rule with a Read-tool canary; the supplier packet covers the Read tool",
      re.search(r"`//", msd) and re.search(r"canary", msd, re.I) and re.search(r"denied by your permission settings", msd)
      and re.search(r"Read tool", gov))
check("REQ-P54-06 the start command says to run `evidence change start` as its own command, performed by the gate engine",
      re.search(r"own command", read("plugins", "evidence-sdlc", "commands", "start.md"))
      and re.search(r"gate engine", read("plugins", "evidence-sdlc", "commands", "start.md")))
gp = subprocess.run([sys.executable, P("plugins", "evidence-sdlc", "bin", "evidence"), "gaps"], cwd=ROOT,
                    capture_output=True, text=True).stdout
orphan = gp.split("ORPHANED", 1)[1].split("\n\n", 1)[0] if "ORPHANED" in gp else ""
check("REQ-P54-07 evidence gaps reads requirement IDs from Tier 1 plans (plan/*.md), so plan-only REQ IDs are not orphaned",
      re.search(r"^\s*-\s*plan/\*\.md\s*$", read(".evidence", "adapter.yml"), re.M) and "REQ-P54" not in orphan, orphan[:300])
check("REQ-V2C-01 the CLI ships in the plugin's bin/ and runs",
      subprocess.run([sys.executable, P("plugins", "evidence-sdlc", "bin", "evidence"), "--version"], capture_output=True, text=True).returncode == 0)
hj = json.load(open(P("plugins", "evidence-sdlc", "hooks", "hooks.json")))
pre = hj["hooks"]["PreToolUse"]
check("REQ-V2G-11 no hook pre-filter: every Bash/Edit/Write/Agent call reaches the engine",
      all("if" not in h for entry in pre for h in entry["hooks"]) and any("Bash" in e.get("matcher", "") and "Edit" in e.get("matcher", "") for e in pre))
# REQ-V2C-09 is proven by run-tests.sh's final step (self-check.xml, PILOT-60 REQ-USA-02), not by a run
# from inside this suite, which could only read results older than itself. This check binds the ID.
_rt = read("scripts", "ci", "run-tests.sh")
check("REQ-V2C-09 this repository's own strict gate is run-tests.sh's final step, over that run's results only",
      "gaps --strict --self-check --only-results" in _rt and "self-check.xml" in _rt)
summaries = [f for f in glob.glob(P("plugins", "*", "evals", "SUMMARY.md"))]
check("REQ-V2E-01 a committed eval SUMMARY.md exists for every plugin", len(summaries) == 5, summaries)
check("REQ-V2E-02 summaries record with-vs-without deltas", summaries and all(re.search(r"Δ|delta|without", open(s).read(), re.I) for s in summaries))
sdlc_cases = [os.path.basename(d) for d in glob.glob(P("plugins", "evidence-sdlc", "evals", "*")) if os.path.isdir(d)]
check("REQ-V2E-03 eval cases exist for release-readiness and the new agents",
      all(any(c.startswith(p) for c in sdlc_cases) for p in ("release-readiness-", "architect-", "code-reviewer-", "release-manager-", "docs-writer-")))

# ------------------------------------------------------------ PILOT-58
vr = read(".github", "workflows", "verify-range.yml")


def run_blocks(yml):
    """The text of every `run:` step (inline or block scalar)."""
    out, lines = [], yml.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^(\s*)(?:-\s+)?run:\s*(.*)$", line)
        if not m:
            continue
        ind, body = len(m.group(1)), [m.group(2)]
        for nxt in lines[i + 1:]:
            if nxt.strip() and len(nxt) - len(nxt.lstrip()) <= ind:
                break
            body.append(nxt)
        out.append("\n".join(body))
    return out


runs = run_blocks(vr)
perms = re.search(r"^permissions:\s*\n((?:\s+.*\n)+)", vr, re.M)
check("REQ-IMH-21 verify-range.yml runs on pull_request_target (opened, synchronize, reopened), workflow_dispatch with a "
      "PR number, and push to main",
      re.search(r"pull_request_target:\s*\n\s+types:\s*\[\s*opened,\s*synchronize,\s*reopened(?:,\s*edited)?\s*\]", vr)
      and re.search(r"workflow_dispatch:\s*\n\s+inputs:\s*\n\s+pr:", vr)
      and re.search(r"push:\s*\n\s+branches:\s*\[\s*main\s*\]", vr), vr[:400])
check("REQ-IMH-21 checks out only the base, full depth, without persisted credentials",
      re.search(r"uses:\s*actions/checkout@", vr) and re.search(r"ref:\s*\$\{\{\s*github\.event\.pull_request\.base\.sha", vr)
      and not re.search(r"ref:\s*\$\{\{[^}]*head", vr) and re.search(r"fetch-depth:\s*0\b", vr)
      and re.search(r"persist-credentials:\s*false", vr)
      # nor any other way of getting PR code onto disk or running it (code review, step 11)
      and not re.search(r"repository:\s*\$\{\{[^}]*head", vr)
      and not any(re.search(r"\bgit\s+(?:-\S+\s+)*(checkout|switch|worktree|restore|reset\s+--hard|read-tree\s+-u|merge|pull)\b", b)
                  for b in runs), vr[:400])
check("REQ-IMH-21 fetches refs/pull/<n>/head from env and checks it equals the event head",
      any(re.search(r"refs/pull/\$\{?PR\}?/head", b) and re.search(r"\$\{?HEAD_SHA\}?", b) for b in runs), runs)
check("REQ-IMH-21 runs the base's CLI in verify-range and push-report modes, with the key and token in step env only",
      any("plugins/evidence-sdlc/bin/evidence verify-range" in b for b in runs) and any("--push-report" in b for b in runs)
      and re.search(r"EVIDENCE_SIGNING_KEY:\s*\$\{\{\s*secrets\.", vr) and re.search(r"GH_TOKEN:", vr)
      and not re.search(r"^env:\s*\n(?:\s+.*\n)*?\s+EVIDENCE_SIGNING_KEY", vr, re.M), runs)
check("REQ-IMH-21 no attacker-controlled event field or other `${{ }}` expression inside any run:",
      runs and not any("${{" in b for b in runs), [b for b in runs if "${{" in b])
check("REQ-IMH-21 nothing is allowed to fail open (no continue-on-error, no `|| true`)",
      vr and "continue-on-error" not in vr and not re.search(r"\|\|\s*true", vr))
check("REQ-IMH-21 permissions are contents: read and pull-requests: read, nothing writable",
      perms and re.search(r"contents:\s*read", perms.group(1)) and re.search(r"pull-requests:\s*read", perms.group(1))
      and "write" not in perms.group(1), perms.group(1) if perms else vr[:300])
check("REQ-IMH-21 each mode is conditioned on its event",
      re.search(r"if:.*github\.event_name\s*==\s*'push'", vr)
      and re.search(r"if:.*github\.event_name\s*!=\s*'push'|if:.*github\.event_name\s*==\s*'pull_request_target'", vr))

gr, mdoc, pref = read("docs", "gates-reference.md"), read("docs", "managed-settings.md"), read("docs", "policy-reference.md")
cm, sap, ho, cl = (read("governance", "control-mapping.md"), read("governance", "supplier-audit-packet.md"), read("HANDOFF.md"),
                   read("CHANGELOG.md"))
cl21 = cl.split("## 2.1.0", 1)[1].split("\n## ", 1)[0] if "## 2.1.0" in cl else ""
check("REQ-IMH-18 gates reference and managed-settings doc: local push gate advisory, verify-range pull_request_target "
      "authoritative, sign-and-gate unchanged",
      all(re.search(r"advisory", t, re.I) and "verify-range" in t and "pull_request_target" in t for t in (gr, mdoc))
      and "sign-and-gate" in gr)
check("REQ-IMH-18 docs name the owner actions: required check, code-owner review, re-run after approval, fork PRs",
      all(re.search(p, gr + mdoc, re.I) for p in (r"required (status )?check", r"code.owner", r"re-run", r"fork")))
check("REQ-IMH-18 policy reference documents git_allowed_config, verify_range_blob_cap_mb and verify_range_allow_large",
      all(k in pref for k in ("git_allowed_config", "verify_range_blob_cap_mb", "verify_range_allow_large")))
check("REQ-IMH-18 governance rests change control on verify-range and states the ADR-0003 residual risk",
      "verify-range" in cm and "verify-range" in sap and all(re.search(r"residual risk", t, re.I) and "ADR-0003" in t for t in (cm, sap)))
check("REQ-IMH-18 HANDOFF and the 2.1.0 CHANGELOG Known issues name what moved to PILOT-59, 60 and 61",
      "verify-range" in ho and re.search(r"known issues", cl21, re.I) and all(k in cl21 for k in ("PILOT-59", "PILOT-60", "PILOT-61")),
      cl21[:300])

# ------------------------------------------------------------ PILOT-62
cl22 = cl.split("## 2.2.0", 1)[1].split("\n## ", 1)[0] if "## 2.2.0" in cl else ""
sec = read("SECURITY.md")
LLA_KEYS = {"auto_resolve_max_per_session": 3, "local_settings_kept_keys": ["model", "outputStyle"],
            "claude_json_security_keys": ["mcpServers", "allowedTools", "enabledMcpjsonServers", "disabledMcpjsonServers",
                                          "enableAllProjectMcpServers"],
            "tier3_auto_modes_with_required_gate": True, "tier3_gate_allowed_modes": ["acceptEdits", "auto"],
            "ci_gate_check": "verify-range", "ci_gate_app_id": 15368, "ci_gate_require_enforce_admins": False,
            "ci_gate_cache_seconds": 900}
try:
    dp = json.load(open(P("plugins", "evidence-sdlc", "policy", "default-policy.json")))
except (OSError, ValueError):
    dp = {}
check("REQ-LLA-11 default policy ships the ten PILOT-62 keys with the spec's defaults",
      all(dp.get(k) == v for k, v in LLA_KEYS.items()) and len(dp.get("user_config_not_charged") or []) == 6
      and all(p.startswith(("/Library/Application Support/ClaudeCode/", "/etc/claude-code/"))
              for p in dp.get("user_config_not_charged") or []),
      {k: dp.get(k) for k in LLA_KEYS})
check("REQ-LLA-11 policy reference documents every new key and its repository merge rule",
      all(k in pref for k in list(LLA_KEYS) + ["user_config_not_charged"])
      and re.search(r"only lower", pref) and re.search(r"only (become|set .{0,60}to) false", pref))
check("REQ-LLA-11 gates reference: restored violations closed at birth and bounded, config edits, Tier 3 auto modes "
      "behind the pinned server gate, check-forgery, rule 5 notes",
      all(t in gr for t in ("closed at birth", "auto_resolve_max_per_session", "config-change", "user-config-changed",
                            "`check-forgery`", "GitHub Actions", "tier3_auto_modes_with_required_gate", "NOTE:"))
      and re.search(r"bypassPermissions.{0,40}dontAsk.{0,40}stay\s+denied", gr, re.S))
check("REQ-LLA-11 managed-settings owner actions: pin the check to GitHub Actions, approval.github_repo, a root-owned "
      "org policy, remove the permission-mode loosening",
      re.search(r"Pin `verify-range` to GitHub Actions", mdoc) and "approval.github_repo" in mdoc
      and re.search(r"root-owned", mdoc) and re.search(r"permission-mode loosening", mdoc))
check("REQ-LLA-11 governance and SECURITY restate the monitor as verified automatic undo, and unresolved violations "
      "still block",
      all(re.search(r"verified", t, re.I) and re.search(r"unresolved violations still block", t, re.I) for t in (cm, sap, sec)))
check("REQ-LLA-11 CHANGELOG 2.2.0 states the owner actions, the NEEDS VERIFICATION items and the PILOT-63 "
      "release-automation deferral; HANDOFF names PILOT-62 and PILOT-63",
      cl22 and "GitHub Actions" in cl22 and "approval.github_repo" in cl22 and "NEEDS VERIFICATION" in cl22
      and re.search(r"known issues", cl22, re.I) and "PILOT-63" in cl22 and "PILOT-62" in ho and "PILOT-63" in ho, cl22[:300])
vers = {p: json.load(open(p)).get("version") for p in glob.glob(P("plugins", "*", ".claude-plugin", "plugin.json"))}
mk = json.load(open(P(".claude-plugin", "marketplace.json")))
mvers = [x.get("version") for x in mk.get("plugins", [])] + [mk.get("version") or (mk.get("metadata") or {}).get("version")]
import state as _st  # noqa: E402
# Since PILOT-60 (2.3.0) this checks the versions agree at 2.2.0 or later, instead of pinning 2.2.0.
_v22 = set(vers.values()) | set(v for v in mvers if v) | {_st.ENGINE_VERSION}
check("REQ-LLA-11 all five plugins, the marketplace and the engine agree on one version, 2.2.0 or later",
      len(vers) == 5 and len(_v22) == 1 and tuple(int(x) for x in next(iter(_v22)).split(".")) >= (2, 2, 0),
      (vers, mvers, _st.ENGINE_VERSION))

# ------------------------------------------------------------ PILOT-60
rt = read("scripts", "ci", "run-tests.sh")
m_out = re.search(r'^out="\$\{EVIDENCE_RESULTS_DIR:-([^\n]*)\}"\s*$', rt, re.M)
check("REQ-USA-01 run-tests.sh reads EVIDENCE_RESULTS_DIR and its default is outside the working tree",
      m_out and "$root" not in m_out.group(1) and "TMPDIR" in m_out.group(1) and "validation/results" not in rt
      and re.search(r'rm -f "\$out"/\*\.xml "\$out"/\*\.log "\$out"/\*\.sig', rt)
      and re.search(r"^echo .*\$out", rt, re.M), m_out.group(0) if m_out else rt[:300])
rt_lines = [l for l in rt.splitlines() if l.strip() and not l.strip().startswith("#")]
sc_at = next((i for i, l in enumerate(rt_lines) if "gaps --strict --self-check --only-results" in l), -1)
_in_suite = '"gaps", ' + '"--strict"'
check("REQ-USA-02 run-tests.sh ends with gaps --strict --self-check and the content suite has no in-suite self-check",
      sc_at > max((i for i, l in enumerate(rt_lines) if l.startswith("run ")), default=10 ** 6)
      and re.search(r'--results "\$out"', rt_lines[sc_at] if sc_at >= 0 else "")
      and re.search(r'junit_from_tsv\.py" "self-check" "\$out/self-check\.xml"', rt)
      and "REQ-V2C-09 this repository passes its own evidence gaps --strict (run-tests.sh final step)" in rt
      and _in_suite not in read("tests", "content_acceptance_tests.py"), rt_lines[-6:])
ci = read(".github", "workflows", "ci.yml")
sg = ci.split("sign-and-gate:", 1)[1].split("\n  evals:", 1)[0] if "sign-and-gate:" in ci else ""
chk = ci.split("  checks:", 1)[1].split("\n  sign-and-gate:", 1)[0] if "  checks:" in ci else ""
check("REQ-USA-04 sign-and-gate signs and gates only runner.temp results",
      re.search(r"EVIDENCE_RESULTS_DIR: \$\{\{ runner\.temp \}\}/results", chk)
      and re.search(r"if: always\(\)\s*\n\s*with:\s*\n\s*name: validation-results\s*\n\s*path: \$\{\{ runner\.temp \}\}/results/", chk)
      and re.search(r"path: \$\{\{ runner\.temp \}\}/results/", sg)
      and 'results sign "$RUNNER_TEMP"/results/*.xml' in sg
      and '--only-results --results "$RUNNER_TEMP/results"' in sg and "gaps --help | grep -q -- --only-results" in sg
      and "validation/results" not in sg, sg[:400])
gha = read("pipelines", "github-actions", "evidence-chain.yml")
gl = read("pipelines", "gitlab", "evidence-chain.gitlab-ci.yml")
ev = gha.split("\n  evidence:", 1)[1] if "\n  evidence:" in gha else ""
check("REQ-USA-04 adopter templates sign only downloaded results; GitLab refuses tracked test-results",
      re.search(r"path: \$\{\{ runner\.temp \}\}/test-results/", ev)
      and 'results sign "$RUNNER_TEMP"/test-results/*.xml' in ev
      and '--only-results --results "$RUNNER_TEMP/test-results"' in ev and "sign test-results/" not in ev
      and 'out=$(git ls-files -- test-results) || exit 1; test -z "$out"' in gl
      and 'test -z "$(git ls-files' not in gl and "--only-results --results test-results" in gl,
      (ev[:300], gl[-300:]))
_rt_code = [l for l in rt.splitlines() if l.strip() and not l.strip().startswith("#")]
_guard_at = next((i for i, l in enumerate(_rt_code) if '"$real_out/"' in l and '"$real_root"/*' in l and "exit 2" in l), -1)
_rm_at = next((i for i, l in enumerate(_rt_code) if l.startswith("rm -f")), -1)
check("REQ-USA-01 run-tests.sh refuses an EVIDENCE_RESULTS_DIR inside the working tree (realpath) before any rm -f",
      0 <= _guard_at < _rm_at
      and any(l.startswith("real_out=") and "realpath" in l and '"$out"' in l for l in _rt_code[:_guard_at])
      and any(l.startswith("real_root=") and "realpath" in l and '"$root"' in l for l in _rt_code[:_guard_at]),
      _rt_code[:14])

# REQ-USA-12: docs, governance, HANDOFF, CHANGELOG and versions match the shipped behaviour
cl23 = cl.split("## 2.3.0", 1)[1].split("\n## ", 1)[0] if "## 2.3.0" in cl else ""
adr2 = read(".evidence", "decisions", "0002-ci-owns-test-results.md")
adr3 = read(".evidence", "decisions", "0003-hook-git-is-neutralised.md")
clir = read("cli", "README.md")
gr60, pr60 = read("docs", "gates-reference.md"), read("docs", "policy-reference.md")
ho60, contrib = read("HANDOFF.md"), read("CONTRIBUTING.md")
check("REQ-USA-12 ADR-0002 is revision 2 and ADR-0003 §2 carries the dated PILOT-60 revision note",
      "revision 2" in adr2 and "--only-results" in adr2 and re.search(r"Revision note, 2026-09-\d\d \(PILOT-60", adr3)
      and "ENGINE_ALWAYS_REFUSED" in adr3, adr3[:200])
check("REQ-USA-12 CI's signed artifact is the test evidence; validation/results is historical; one run; --results <dir>",
      all("historical" in t for t in (cl23, ho60, sap)) and "freshly downloaded" in cm and "--results <dir>" in clir
      and "One run is enough" in ho60 and "one run is enough" in contrib
      and "--self-check" in clir and "--only-results" in clir, (len(cl23), "historical" in sap))
check("REQ-USA-12 the YAML comment rule, plan references and -k/--suite are documented",
      re.search(r"Comments \(2\.3\.0\)", clir) and re.search(r"Comments \(2\.3\.0\)", read(".evidence", "adapter.example.yml"))
      and re.search(r"\*\*reference\*\*", clir) and re.search(r"\*\*reference\*\*", read("docs", "concepts.md"))
      and "--suite" in contrib and "0 cases matched" in contrib and "--suite" in ho60)
check("REQ-USA-12 gates reference: temp paths judged as paths, what stays denied, and the sandbox-safe mktemp form",
      "## Temp-directory paths" in gr60 and 'mktemp "$TMPDIR/x.XXXXXX"' in gr60 and "--compress-program" in gr60
      and "`make -f /tmp/Makefile`" in gr60)
check("REQ-USA-12 both git config sets are documented with their reasons; the known-issue sentence is gone",
      "git_config_engine_ignored" in pr60 and "ENGINE_ALWAYS_REFUSED" in pr60 and "shadows a built-in" in pr60
      and "**Intersection**" in pr60 and "PILOT-60 splits the list" not in pr60
      and all(k in pr60 for k in ("remote.*.url", "remote.*.pushurl", "url.*.insteadOf", "url.*.pushInsteadOf"))
      and "ENGINE_ALWAYS_REFUSED" in gr60)
check("REQ-USA-12 CHANGELOG 2.3.0 states the owner actions and PILOT-64; HANDOFF carries the ci.yml diff",
      cl23 and "ci.yml" in cl23 and "git_allowed_config" in cl23 and "PILOT-64" in cl23 and "MAN-USA-01" in cl23
      and "## PILOT-60 owner actions" in ho60 and "```diff\n--- a/.github/workflows/ci.yml" in ho60, cl23[:200])
check("REQ-USA-12 all five plugins, the marketplace and the engine are version 2.3.0",
      set(vers.values()) == {"2.3.0"} and set(v for v in mvers if v) == {"2.3.0"} and _st.ENGINE_VERSION == "2.3.0",
      (vers, mvers, _st.ENGINE_VERSION))

fails = sum(1 for _, ok, _ in res if not ok)
print(f"\n{len(res) - fails} passed, {fails} failed")
if os.environ.get("JUNIT_OUT"):
    from xml.sax.saxutils import escape, quoteattr
    with open(os.environ["JUNIT_OUT"], "w") as f:
        f.write(f'<?xml version="1.0" encoding="UTF-8"?>\n<testsuite name="content presence and function checks" tests="{len(res)}" failures="{fails}">\n')
        for label, ok, detail in res:
            f.write(f'  <testcase classname="content presence and function checks" name={quoteattr(label)}>')
            if not ok:
                f.write(f'<failure message={quoteattr(detail[:200])}>{escape(detail)}</failure>')
            f.write("</testcase>\n")
        f.write("</testsuite>\n")
sys.exit(1 if fails else 0)
