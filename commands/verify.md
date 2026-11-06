---
description: Detect and run the right lint, typecheck, and tests for this project
argument-hint: [--all] [--fix] [path-or-repo]
allowed-tools: Bash, Read, Grep, Glob, Skill
---

# Verify

Run the **correct** checks for whatever project this is, without you having to remember its toolchain.

Arguments: **$ARGUMENTS**

## Step 1 — Resolve the toolchain

Load the `project-toolchain` skill and follow its resolution order: `.claude/devflow.json` first, then the project's own manifest and CI config.

Do not guess command names. `npm run typecheck` exists in some projects and not others; running one that does not exist produces a "missing script" error that looks like a real failure and is not.

Resolve targets:

- No argument → the repo containing the current directory (`git rev-parse --show-toplevel`).
- A path or repo name → that project.
- `--all` → every repo under the current workspace with uncommitted changes or an unmerged branch. Resolve each one's toolchain **independently**.

## Step 2 — Scope to what changed

```bash
git diff --name-only $(git merge-base HEAD origin/HEAD)...HEAD
git status --porcelain
```

If nothing changed, say so and stop. Do not run a suite for no reason.

Narrow the work: lint only changed files; run test files that changed plus tests covering changed modules. Fall back to everything only when that mapping is unclear or `--all` was passed. Typecheck is whole-project by nature — that is fine.

## Step 3 — Run: lint → typecheck → test

Stop at the first hard failure so you report the root cause instead of a cascade of downstream noise.

Before each command, check it against the skill's watch-mode list. **A watch-mode command will hang the session** — if the resolved test command is bare `vitest`, `jest --watch`, or an `npm test` that wraps one, use the non-watch form instead.

If a stage does not exist in this project, skip it and say so explicitly. Never substitute a guess, and never scaffold a missing tool unless asked.

With `--fix`, use the project's fix variant where one exists, then re-run the stage to confirm it is clean.

Do not run builds. They are slow and prove little beyond lint and typecheck. Build only on request, or when the change touches build config itself.

## Step 4 — Report

One compact verdict per stage, per project:

```
web
  lint       PASS  (7 files)
  typecheck  FAIL  2 errors
  test       SKIP  (blocked by typecheck)

mobile-app
  lint       PASS  (2 files)
  typecheck  PASS
  test       SKIP  (no test runner configured)
```

For each failure give the `file:line`, the actual message, and the fix you propose. Extract the real errors — never paste hundreds of lines of raw output.

If everything passes, say so in one line without padding.

Fix failures only if asked, or if they are unambiguous mechanical errors from work you did earlier this session. Anything ambiguous: report it and ask.

Report honestly. A failing suite described as passing is worse than not running it.
