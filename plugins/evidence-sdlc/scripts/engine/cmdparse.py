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
        self.heredocs = []  # indexes into split_simple's heredoc bodies fed to this command's stdin

    @property
    def prog(self):
        return os.path.basename(self.argv[0]) if self.argv else ""


def _tokenize(cmd):
    """shlex over text that _scan has already prepared: comments removed (shlex would also end a
    word like `a#b` at the `#` and drop the rest of the line), heredoc bodies replaced by markers,
    line continuations joined and newlines turned into `;`."""
    lex = shlex.shlex(cmd, posix=True, punctuation_chars=";&|()<>")
    lex.whitespace_split = True
    lex.commenters = ""
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
# A heredoc body is replaced by this marker (the word after `<<`), so a rescan of the text (a
# command substitution is parsed again on its own) does not look for the body a second time.
_HEREDOC_MARK = "__EVIDENCE_HEREDOC_{}__"
_HEREDOC_MARK_RE = re.compile(r"__EVIDENCE_HEREDOC_(\d+)__")
_META = set(" \t\n;&|()<>")


class _Scanner:
    """A shell lexer for what the gates need (PILOT-59, REQ-CON-15). It walks the command once,
    tracking quotes, escapes, `$( )`, `${ }`, `$(( ))`, backticks, process substitution and
    heredocs, and returns the command text with:
      - comments removed (a `#` at the start of a word, to the end of the line);
      - `\\` + newline joined, as the shell does outside single quotes;
      - every newline in command context turned into a `;` separator, unless the line ends in an
        operator that continues onto the next line (`|`, `&&`, `||`, `(`);
      - each heredoc body removed (it is data) and recorded, while the rest of the operator's line
        (`| sh`, `&& touch x`, `> f`, a second heredoc) is kept; `<<<` is a here-string;
      - each process substitution `<( )` / `>( )` replaced by a quoted placeholder word, its
        inside recorded to be parsed as a command of its own.
    Command substitutions `$( )` and backticks are recorded too (their text stays in place), as
    are the substitutions inside an unquoted heredoc body, which the shell expands. Anything it
    cannot place (an unterminated quote or substitution) clears `ok`."""

    def __init__(self, src, bodies):
        self.s, self.n, self.i = src, len(src), 0
        self.bodies = bodies
        self.subs = []        # [(kind, inner text)] for kind in "$(", "`", "<(", ">("
        self.pending = []     # heredocs whose bodies start after the next newline
        self.ok = True

    # -- helpers
    def _peek(self, k=1):
        return self.s[self.i + k] if self.i + k < self.n else ""

    @staticmethod
    def _last_char(out):
        for piece in reversed(out):
            if piece:
                return piece[-1]
        return ""

    @staticmethod
    def _last_significant(out):
        for piece in reversed(out):
            t = piece.rstrip(" \t\n")
            if t:
                return t[-1]
        return ""

    # -- contexts
    def cmd(self, level, nested):
        """Command context. `nested` ends at the `)` that closes a substitution; level 0 is the
        text this scanner was asked about, deeper levels are copied for a later rescan."""
        out, pdepth = [], 0
        s = self.s
        while self.i < self.n:
            c = s[self.i]
            nxt = self._peek()
            if c == "\\":
                if nxt == "\n":
                    self.i += 2  # line continuation
                    continue
                out.append(s[self.i:self.i + 2])
                self.i += 2
                continue
            if c == "'":
                j = s.find("'", self.i + 1)
                if j < 0:
                    self.ok = False
                    out.append(s[self.i:])
                    self.i = self.n
                    break
                out.append(s[self.i:j + 1])
                self.i = j + 1
                continue
            if c == '"':
                out.append(self.dq(level))
                continue
            if c == "`":
                out.append(self.backtick(level))
                continue
            if c == "$" and nxt == "'":
                out.append(self.ansi())
                continue
            if c == "$" and nxt == "(" and self._peek(2) == "(":
                out.append(self.arith(3, "$(("))
                continue
            if c == "$" and nxt == "(":
                out.append(self.comsub(level))
                continue
            if c == "$" and nxt == "{":
                out.append(self.brace(level))
                continue
            if c == "(" and nxt == "(" and self._last_char(out) in ("",) + tuple(_META):
                out.append(self.arith(2, "(("))  # `(( x << 2 ))`: arithmetic, not a heredoc
                continue
            if c in "<>" and nxt == "(":
                self.i += 2
                inner = self.cmd(level + 1, nested=True)
                if level == 0:
                    self.subs.append((c + "(", inner))
                    out.append(f"'{c}(PROCSUB)'")
                else:
                    out.append(c + "(" + inner + ")")
                continue
            if c == "<" and nxt == "<" and self._peek(2) == "<":
                out.append("<<<")
                self.i += 3
                continue
            if c == "<" and nxt == "<":
                out.append(self.heredoc_op(nested))
                continue
            if c == "#" and self._last_char(out) in ("",) + tuple(_META):
                j = s.find("\n", self.i)
                self.i = self.n if j < 0 else j
                continue
            if c == "\n":
                self.i += 1
                last = self._last_significant(out)
                if self.pending:
                    self.read_bodies(nested)
                out.append("\n" if last in ("", "|", "&", ";", "(") else "\n;")
                continue
            if nested:
                if c == "(":
                    pdepth += 1
                elif c == ")":
                    if pdepth == 0:
                        self.i += 1
                        return "".join(out)
                    pdepth -= 1
            out.append(c)
            self.i += 1
        if nested:
            self.ok = False  # the substitution never closed
        return "".join(out)

    def dq(self, level):
        s, out = self.s, ['"']
        self.i += 1
        while self.i < self.n:
            c, nxt = s[self.i], self._peek()
            if c == "\\":
                if nxt == "\n":
                    self.i += 2
                    continue
                out.append(s[self.i:self.i + 2])
                self.i += 2
                continue
            if c == '"':
                out.append('"')
                self.i += 1
                return "".join(out)
            if c == "`":
                out.append(self.backtick(level))
                continue
            if c == "$" and nxt == "(" and self._peek(2) == "(":
                out.append(self.arith(3, "$(("))
                continue
            if c == "$" and nxt == "(":
                out.append(self.comsub(level))
                continue
            if c == "$" and nxt == "{":
                out.append(self.brace(level))
                continue
            out.append(c)
            self.i += 1
        self.ok = False
        return "".join(out)

    def ansi(self):
        s, start = self.s, self.i
        self.i += 2
        while self.i < self.n:
            if s[self.i] == "\\":
                self.i += 2
                continue
            if s[self.i] == "'":
                self.i += 1
                return s[start:self.i]
            self.i += 1
        self.ok = False
        return s[start:]

    def backtick(self, level):
        s, raw = self.s, []
        self.i += 1
        while self.i < self.n:
            c = s[self.i]
            if c == "\\" and self.i + 1 < self.n:
                nxt = s[self.i + 1]
                raw.append(nxt if nxt in "`\\$" else c + nxt)
                self.i += 2
                continue
            if c == "`":
                self.i += 1
                inner = "".join(raw)
                if level == 0:
                    self.subs.append(("`", inner))
                return "`" + inner.replace("`", "\\`") + "`"
            raw.append(c)
            self.i += 1
        self.ok = False
        return "`" + "".join(raw)

    def comsub(self, level):
        self.i += 2
        inner = self.cmd(level + 1, nested=True)
        if level == 0:
            self.subs.append(("$(", inner))
        return "$(" + inner + ")"

    def brace(self, level):
        s, out = self.s, ["${"]
        self.i += 2
        while self.i < self.n:
            c, nxt = s[self.i], self._peek()
            if c == "\\":
                out.append(s[self.i:self.i + 2])
                self.i += 2
                continue
            if c == "'":
                j = s.find("'", self.i + 1)
                if j < 0:
                    break
                out.append(s[self.i:j + 1])
                self.i = j + 1
                continue
            if c == '"':
                out.append(self.dq(level))
                continue
            if c == "`":
                out.append(self.backtick(level))
                continue
            if c == "$" and nxt == "(":
                out.append(self.comsub(level))
                continue
            if c == "$" and nxt == "{":
                out.append(self.brace(level))
                continue
            if c == "}":
                out.append("}")
                self.i += 1
                return "".join(out)
            out.append(c)
            self.i += 1
        self.ok = False
        return "".join(out)

    def arith(self, width, opener):
        """`$(( ))` or `(( ))`: copied as is; a `$( )` inside still runs, so it is recorded."""
        s, out, depth = self.s, [opener], 2
        self.i += width
        while self.i < self.n:
            c = s[self.i]
            if c == "$" and self._peek() == "(" and self._peek(2) != "(":
                out.append(self.comsub(0))
                continue
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    out.append(c)
                    self.i += 1
                    return "".join(out)
            out.append(c)
            self.i += 1
        self.ok = False
        return "".join(out)

    def heredoc_op(self, nested):
        s = self.s
        self.i += 2
        strip_tabs = self.i < self.n and s[self.i] == "-"
        if strip_tabs:
            self.i += 1
        while self.i < self.n and s[self.i] in " \t":
            self.i += 1
        delim, quoted = [], False
        while self.i < self.n and s[self.i] not in _META:
            c = s[self.i]
            if c in "'\"":
                j = s.find(c, self.i + 1)
                if j < 0:
                    self.ok = False
                    self.i = self.n
                    break
                delim.append(s[self.i + 1:j])
                quoted = True
                self.i = j + 1
                continue
            if c == "\\" and self.i + 1 < self.n:
                delim.append(s[self.i + 1])
                quoted = True
                self.i += 2
                continue
            delim.append(c)
            self.i += 1
        word = "".join(delim)
        if not word:
            self.ok = False
            return "<<"
        if _HEREDOC_MARK_RE.fullmatch(word):
            return "<< " + word  # already scanned: its body was removed before
        idx = len(self.bodies)
        self.bodies.append("")
        self.pending.append((idx, word, strip_tabs, quoted))
        return "<< " + _HEREDOC_MARK.format(idx)

    def read_bodies(self, nested):
        """Read the pending heredocs' bodies, in order, from the line after their operators. A
        body ends at a line that is exactly its word (leading tabs dropped for `<<-`); spaces
        around it are tolerated, which ends bodies no later than the shell does. Inside a command
        substitution `WORD)` also ends it. A body with no end runs to the end of the text, as in
        bash."""
        s = self.s
        pending, self.pending = self.pending, []
        for idx, word, strip_tabs, quoted in pending:
            lines = []
            while self.i < self.n:
                j = s.find("\n", self.i)
                end = self.n if j < 0 else j
                line = s[self.i:end]
                probe = (line.lstrip("\t") if strip_tabs else line).strip()
                if probe == word:
                    self.i = end + 1 if j >= 0 else self.n
                    break
                if nested and probe.startswith(word) and probe[len(word):].lstrip().startswith(")"):
                    self.i += line.index(word) + len(word)  # the `)` closes the substitution
                    break
                lines.append(line)
                self.i = end + 1 if j >= 0 else self.n
            body = "\n".join(lines)
            self.bodies[idx] = body
            if not quoted:
                # an unquoted body is expanded by the shell: its $( ) and backticks run
                sub = _Scanner(body, self.bodies)
                sub.dq_body()
                self.subs.extend(sub.subs)
                self.ok = self.ok and sub.ok

    def dq_body(self):
        """An unquoted heredoc body: like the inside of double quotes, with no closing quote."""
        s = self.s
        while self.i < self.n:
            c, nxt = s[self.i], self._peek()
            if c == "\\":
                self.i += 2
                continue
            if c == "`":
                self.backtick(0)
                continue
            if c == "$" and nxt == "(" and self._peek(2) == "(":
                self.arith(3, "$((")
                continue
            if c == "$" and nxt == "(":
                self.comsub(0)
                continue
            if c == "$" and nxt == "{":
                self.brace(0)
                continue
            self.i += 1


def _scan(cmd, bodies):
    """(prepared text, substitutions, ok) for one level of a command; see _Scanner."""
    sc = _Scanner(cmd, bodies)
    text = sc.cmd(0, nested=False)
    if sc.pending:  # a heredoc operator on the last line: its body is empty
        sc.read_bodies(False)
    return text, sc.subs, sc.ok


def _strip_heredocs(cmd):
    """The command text as the parser reads it (see _Scanner), and the heredoc bodies."""
    bodies = []
    text, _subs, _ok = _scan(cmd, bodies)
    return text, bodies


def split_simple(cmd, _depth=0, _bodies=None):
    """Return (simples, ok, heredoc_bodies). Recurses into $(...), `...`, <(...), >(...), sh -c,
    and a shell reading a heredoc. Nested calls share the top level's heredoc list."""
    if _depth > 4:
        return [], False, []
    bodies = [] if _bodies is None else _bodies
    cmd, subs, scan_ok = _scan(cmd, bodies)
    # the scanner's substitutions, plus the old textual match (which also finds `$(` inside
    # single quotes: parsing more than the shell runs only ever judges more)
    inner_cmds = list(dict.fromkeys([m.group(1) or m.group(2) for m in _SUBST.finditer(cmd)]
                                    + [t for k, t in subs if k in ("$(", "`")]))
    procs = [(k, t) for k, t in subs if k in ("<(", ">(")]
    tokens, ok = _tokenize(cmd)
    ok = ok and scan_ok

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
    own = list(simples)

    def recurse(text, piped=False):
        nonlocal ok
        sub, sub_ok, _ = split_simple(text, _depth + 1, bodies)
        if piped and sub:
            sub[0].piped_in = True  # `>(cmd)`: cmd reads what the outer command writes
        simples.extend(sub)
        ok = ok and sub_ok

    # Recurse into command substitutions, process substitutions and shell -c payloads.
    for inner in inner_cmds:
        recurse(inner)
    for kind, inner in procs:
        recurse(inner, piped=kind == ">(")
    for s in own:
        if s.prog in SHELLS:
            payload = _flag_value(s.argv[1:], {"-c"})
            if payload:
                recurse(payload)
        if (s.prog in SHELLS or s.prog in ("source", ".")) and s.heredocs and _reads_stdin_program(s):
            # `bash <<EOF … EOF`, `. /dev/stdin <<EOF`: the body is the program; judge its commands
            for idx in s.heredocs:
                if 0 <= idx < len(bodies):
                    recurse(bodies[idx])
        if s.prog in ("export", "declare", "typeset", "readonly"):
            for a in s.argv[1:]:
                if "=" in a and not a.startswith("-"):
                    k, v = a.split("=", 1)
                    s.env[k] = v
        if s.prog == "alias":
            for a in s.argv[1:]:
                if "=" in a:
                    recurse(a.split("=", 1)[1])
        if s.prog == "eval":
            recurse(" ".join(s.argv[1:]))
    return simples, ok, (bodies if _bodies is None else [])


_STDIN_PATHS = ("/dev/stdin", "/dev/fd/0", "/proc/self/fd/0")


def _reads_stdin_program(s):
    """True when a shell (or `source`) takes its program from standard input: no -c, and no
    script operand other than /dev/stdin."""
    if s.prog in ("source", "."):
        return bool(s.argv[1:]) and s.argv[1] in _STDIN_PATHS
    if _flag_value(s.argv[1:], {"-c"}) is not None:
        return False
    sc = script_execution(s)
    return sc is None or sc in _STDIN_PATHS


def _flag_value(args, flags):
    for i, a in enumerate(args):
        if a in flags and i + 1 < len(args):
            return args[i + 1]
    return None


def _make_simple(tokens):
    env, argv, redirects = {}, [], []
    stdin_file = None
    heredocs = []
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
        if t == "<<" and i + 1 < len(tokens):
            m = _HEREDOC_MARK_RE.fullmatch(tokens[i + 1])
            if m:
                heredocs.append(int(m.group(1)))
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
    s = Simple(argv, env, redirects, " ".join(tokens), via_xargs, stdin_file, wrappers)
    s.heredocs = heredocs
    return s


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


def _target_directory(prog, args):
    """(DIR, source operands) when cp/mv/install/ln is given -t DIR in any form (`-t DIR`, `-tDIR`,
    a cluster ending in t such as `-rt DIR`, `--target-directory[=]DIR` or an abbreviation of it),
    else (None, [])."""
    if prog not in ("cp", "mv", "install", "ln"):
        return None, []
    tdir, rest, i = None, [], 0
    while i < len(args):
        a = args[i]
        nxt = args[i + 1] if i + 1 < len(args) else None
        if a == "--":
            rest.extend(args[i + 1:])
            break
        if a.startswith("--t") and "--target-directory".startswith(a.split("=", 1)[0]):
            if "=" in a:
                tdir = a.split("=", 1)[1]
            else:
                tdir, i = nxt, i + 1
        elif re.fullmatch(r"-[A-Za-z]*t.*", a) and not a.startswith("--"):
            k = a.index("t")
            if a[k + 1:]:
                tdir = a[k + 1:]
            else:
                tdir, i = nxt, i + 1
        elif not a.startswith("-") or a == "-":
            rest.append(a)
        i += 1
    return (tdir, rest) if tdir else (None, [])


# curl: options whose value is a file curl writes, options that make it write where something else
# says (a config file, the URL's own name), and the short options that take a value (so a cluster
# such as `-sKcfg` or `-osrc/x` is read as the shell hands it to curl). PILOT-60 review P5.
_CURL_WRITE_OPTS = {"-o": "--output", "-c": "--cookie-jar", "-D": "--dump-header"}
_CURL_WRITE_LONG = ("--output", "--cookie-jar", "--dump-header", "--trace", "--trace-ascii", "--stderr", "--libcurl",
                    "--etag-save", "--hsts", "--alt-svc")
_CURL_OPAQUE_LONG = ("--config", "--remote-name", "--remote-name-all", "--output-dir", "--create-dirs")
_CURL_VALUE_SHORT = set("oKcDdHuXeAbTwxrmECFYyzQtPU")


def _long_opt(arg, names):
    """The option in `names` that `arg` (`--name` or `--name=value`) spells, allowing a unique-looking
    prefix of at least four letters (`--conf` for --config), or None."""
    name = arg.split("=", 1)[0]
    if name in names:
        return name
    hits = [n for n in names if len(name) >= 6 and n.startswith(name)]
    return hits[0] if hits else None


def _curl_writes(args):
    w, i = [], 0
    while i < len(args):
        a = args[i]
        nxt = args[i + 1] if i + 1 < len(args) else None
        if a.startswith("--"):
            wl, ol = _long_opt(a, _CURL_WRITE_LONG), _long_opt(a, _CURL_OPAQUE_LONG)
            val = a.split("=", 1)[1] if "=" in a else nxt
            if ol:
                w.append(Write(None, "opaque", f"curl {ol}"))
            elif wl and val:
                w.append(Write(val, "write", f"curl {wl}"))
            if (wl or ol in ("--config", "--output-dir")) and "=" not in a:
                i += 1
        elif a.startswith("-") and len(a) > 1:
            for j, ch in enumerate(a[1:], 1):
                if ch == "O":
                    w.append(Write(None, "opaque", "curl -O"))
                    continue
                if ch in _CURL_VALUE_SHORT:
                    val = a[j + 1:] or nxt
                    if ch == "K":
                        w.append(Write(None, "opaque", "curl -K (a config file can name any output)"))
                    elif "-" + ch in _CURL_WRITE_OPTS and val:
                        w.append(Write(val, "write", f"curl -{ch}"))
                    if not a[j + 1:]:
                        i += 1
                    break
        i += 1
    return w


def _wget_writes(args):
    """wget writes the URL's own name unless -O names the file; -e/--execute, -i/--input-file, --config
    and -P make what it writes, or where, come from somewhere else."""
    w, out, i = [], None, 0
    while i < len(args):
        a = args[i]
        nxt = args[i + 1] if i + 1 < len(args) else None
        if a.startswith("--"):
            name = a.split("=", 1)[0]
            val = a.split("=", 1)[1] if "=" in a else nxt
            if _long_opt(a, ("--execute", "--input-file", "--config", "--directory-prefix")):
                w.append(Write(None, "opaque", f"wget {name}"))
            elif _long_opt(a, ("--output-document",)):
                out = val
            elif _long_opt(a, ("--output-file", "--append-output")) and val:
                w.append(Write(val, "write", f"wget {name}"))
            if "=" not in a and _long_opt(a, ("--execute", "--input-file", "--config", "--directory-prefix",
                                                "--output-document", "--output-file", "--append-output")):
                i += 1
        elif a.startswith("-") and len(a) > 1:
            for j, ch in enumerate(a[1:], 1):
                if ch in "eiP":
                    w.append(Write(None, "opaque", f"wget -{ch}"))
                if ch in "eiPOoa":
                    val = a[j + 1:] or nxt
                    if ch == "O":
                        out = val
                    elif ch in "oa" and val:
                        w.append(Write(val, "write", f"wget -{ch}"))
                    if not a[j + 1:]:
                        i += 1
                    break
        i += 1
    w.append(Write(out, "write", "wget") if out else Write(None, "opaque", "wget"))
    return w


# Programs that never write a file named by one of their arguments: their only writes are
# redirects, judged on their own. Any other program's path arguments are possible writes
# (PILOT-60 review C2), judged by evidence_policy against the control plane and the claims.
PURE_READERS = frozenset({
    "cat", "head", "tail", "wc", "ls", "stat", "file", "echo", "printf", "test", "[", "[[", "basename", "dirname",
    "realpath", "readlink", "md5sum", "md5", "sha1sum", "sha256sum", "sha512sum", "shasum", "b2sum", "cksum", "diff",
    "cmp", "comm", "cut", "paste", "nl", "column", "grep", "egrep", "fgrep", "rg", "jq", "true", "false", "pwd", "which",
    "type", "sleep", "date", "whoami", "id", "uname", "hostname", "tree", "du", "df", "less", "more", "od", "hexdump",
    "strings", "tr", "expr", "seq", "cd", "pushd", "popd", "git", "gh", "evidence", "mktemp", "exit", "return", "wait",
    "unset", "read", "shift", "local", "set", "export", "declare", "typeset", "readonly", "alias", "hash", "fold",
    "wait", "tput", "clear"})
_SED_S_BODY = re.compile(r"s/(?:[^/\\\n]|\\.)*/(?:[^/\\\n]|\\.)*/")
_SED_ADDR = re.compile(r"/(?:[^/\\\n]|\\.)*/")


def may_write_args(s):
    """False when s cannot write a file named by one of its arguments (C2): a pure reader, a sed
    without -i, -f or a w/W/e command, an awk with no -f and nothing writes_of flags, a find with
    no -delete, -exec*, -ok*, -fprint* or -fls."""
    prog, args = s.prog, s.argv[1:]
    if prog in PURE_READERS:
        return False
    if prog in ("sed", "gsed"):
        scripts, has_e, skip = [], False, False
        for k, a in enumerate(args):
            if skip:
                skip = False
                continue
            if a in ("-e", "--expression"):
                if k + 1 < len(args):
                    scripts.append(args[k + 1])
                has_e, skip = True, True
            elif a.startswith("--expression="):
                scripts.append(a.split("=", 1)[1])
                has_e = True
            elif a.startswith(("-i", "--in-place", "-f", "--file")) or (
                    re.fullmatch(r"-[A-Za-z]+", a) and set(a[1:]) & set("if")):
                return True
        if not has_e:
            ops = [a for a in args if not a.startswith("-")]
            scripts = ops[:1]
        for sc in scripts:
            body = _SED_ADDR.sub("//", _SED_S_BODY.sub("s///", sc))
            if re.search(r"[wWe]", body):
                return True
        return False
    if prog in ("awk", "gawk", "mawk", "nawk"):
        return any(a == "-f" or a.startswith("--file") for a in args) or bool(_writes_of(s))
    if prog == "find":
        return any(a in ("-delete", "-exec", "-execdir", "-ok", "-okdir", "-fprint", "-fprint0", "-fprintf", "-fls")
                   for a in args)
    return True


def writes_of(s):
    """File-system writes performed by one simple command. A process substitution operand
    (`tee >(sh)`, `> >(sh)`) is a pipe, not a file: its command is parsed and judged on its own."""
    return [x for x in _writes_of(s) if not (x.path or "").startswith(("<(", ">("))]


def _writes_of(s):
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
    target_dir, srcs = _target_directory(prog, args)
    if target_dir is not None:
        # `cp -t DIR a b`, `mv --target-directory=DIR a`, `cp -rt DIR a` (PILOT-60 review P3): every operand
        # is a source, and each lands in DIR under its own name
        for p in srcs:
            w.append(Write(os.path.join(target_dir, os.path.basename(p.rstrip("/")) or p), "write", f"{prog} -t"))
            if prog == "mv":
                w.append(Write(p, "delete", "mv"))
    elif prog in ("cp", "install", "ln", "rsync", "scp"):
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
        w.extend(_curl_writes(args))
    elif prog in ("wget",):
        w.extend(_wget_writes(args))
    elif prog == "uniq":
        # uniq [opts] [input [output]]: the second operand is written (PILOT-60 review C2)
        ops, skip = [], False
        for a in args:
            if skip:
                skip = False
                continue
            if a in ("-f", "-s", "-w", "--skip-fields", "--skip-chars", "--check-chars"):
                skip = True
                continue
            if a.startswith("-") and a != "-":
                continue
            ops.append(a)
        if len(ops) >= 2 and ops[1] != "-":
            w.append(Write(ops[1], "write", "uniq output"))
    elif prog == "sponge":
        for p in _nonopts(args):
            w.append(Write(p, "write", "sponge"))
    elif prog in ("sort", "gsort"):
        for k, a in enumerate(args):
            if a in ("-o", "--output") and k + 1 < len(args):
                w.append(Write(args[k + 1], "write", "sort -o"))
            elif a.startswith("--output="):
                w.append(Write(a.split("=", 1)[1], "write", "sort -o"))
            elif re.fullmatch(r"-[A-Za-z]*o.+", a) and not a.startswith("--"):
                w.append(Write(a[a.index("o") + 1:], "write", "sort -o"))
            elif re.fullmatch(r"-[A-Za-z]*o", a) and k + 1 < len(args):
                w.append(Write(args[k + 1], "write", "sort -o"))
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
    if s.prog in ("source", "."):
        # `source <(…)`, `. /dev/stdin`, `. /dev/fd/3`: the sourced program is not a file the gates can read
        # (a heredoc fed to /dev/stdin is parsed as commands by split_simple instead)
        sc = s.argv[1] if len(s.argv) > 1 else ""
        if sc.startswith(("<(", ">(", "/dev/fd/", "/proc/self/fd")) or (sc in _STDIN_PATHS and not s.heredocs):
            return Write(None, "opaque", f"{s.prog} reading its program from {sc}")
        return None
    if s.prog not in INTERPRETERS and s.prog not in SHELLS:
        return None
    if s.prog in SHELLS and s.heredocs and _reads_stdin_program(s) and not s.piped_in:
        return None  # the heredoc is the program, and split_simple parsed its commands
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
