#!/usr/bin/env python3
"""PostToolUse(Edit|Write) hook: lint the file that was just edited.

Silent on success. On real lint errors, exit 2 so the message reaches Claude
and it can self-correct before moving on.

Stack-agnostic: picks a linter from the file extension and what the project
actually has installed. Any internal error exits 0 - a lint hook must never be
the reason an edit is rejected.
"""
import json
import os
import subprocess
import sys

TIMEOUT = 45
SKIP_DIRS = ("/node_modules/", "/dist/", "/build/", "/.git/", "/coverage/",
             "/vendor/", "/.venv/", "/__pycache__/", "/.next/")


def find_root(path):
    path = os.path.abspath(path)
    while True:
        if os.path.exists(os.path.join(path, ".git")):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            return None
        path = parent


def which(root, *candidates):
    """Prefer a project-local binary; fall back to one on PATH."""
    for c in candidates:
        local = os.path.join(root, "node_modules", ".bin", c)
        if os.path.isfile(local) and os.access(local, os.X_OK):
            return local
    for c in candidates:
        from shutil import which as _which
        found = _which(c)
        if found:
            return found
    return None


def build_cmd(root, path):
    """Return (argv, ok_codes) for linting one file, or None to skip."""
    ext = os.path.splitext(path)[1].lower()

    if ext in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"):
        b = which(root, "eslint")
        if b:
            return [b, "--quiet", "--format", "unix", path]

    elif ext == ".py":
        b = which(root, "ruff")
        if b:
            return [b, "check", "--quiet", path]
        b = which(root, "flake8")
        if b:
            return [b, path]

    elif ext == ".go":
        b = which(root, "gofmt")
        if b:
            return [b, "-l", path]

    elif ext == ".rb":
        b = which(root, "rubocop")
        if b:
            return [b, "--format", "emacs", "--force-exclusion", path]

    return None


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return

    path = (data.get("tool_input") or {}).get("file_path", "") or ""
    if not path or not os.path.isfile(path):
        return

    norm = path.replace(os.sep, "/")
    if any(d in norm for d in SKIP_DIRS):
        return

    root = find_root(os.path.dirname(path))
    if not root:
        return

    cmd = build_cmd(root, path)
    if not cmd:
        return

    try:
        proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True,
                              timeout=TIMEOUT)
    except Exception:
        # Timed out, or the linter is missing/misconfigured. Not the edit's fault.
        return

    if proc.returncode == 0:
        return

    out = ((proc.stdout or "") + (proc.stderr or "")).strip()
    if not out:
        return

    # A crashed or misconfigured linter usually exits >1 with no findings we
    # can act on. Only surface what looks like real per-file diagnostics.
    if proc.returncode > 1 and "\n" not in out:
        return

    rel = os.path.relpath(path, root)
    lines = out.splitlines()
    if len(lines) > 40:
        lines = lines[:40] + ["... (%d more)" % (len(out.splitlines()) - 40)]

    sys.stderr.write(
        "Lint errors in %s:\n%s\n\nFix these before continuing.\n"
        % (rel, "\n".join(lines)))
    sys.exit(2)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        pass
    sys.exit(0)
