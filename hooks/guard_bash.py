#!/usr/bin/env python3
"""PreToolUse(Bash) guard: block commands that hang the session in a watch/serve loop.

Works in any repo. Honours .claude/devflow.json "avoid" when present, then falls
back to resolving package.json scripts and detecting watch mode generically.

Exit 2 blocks the call and returns stderr to Claude. Exit 0 allows it.
Any internal error exits 0 - a guard must never be the reason work stops.
"""
import json
import os
import re
import sys

WATCH = [
    (r'(^|\s)(npx\s+)?vitest(\s|$)(?!.*(\brun\b|--run|--watch[= ]false))',
     "bare `vitest` starts WATCH mode and never exits. Use `vitest run`."),
    (r'--watchAll|--watch(?![=\w])',
     "this runs a watcher that never exits. Drop the watch flag."),
    (r'(^|\s)(npx\s+)?nodemon(\s|$)', "`nodemon` never exits."),
    (r'(^|\s)react-native\s+start(\s|$)',
     "`react-native start` runs the Metro bundler and never exits."),
    (r'(^|\s)(next|vite|webpack)\s+(dev|serve)(\s|$)',
     "this starts a dev server that never exits."),
    (r'(^|\s)cargo\s+watch(\s|$)', "`cargo watch` never exits."),
]

SKIP_SCRIPT_NAMES = {"install", "ci", "add", "exec", "publish", "link"}


def find_root(path):
    """Walk up to the enclosing repo root."""
    try:
        path = os.path.abspath(os.path.expanduser(path))
    except Exception:
        return None
    while True:
        if os.path.exists(os.path.join(path, ".git")):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            return None
        path = parent


def load(root):
    cfg, scripts = {}, {}
    if not root:
        return cfg, scripts
    try:
        p = os.path.join(root, ".claude", "devflow.json")
        if os.path.isfile(p):
            cfg = json.load(open(p)) or {}
    except Exception:
        pass
    try:
        p = os.path.join(root, "package.json")
        if os.path.isfile(p):
            scripts = (json.load(open(p)) or {}).get("scripts") or {}
    except Exception:
        pass
    return cfg, scripts


def deny(msg):
    sys.stderr.write(msg.strip() + "\n")
    sys.exit(2)


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    cmd = (data.get("tool_input") or {}).get("command", "") or ""
    if not cmd.strip():
        return

    # Explicit opt-outs: caller already bounded or backgrounded the process.
    if re.search(r'(^|\s)timeout\s', cmd) or re.search(r'&\s*$', cmd):
        return

    segments = [s.strip() for s in re.split(r'&&|\|\||;|\|', cmd) if s.strip()]

    root = data.get("cwd") or os.getcwd()
    root = find_root(root) or root

    # An inline `cd` changes which project later segments run in.
    for seg in segments:
        m = re.match(r'^cd\s+([^\s;]+)', seg)
        if m:
            target = m.group(1).strip("\"'")
            cand = find_root(target)
            if cand:
                root = cand

    cfg, scripts = load(root)

    # 1) Project-declared avoid list wins.
    for bad in (cfg.get("avoid") or []):
        bad = (bad or "").strip()
        if not bad:
            continue
        for seg in segments:
            m = re.search(r'(^|\s)' + re.escape(bad) + r'(\s|$)', seg)
            if not m:
                continue
            # `vitest run` is not `vitest`. A following non-flag token is a
            # subcommand that usually makes it safe - defer to detection below.
            rest = seg[m.end():].strip()
            if rest and not rest.startswith("-"):
                continue
            good = (cfg.get("commands") or {}).get("test")
            hint = " Use `%s` instead." % good if good else ""
            notes = " ".join(cfg.get("notes") or [])
            deny("Blocked: `%s` is on this project's .claude/devflow.json avoid "
                 "list.%s %s" % (bad, hint, notes))

    # 2) Generic watch/serve detection on the literal command.
    for seg in segments:
        for pat, msg in WATCH:
            if re.search(pat, seg):
                deny("Blocked: %s Run it in the background if you genuinely "
                     "need it." % msg)

    # 3) A package script that resolves to a watch command.
    if scripts:
        for seg in segments:
            m = re.search(r'(^|\s)(?:npm|yarn|pnpm)\s+(?:run\s+)?([\w:.-]+)', seg)
            if not m:
                continue
            name = m.group(2)
            if name in SKIP_SCRIPT_NAMES:
                continue
            body = scripts.get(name, "")
            if not body:
                continue
            for pat, msg in WATCH:
                if re.search(pat, body):
                    alt = next(
                        (k for k in ("%s:run" % name, "test:run", "test:ci")
                         if k in scripts and not any(
                             re.search(p, scripts[k]) for p, _ in WATCH)),
                        None)
                    hint = " Use `npm run %s` instead." % alt if alt else ""
                    deny("Blocked: `%s` resolves to `%s` - %s%s"
                         % (name, body, msg, hint))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        pass
    sys.exit(0)
