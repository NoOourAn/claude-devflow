# devflow

A stack-agnostic plan → build → verify → ship workflow for [Claude Code](https://claude.com/claude-code).

It exists because the same three things go wrong in every repo:

1. Claude guesses a build command that does not exist, and reports the "missing script" error as if it were a real failure.
2. Claude runs a **watch-mode** command, which never exits, and the session hangs.
3. Lint errors are found at commit time instead of at edit time.

devflow fixes all three by **detecting** each project's real toolchain instead of assuming one.

## Install

```
/plugin marketplace add NoOourAn/claude-devflow
/plugin install devflow@devflow
```

Or, from a local clone:

```
/plugin marketplace add /path/to/claude-devflow
/plugin install devflow@devflow
```

## What you get

### Commands

| Command | What it does |
|---|---|
| `/devflow:verify` | Detects and runs the right lint, typecheck, and tests for whatever project you are in. Scopes to changed files. Skips stages that do not exist rather than inventing them. |
| `/devflow:ship` | Takes a ticket from plan to PR, across every repo it touches — including branch creation, verification, merge ordering, and cross-repo PR links. |
| `/devflow:spec` | Turns a rough idea or empty ticket into a proper spec, reading the code first. |
| `/devflow:qa` | Deploys current work to QA, waits for the pipeline, then smoke-tests it against the acceptance criteria. |

### Agents

| Agent | Use for |
|---|---|
| `frontend-reviewer` | Web frontend diffs — data-fetching correctness, effect bugs, design-system compliance, a11y, i18n/RTL, circular imports. |
| `mobile-reviewer` | Mobile diffs — offline and retry safety, idempotency, permission denial paths, platform differences, build flavors. |

Both detect the project's stack first and defer to its existing conventions.

### Hooks

| Hook | Effect |
|---|---|
| `PreToolUse(Bash)` | Blocks commands that would hang the session — bare `vitest`, `--watch` flags, `nodemon`, dev servers, Metro — including when reached through `npm test` or an inline `cd`. Suggests the non-watch equivalent. |
| `PostToolUse(Edit\|Write)` | Lints the file just edited and feeds real errors straight back, so they are fixed immediately instead of at commit time. Supports eslint, ruff, flake8, gofmt, and rubocop. |

Both hooks fail open: if anything goes wrong internally they exit 0 and stay out of the way.

### Skills

| Skill | What it carries |
|---|---|
| `project-toolchain` | How to resolve the correct commands for any ecosystem, and which commands hang. |
| `product-spec` | How to turn a rough idea into a specified ticket — code first, then scope, criteria, and open questions. |
| `work-artifacts` | The `.devflow/<ticket>/` convention that makes multi-session, multi-repo work resumable. |

### Resumable work

`/devflow:spec` and `/devflow:ship` persist their output to `.devflow/<ticket>/`:

```
.devflow/PROJ-123/
  spec.md      # the agreed spec
  plan.md      # per-repo plan, in merge order
  progress.md  # done / in flight / blocked, plus decisions and who made them
```

Both commands check that directory before starting, so a ticket picked up days later resumes instead of being re-derived. The tracker stays the source of truth for anything the team needs to see — these files exist so you can pick the thread back up.

`.devflow/` is working state. Add it to `.gitignore` unless your team agrees to commit it.

## Per-project configuration (optional)

Detection handles most projects. When a project has a trap that detection cannot infer, record it in `.claude/devflow.json` at the repo root:

```json
{
  "name": "my-app",
  "defaultBranch": "main",
  "commands": {
    "lint": "npm run lint",
    "lint:fix": "npm run lint:fix",
    "typecheck": "npx tsc --noEmit -p tsconfig.json",
    "test": "npm run test:run",
    "build": "npm run build"
  },
  "avoid": ["npm test", "vitest"],
  "notes": [
    "`npm test` is bare vitest = watch mode, never exits."
  ]
}
```

- `commands` — authoritative; overrides detection.
- A `null` command means **that stage does not exist here**. It is skipped and reported as skipped, not guessed at.
- `avoid` — commands the guard hook will refuse to run. A following non-flag subcommand is still allowed, so `"vitest"` blocks `npx vitest` but permits `npx vitest run`.
- `notes` — surfaced to Claude when it hits the guard.

Commit this file so the whole team benefits, not just you.

## Requirements

- Claude Code
- `python3` on PATH (both hooks are Python, so they work identically on macOS and Linux — no GNU `coreutils` dependency)

## License

MIT
