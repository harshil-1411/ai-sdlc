"""Shell command analysis for the Evidence Chain gate engine.

Parses a Bash tool command into simple commands and reports what each one does
that the gates care about: file writes (with target paths when they can be
known), pushes, commits, deploys, merges and approvals. Standard library only.

This is deliberately a parser, not a pattern matcher. The v1 audit showed that
regexes over the raw command string both miss real operations (`git -C . push`,
`kubectl apply`) and fire on text that merely mentions them (`grep production`).
"""
import os
import re
import shlex

CONTROL_OPS = {";", "&&", "||", "|", "&", "|&", "\n", ";;", "(", ")"}
REDIRECT_OPS = {">", ">>", ">|", "&>", "&>>", "<>"}
WRAPPERS = {"command", "builtin", "exec", "nohup", "nice", "time", "stdbuf",
            "timeout", "sudo", "doas", "env", "xargs", "ionice", "chronic"}
SHELLS = {"sh", "bash", "zsh", "dash", "ksh"}
PERSISTENCE = {"nohup", "setsid", "disown", "at", "batch", "crontab", "launchctl", "systemd-run", "daemonize",
               "start-stop-daemon", "screen", "tmux", "caffeinate", "script", "dtach", "abduco"}
MULTICALL = {"busybox", "toybox"}
INTERPRETERS = {"python", "python3", "python2", "node", "nodejs", "ruby", "perl",
                "php", "deno", "bun", "pwsh", "powershell", "osascript"}
INLINE_FLAGS = {"-c", "-e", "-E", "--eval", "-r", "--command", "-Command"}
# Words in inline interpreter code that indicate it writes or deletes files.
_WRITE_HINTS = re.compile(
    r"open\s*\([^)]*['\"][wax+]|write_text|write_bytes|\.write\(|os\.remove|os\.unlink|"
    r"unlink\(|rmtree|shutil\.|os\.rename|os\.replace|\.touch\(|Path\([^)]*\)\.(write|unlink|rename)|"
    r"writeFile|appendFile|fs\.rm|fs\.unlink|File\.write|IO\.write|File\.delete|"
    r"open\(.*,\s*['\"]>|subprocess|os\.system|child_process|execSync|spawnSync|"
    r"Out-File|Set-Content|Remove-Item|-i\b|"
    r"json\.dump\(|write_approval|save_state|audit_append|lifecycle|\.evidence|approval|"
    r"os\.environ\[[^\]]*\]\s*=|putenv|\bexec\s*\(|\beval\s*\(|\bcompile\s*\(|__import__|importlib|"
    r"base64|codecs\.decode|marshal|pickle|ctypes|new\s+Function|require\(['\"]child_process",
    re.S,
)


class Write:
    """A file-system effect. path is None when the target can't be known."""

    __slots__ = ("path", "kind", "detail")

    def __init__(self, path, kind, detail=""):
        self.path = path
        self.kind = kind          # write | delete | opaque
        self.detail = detail

    def __repr__(self):
        return f"Write({self.path!r}, {self.kind!r})"


class Simple:
    """One simple command after wrappers are stripped."""

    def __init__(self, argv, env, redirects, raw, via_xargs=False, stdin_file=None, wrappers=()):
        self.argv = argv
        self.env = env
        self.redirects = redirects
        self.raw = raw
        self.via_xargs = via_xargs
        self.stdin_file = stdin_file
        self.wrappers = list(wrappers)
        self.piped_in = False

    @property
    def prog(self):
        return os.path.basename(self.argv[0]) if self.argv else ""


def _tokenize(cmd):
    lex = shlex.shlex(cmd, posix=True, punctuation_chars=";&|()<>")
    lex.whitespace_split = True
    lex.commenters = "#"
    tokens = []
    try:
        for tok in lex:
            tokens.append(tok)
    except ValueError:
        # Unbalanced quotes: fall back to a whitespace split so analysis still
        # happens. Anything we cannot see clearly is treated conservatively by
        # the caller, never as "nothing happened".
        return cmd.split(), False
    return tokens, True


_SUBST = re.compile(r"\$\(((?:[^()]|\([^()]*\))*)\)|`([^`]*)`")
_HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1[^\n]*\n(.*?)\n\s*\2\s*(?:\n|$)", re.S)


def _strip_heredocs(cmd):
    """Remove heredoc bodies (they are data, not commands) but keep the command line."""
    bodies = []

    def repl(m):
        bodies.append(m.group(3))
        return "<< HEREDOC\n"

    return _HEREDOC.sub(repl, cmd), bodies


def split_simple(cmd, _depth=0):
    """Return (simples, ok, heredoc_bodies). Recurses into $(...), `...`, and sh -c."""
    if _depth > 4:
        return [], False, []
    cmd, bodies = _strip_heredocs(cmd)
    inner_cmds = [m.group(1) or m.group(2) for m in _SUBST.finditer(cmd)]
    tokens, ok = _tokenize(cmd)

    simples, cur = [], []
    state = {"piped": False}

    def flush(next_piped=False):
        if cur:
            s = _make_simple(list(cur))
            if s is not None:
                s.piped_in = state["piped"]
                simples.append(s)
            cur.clear()
        state["piped"] = next_piped

    for tok in tokens:
        if tok in CONTROL_OPS or re.fullmatch(r"[;&|()]+", tok or ""):
            flush(next_piped=tok in ("|", "|&"))
        else:
            cur.append(tok)
    flush()

    # Recurse into command substitutions and shell -c payloads.
    for inner in inner_cmds:
        sub, sub_ok, sub_bodies = split_simple(inner, _depth + 1)
        simples.extend(sub)
        ok = ok and sub_ok
        bodies.extend(sub_bodies)
    for s in list(simples):
        if s.prog in SHELLS:
            payload = _flag_value(s.argv[1:], {"-c"})
            if payload:
                sub, sub_ok, sub_bodies = split_simple(payload, _depth + 1)
                simples.extend(sub)
                ok = ok and sub_ok
                bodies.extend(sub_bodies)
        if s.prog in ("export", "declare", "typeset", "readonly"):
            for a in s.argv[1:]:
                if "=" in a and not a.startswith("-"):
                    k, v = a.split("=", 1)
                    s.env[k] = v
        if s.prog == "alias":
            for a in s.argv[1:]:
                if "=" in a:
                    sub, sub_ok, sub_bodies = split_simple(a.split("=", 1)[1], _depth + 1)
                    simples.extend(sub)
                    ok = ok and sub_ok
        if s.prog == "eval":
            sub, sub_ok, sub_bodies = split_simple(" ".join(s.argv[1:]), _depth + 1)
            simples.extend(sub)
            ok = ok and sub_ok
    return simples, ok, bodies


def _flag_value(args, flags):
    for i, a in enumerate(args):
        if a in flags and i + 1 < len(args):
            return args[i + 1]
    return None


def _make_simple(tokens):
    env, argv, redirects = {}, [], []
    stdin_file = None
    i = 0
    # Redirections can appear anywhere; pull them out first.
    rest = []
    while i < len(tokens):
        t = tokens[i]
        if t in REDIRECT_OPS or (t == ">" or t == ">>"):
            target = tokens[i + 1] if i + 1 < len(tokens) else ""
            redirects.append((t, target))
            i += 2
            continue
        if t == "<" and i + 1 < len(tokens):
            stdin_file = tokens[i + 1]
        if t in ("<", "<<", "<<<", "<&", ">&"):
            # input redirection or fd duplication: not a write
            if t == ">&" and i + 1 < len(tokens) and not tokens[i + 1].isdigit() and tokens[i + 1] != "-":
                redirects.append((">", tokens[i + 1]))
            i += 2
            continue
        # a lone digit immediately before a redirect op is an fd number
        if t.isdigit() and i + 1 < len(tokens) and tokens[i + 1] in REDIRECT_OPS | {">&", "<&", "<"}:
            i += 1
            continue
        rest.append(t)
        i += 1
    # Leading VAR=value assignments.
    j = 0
    while j < len(rest) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", rest[j]):
        k, v = rest[j].split("=", 1)
        env[k] = v
        j += 1
    argv = rest[j:]
    via_xargs = any(os.path.basename(a) == "xargs" for a in argv[:4])
    wrappers = [os.path.basename(a) for a in argv[:6] if os.path.basename(a) in WRAPPERS | PERSISTENCE]
    argv = _strip_wrappers(argv, env)
    if not argv and not redirects:
        return None
    return Simple(argv, env, redirects, " ".join(tokens), via_xargs, stdin_file, wrappers)


SHELL_KEYWORDS = {"{", "}", "!", "then", "do", "else", "elif", "if", "while", "until", "fi", "done", "esac", "in",
                  "function", "coproc"}


def _strip_wrappers(argv, env):
    guard = 0
    while argv and guard < 12:
        guard += 1
        # function bodies and compound commands: `f(){ rm x; }`, `if …; then rm x; fi`
        if argv[0] in SHELL_KEYWORDS or argv[0].endswith("{") and argv[0][:-1].replace("_", "a").isalnum():
            argv = argv[1:]
            continue
        prog = os.path.basename(argv[0])
        if prog in MULTICALL and len(argv) > 1:
            argv = argv[1:]
            continue
        if prog not in WRAPPERS:
            break
        argv = argv[1:]
        if prog == "env":
            while argv and (argv[0].startswith("-") or "=" in argv[0]):
                if "=" in argv[0] and not argv[0].startswith("-"):
                    k, v = argv[0].split("=", 1)
                    env[k] = v
                elif argv[0] in ("-S", "--split-string") and len(argv) > 1:
                    argv = argv[1].split() + argv[2:]  # env -S 'cmd args' runs that string as the command
                    break
                elif argv[0] in ("-u", "-C") and len(argv) > 1:
                    argv = argv[1:]
                argv = argv[1:]
        elif prog in ("sudo", "doas"):
            while argv and argv[0].startswith("-"):
                if argv[0] in ("-u", "-g", "-C", "-D", "-h", "-p", "-r", "-t", "-U") and len(argv) > 1:
                    argv = argv[1:]
                argv = argv[1:]
        elif prog in ("nice", "ionice", "stdbuf"):
            while argv and argv[0].startswith("-"):
                if argv[0] in ("-n", "-c") and len(argv) > 1:
                    argv = argv[1:]
                argv = argv[1:]
        elif prog == "timeout":
            while argv and argv[0].startswith("-"):
                argv = argv[1:]
            if argv:
                argv = argv[1:]  # the duration
        elif prog == "xargs":
            while argv and argv[0].startswith("-"):
                if argv[0] in ("-I", "-n", "-P", "-L", "-d", "-E", "-s") and len(argv) > 1:
                    argv = argv[1:]
                argv = argv[1:]
        else:
            while argv and argv[0].startswith("-"):
                argv = argv[1:]
    return argv


# ---------------------------------------------------------------- git parsing

_GIT_OPTS_WITH_ARG = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path",
                      "--config-env", "--super-prefix"}


def git_split(argv):
    """Return (global_opts [(opt, val)], subcommand, sub_args) for a git argv."""
    args = argv[1:]
    gopts = []
    i = 0
    while i < len(args):
        a = args[i]
        if a in _GIT_OPTS_WITH_ARG and i + 1 < len(args):
            gopts.append((a, args[i + 1]))
            i += 2
            continue
        if a.startswith("--") and "=" in a and a.split("=", 1)[0] in _GIT_OPTS_WITH_ARG:
            k, v = a.split("=", 1)
            gopts.append((k, v))
            i += 1
            continue
        if a.startswith("-"):
            gopts.append((a, None))
            i += 1
            continue
        return gopts, a, args[i + 1:]
    return gopts, None, []


def git_push_targets(sub_args, current_branch):
    """Destination refs a `git push` would update, plus flags.

    Returns (targets:list[str], flags:set). A target of '*' means "all refs".
    """
    flags = set()
    positional = []
    i = 0
    opts_with_arg = {"--repo", "--receive-pack", "--exec", "-o", "--push-option",
                     "--force-with-lease", "--signed"}
    while i < len(sub_args):
        a = sub_args[i]
        if a in ("-f", "--force", "--force-if-includes"):
            flags.add("force")
        elif a.startswith("--force-with-lease"):
            flags.add("force")
        elif a in ("--mirror",):
            flags.add("mirror")
        elif a in ("--all", "--branches"):
            flags.add("all")
        elif a in ("-d", "--delete"):
            flags.add("delete")
        elif a == "--tags":
            flags.add("tags")
        elif a in opts_with_arg and "=" not in a and i + 1 < len(sub_args) and not sub_args[i + 1].startswith("-"):
            i += 1
        elif a.startswith("-"):
            if re.fullmatch(r"-[a-zA-Z]+", a) and "f" in a:
                flags.add("force")
        else:
            positional.append(a)
        i += 1
    targets = []
    if "mirror" in flags or "all" in flags:
        return ["*"], flags
    refspecs = positional[1:] if positional else []
    if not refspecs:
        if current_branch:
            targets.append(current_branch)
        return targets, flags
    for spec in refspecs:
        if spec.startswith("+"):
            flags.add("force")
            spec = spec[1:]
        if ":" in spec:
            src, dst = spec.split(":", 1)
            if dst == "" and "delete" not in flags:
                dst = src
            if src == "":
                flags.add("delete")
        else:
            dst = spec
        if dst in ("HEAD", "@") and current_branch:
            dst = current_branch
        dst = re.sub(r"^refs/heads/", "", dst)
        if "$" in dst or "`" in dst:
            dst = "*"
        targets.append(dst)
    return targets, flags


def git_commit_messages(sub_args, read_file=None):
    """Return (messages:list[str], flags:set) from `git commit` args."""
    msgs, flags = [], set()
    i = 0
    while i < len(sub_args):
        a = sub_args[i]
        nxt = sub_args[i + 1] if i + 1 < len(sub_args) else None
        if a in ("-m", "--message") and nxt is not None:
            msgs.append(nxt)
            i += 2
            continue
        if a.startswith("--message="):
            msgs.append(a.split("=", 1)[1])
        elif a.startswith("-m") and len(a) > 2 and not a.startswith("--"):
            msgs.append(a[2:])
        elif a in ("-F", "--file") and nxt is not None:
            flags.add("file")
            msgs.append(read_file(nxt) if read_file else "")
            i += 2
            continue
        elif a.startswith("--file="):
            flags.add("file")
            msgs.append(read_file(a.split("=", 1)[1]) if read_file else "")
        elif a == "--amend":
            flags.add("amend")
        elif a == "--no-edit":
            flags.add("no-edit")
        elif a in ("-C", "-c", "--reuse-message", "--reedit-message") and nxt is not None:
            flags.add("reuse")
            i += 2
            continue
        elif a in ("-a", "--all"):
            flags.add("all")
        elif re.fullmatch(r"-[a-zA-Z]+", a) and not a.startswith("--"):
            letters = a[1:]
            if "a" in letters:
                flags.add("all")
            if letters.endswith("m") and nxt is not None:
                msgs.append(nxt)
                i += 2
                continue
            if letters.endswith("F") and nxt is not None:
                flags.add("file")
                msgs.append(read_file(nxt) if read_file else "")
                i += 2
                continue
        i += 1
    return msgs, flags


# ------------------------------------------------------------- write analysis

def _nonopts(args):
    out, end = [], False
    for a in args:
        if end:
            out.append(a)
        elif a == "--":
            end = True
        elif a.startswith("-") and a != "-":
            continue
        else:
            out.append(a)
    return out


READ_ONLY_PROGS = {"grep", "egrep", "fgrep", "rg", "cat", "head", "tail", "wc", "ls", "stat", "file", "echo",
                   "printf", "test", "[", "basename", "dirname", "realpath", "readlink", "md5sum", "sha256sum",
                   "shasum", "diff", "cmp", "sort", "uniq", "cut", "awk", "sed", "jq", "python3", "true"}
WRITE_PROGS = {"rm", "unlink", "rmdir", "shred", "mv", "cp", "install", "ln", "touch", "truncate", "tee", "dd",
               "chmod", "chown", "sed", "perl", "patch"}


def script_execution(s):
    """The script file an interpreter or shell is asked to run, if any."""
    if not s.argv:
        return None
    prog, args = s.prog, s.argv[1:]
    if prog in ("source", "."):
        return args[0] if args else None
    if prog in SHELLS or prog in INTERPRETERS:
        if any(a in INLINE_FLAGS for a in args) or "-n" in args or "-m" in args:
            return None
        i = 0
        while i < len(args) and args[i].startswith("-"):
            i += 1
        return args[i] if i < len(args) and args[i] != "-" else None
    return None


def writes_of(s):
    """File-system writes performed by one simple command."""
    w = []
    if s.via_xargs and s.prog in WRITE_PROGS:
        w.append(Write(None, "opaque", f"xargs {s.prog} (targets come from input)"))
    for op, target in s.redirects:
        if target and target not in ("/dev/null", "/dev/stdout", "/dev/stderr") and not target.startswith("&"):
            w.append(Write(target, "write", "redirect"))
    if not s.argv:
        return w
    prog, args = s.prog, s.argv[1:]
    for a in args:
        # output-file flags of common tools: pytest --junitxml=…, -o=…, --output=…, --report=…
        m = re.match(r"^--?(junitxml|junit-xml|output|outfile|out|report|log-file|result-file|reports?-dir|coverage-xml|cov-report)=(.+)$", a)
        if m and "/" in m.group(2) or (m and "." in m.group(2)):
            w.append(Write(m.group(2).split(":", 1)[-1], "write", f"--{m.group(1)}="))
    if prog == "ditto":
        paths = _nonopts(args)
        if len(paths) >= 2:
            w.append(Write(paths[-1], "write", "ditto"))
    elif prog == "pax" and "-r" in args:
        w.append(Write(None, "opaque", "pax -r"))
    elif prog in ("sqlite3", "duckdb") and args:
        db = _nonopts(args)[:1]
        if db:
            w.append(Write(db[0], "write", prog))
    elif prog == "osascript" and re.search(r"do shell script|write|delete", " ".join(args), re.I):
        w.append(Write(None, "opaque", "osascript that runs shell commands or writes files"))
    if prog in ("cp", "install", "ln", "rsync", "scp"):
        paths = _nonopts(args)
        if len(paths) >= 2:
            w.append(Write(paths[-1], "write", prog))
            if prog == "ln":
                # a link pointing at a protected file is judged like writing that file
                link_dir = os.path.dirname(paths[-1])
                for p in paths[:-1]:
                    # a relative link target resolves from the link's own directory
                    tgt = p if os.path.isabs(p) or not link_dir else os.path.join(link_dir, p)
                    w.append(Write(tgt, "write", "ln target"))
    elif prog == "mv":
        paths = _nonopts(args)
        if len(paths) >= 2:
            w.append(Write(paths[-1], "write", "mv"))
            for p in paths[:-1]:
                w.append(Write(p, "delete", "mv"))
    elif prog in ("rm", "unlink", "rmdir", "shred", "srm"):
        for p in _nonopts(args):
            w.append(Write(p, "delete", prog))
    elif prog in ("touch", "truncate", "tee", "chmod", "chown", "chgrp", "setfacl", "xattr"):
        paths = _nonopts(args)
        if prog in ("chmod", "chown", "chgrp") and paths:
            paths = paths[1:]
        if prog == "truncate":
            paths = [p for p in paths]
        for p in paths:
            w.append(Write(p, "write", prog))
    elif prog == "dd":
        for a in args:
            if a.startswith("of="):
                w.append(Write(a[3:], "write", "dd"))
    elif prog in ("sed", "gsed", "perl") and any(a.startswith("-i") or a.startswith("-pi") or a == "--in-place" or a.startswith("--in-place=") for a in args):
        if "-i" in args:
            k = args.index("-i")
            if k + 1 < len(args) and args[k + 1] == "":
                args = args[:k + 1] + args[k + 2:]  # BSD/macOS: sed -i '' expr file
        if "-e" in args or "--expression" in args:
            # every -e takes the following word as a script, not a file
            cleaned, skip = [], False
            for a in args:
                if skip:
                    skip = False
                    continue
                if a in ("-e", "--expression"):
                    skip = True
                    continue
                cleaned.append(a)
            args = cleaned + ["-e"]
        paths = [p for p in _nonopts(args) if p != ""]
        # first non-option is the script unless -e was given
        has_e = "-e" in args or "--expression" in args
        files = paths if has_e else paths[1:]
        if not files:
            w.append(Write(None, "opaque", f"{prog} -i without a file"))
        for p in files:
            w.append(Write(p, "write", f"{prog} -i"))
    elif prog in ("awk", "gawk", "mawk", "nawk"):
        prog_text = " ".join(a for a in args if not a.startswith("-"))
        if ("-i" in args and "inplace" in args) or re.search(r"system\s*\(|print[f]?[^;{}]*>|\|\s*getline|\|&", prog_text):
            w.append(Write(None, "opaque", f"{prog} program that writes files or runs commands"))
    elif prog in ("vi", "vim", "nvim", "ex", "ed", "red", "emacs", "nano", "pico", "joe", "micro", "kak", "hx"):
        for p in _nonopts(args):
            if not p.startswith(("+", "-")):
                w.append(Write(p, "write", prog))
    elif prog in ("patch",):
        w.append(Write(None, "opaque", "patch"))
    elif prog in ("curl",):
        for flag in ("-o", "--output"):
            v = _flag_value(args, {flag})
            if v:
                w.append(Write(v, "write", "curl -o"))
        if "-O" in args or "--remote-name" in args:
            w.append(Write(None, "opaque", "curl -O"))
    elif prog in ("wget",):
        v = _flag_value(args, {"-O", "--output-document"})
        w.append(Write(v, "write", "wget") if v else Write(None, "opaque", "wget"))
    elif prog == "tar":
        first = args[0] if args else ""
        if "--extract" in args or "--get" in args or (first and not first.startswith("--") and "x" in first.lstrip("-")):
            w.append(Write(None, "opaque", "tar extract"))
    elif prog in ("unzip", "7z", "7za", "gunzip", "bunzip2", "unxz", "cpio", "rsync"):
        if prog != "rsync":
            w.append(Write(None, "opaque", f"{prog} extract"))
    elif prog == "find":
        if "-delete" in args:
            w.append(Write(None, "opaque", "find -delete"))
        for flag in ("-exec", "-execdir", "-ok", "-okdir"):
            if flag in args:
                i = args.index(flag)
                inner = args[i + 1] if i + 1 < len(args) else ""
                if os.path.basename(inner) not in READ_ONLY_PROGS:
                    w.append(Write(None, "opaque", f"find {flag} {os.path.basename(inner)}"))
    elif prog == "git":
        gopts, sub, sargs = git_split(s.argv)
        if sub in ("checkout", "restore") and "--" in sargs:
            for p in sargs[sargs.index("--") + 1:]:
                w.append(Write(p, "write", f"git {sub}"))
        elif sub == "restore":
            for p in _nonopts(sargs):
                w.append(Write(p, "write", "git restore"))
        elif sub in ("apply", "am"):
            if "--check" not in sargs and "--stat" not in sargs:
                w.append(Write(None, "opaque", f"git {sub}"))
        elif sub == "rm":
            for p in _nonopts(sargs):
                w.append(Write(p, "delete", "git rm"))
        elif sub == "mv":
            paths = _nonopts(sargs)
            if len(paths) >= 2:
                w.append(Write(paths[-1], "write", "git mv"))
                for p in paths[:-1]:
                    w.append(Write(p, "delete", "git mv"))
        elif sub == "clean" and any("f" in a for a in sargs if a.startswith("-")) and "-n" not in sargs and "--dry-run" not in sargs:
            w.append(Write(None, "opaque", "git clean -f"))
        elif sub == "reset" and "--hard" in sargs:
            w.append(Write(None, "opaque", "git reset --hard"))
        elif sub == "stash" and sargs[:1] in (["pop"], ["apply"]):
            w.append(Write(None, "opaque", f"git stash {sargs[0]}"))
    elif prog in INTERPRETERS:
        code = None
        for i, a in enumerate(args):
            if a in INLINE_FLAGS and i + 1 < len(args):
                code = args[i + 1]
                break
            if a == "-" or (a.startswith("-") and a[1:] and set(a[1:]) <= set("uBIEsSOq")):
                continue
        # `python3 - <<EOF` reads code from stdin (a heredoc); handled by caller.
        if code is not None and _WRITE_HINTS.search(code):
            w.append(Write(None, "opaque", f"{prog} inline code that writes files"))
        if prog.startswith("perl") and any(a.startswith("-i") or a.startswith("-pi") for a in args):
            w.append(Write(None, "opaque", "perl -i"))
    return w


def stdin_code(s):
    """An interpreter or shell reading its program from a file redirect, a pipe, a file
    descriptor or process substitution: the program is not visible to the gates."""
    if s.prog not in INTERPRETERS and s.prog not in SHELLS:
        return None
    for i, a in enumerate(s.argv[1:]):
        if a in INLINE_FLAGS and i + 2 <= len(s.argv[1:]) and ("$(" in s.argv[i + 2] or "`" in s.argv[i + 2]):
            return Write(None, "opaque", f"{s.prog} running code assembled at run time")
    if any(t in ("<&", "0<&") for t in s.raw.split()) or re.search(r"<&\s*\d|<\(", s.raw):
        return Write(None, "opaque", f"{s.prog} reading its program from a file descriptor")
    sc = script_execution(s)
    if sc and sc.startswith(("/dev/stdin", "/dev/fd/", "/proc/self/fd")):
        return Write(None, "opaque", f"{s.prog} reading its program from {sc}")
    if sc or any(a in INLINE_FLAGS or a in ("-m", "-n", "--version", "-V") for a in s.argv[1:]):
        return None
    script = script_execution(s)
    if script and (script.startswith(("/dev/stdin", "/dev/fd/", "/proc/self/fd", "<(", "(")) or script in ("-", "")):
        return Write(None, "opaque", f"{s.prog} reading its program from {script}")
    if s.stdin_file and s.stdin_file not in ("/dev/null", "HEREDOC"):
        return Write(None, "opaque", f"{s.prog} reading its program from {s.stdin_file}")
    if s.piped_in:
        return Write(None, "opaque", f"{s.prog} reading its program from a pipe")
    return None


def stdin_code_writes(s, heredoc_bodies):
    """`python3 - <<EOF ... EOF` style: inline code arrives via a heredoc."""
    if s.prog in INTERPRETERS and ("-" in s.argv[1:] or len(s.argv) == 1):
        for body in heredoc_bodies:
            if _WRITE_HINTS.search(body):
                return Write(None, "opaque", f"{s.prog} heredoc code that writes files")
    return None


# ------------------------------------------------------------ deploy analysis

DEPLOY_VERBS = {
    "kubectl": {"apply", "create", "replace", "patch", "delete", "rollout", "set", "scale", "edit", "run", "expose", "annotate", "label", "autoscale", "cordon", "drain", "taint"},
    "oc": {"apply", "create", "replace", "patch", "delete", "rollout", "set", "scale", "edit", "new-app", "start-build"},
    "helm": {"install", "upgrade", "rollback", "uninstall", "delete"},
    "helmfile": {"apply", "sync", "destroy", "deps"},
    "terraform": {"apply", "destroy", "import", "taint", "untaint", "state"},
    "tofu": {"apply", "destroy", "import", "taint", "untaint", "state"},
    "terragrunt": {"apply", "destroy", "run-all", "apply-all", "destroy-all"},
    "pulumi": {"up", "destroy", "update", "import", "refresh"},
    "cdk": {"deploy", "destroy"},
    "serverless": {"deploy", "remove"},
    "sls": {"deploy", "remove"},
    "eb": {"deploy", "terminate", "swap"},
    "fly": {"deploy", "scale", "secrets"},
    "flyctl": {"deploy", "scale", "secrets"},
    "argocd": {"app"},
    "flux": {"reconcile", "resume", "suspend"},
    "ansible-playbook": None,
    "vercel": None,
    "netlify": {"deploy"},
    "heroku": {"releases:rollback", "container:release", "ps:scale", "config:set", "pipelines:promote"},
    "firebase": {"deploy"},
    "wrangler": {"deploy", "publish"},
    "skaffold": {"run", "deploy", "apply"},
    "kustomize": set(),
    "copilot": {"deploy", "svc", "job", "env"},
    "sam": {"deploy", "sync"},
    "gcloud": None,
    "aws": None,
    "az": None,
    "func": {"azure"},
    "docker": {"stack", "service"},
    "nomad": {"run", "job"},
}
_CLOUD_DEPLOY = re.compile(r"(^|\s)(deploy|deployments?|create-deployment|update-service|update-function-code|"
                           r"update-stack|create-stack|execute-change-set|app\s+deploy|run\s+deploy|functions\s+deploy|"
                           r"builds\s+submit|set-image|rolling-action|swap-slot|slot\s+swap|releases\s+create|promote)(\s|$)")
_DEPLOY_SCRIPT = re.compile(r"(^|[/_.:-])(deploy|release|promote|rollout|ship)([/_.:-]|$)", re.I)


def deploy_invocation(s):
    """Return a short description if this simple command is a deployment, else None."""
    if not s.argv:
        return None
    prog, args = s.prog, s.argv[1:]
    words = [a for a in args if not a.startswith("-")]
    if prog in DEPLOY_VERBS:
        verbs = DEPLOY_VERBS[prog]
        if verbs is None:
            if prog in ("gcloud", "aws", "az"):
                if _CLOUD_DEPLOY.search(" ".join(words)):
                    return f"{prog} {' '.join(words[:3])}"
                return None
            if prog == "vercel":
                return "vercel" if ("--prod" in args or not words or words[0] in ("deploy", "promote", "alias")) else None
            return prog
        if verbs == set():
            return None
        if words and words[0] in verbs:
            return f"{prog} {words[0]}"
        return None
    if prog in ("make", "gmake", "just", "task", "mage", "rake", "invoke", "nx"):
        for wd in words:
            if _DEPLOY_SCRIPT.search(wd):
                return f"{prog} {wd}"
        return None
    if prog in ("npm", "pnpm", "yarn", "bun"):
        if words[:1] == ["run"] or prog in ("yarn", "pnpm", "bun"):
            target = words[1] if words[:1] == ["run"] and len(words) > 1 else (words[0] if words else "")
            if target and _DEPLOY_SCRIPT.search(target):
                return f"{prog} {target}"
        return None
    if prog == "gh":
        if words[:2] == ["workflow", "run"] and len(words) > 2 and _DEPLOY_SCRIPT.search(words[2]):
            return f"gh workflow run {words[2]}"
        if words[:2] == ["release", "create"]:
            return "gh release create"
        return None
    # A script whose own name says it deploys: ./deploy.sh, scripts/release, bin/promote-prod
    if (s.argv[0].startswith(("./", "../", "/")) or "/" in s.argv[0] or prog.endswith((".sh", ".py", ".rb", ".js", ".ps1"))) and _DEPLOY_SCRIPT.search(prog):
        return prog
    if prog in SHELLS or prog in INTERPRETERS:
        script = next((a for a in args if not a.startswith("-")), "")
        if script and _DEPLOY_SCRIPT.search(os.path.basename(script)):
            return os.path.basename(script)
    return None


def targets_production(s, prod_words):
    """True if the command names a production target, or its target can't be known."""
    pat = re.compile(r"(^|[^a-z0-9])(" + "|".join(re.escape(w) for w in prod_words) + r")([^a-z0-9]|$)", re.I)
    for tok in list(s.argv[1:]) + [f"{k}={v}" for k, v in s.env.items()]:
        if "$" in tok or "`" in tok:
            return True, "target is computed at run time and cannot be verified"
        if pat.search(tok):
            return True, f"names a production target ({tok})"
    return False, ""
