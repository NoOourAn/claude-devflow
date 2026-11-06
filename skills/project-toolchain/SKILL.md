---
name: project-toolchain
description: Determine the correct lint, typecheck, test, and build commands for whatever project you are in, by detection rather than assumption - and avoid commands that hang the session. Use before running any build/test/lint command, when a script fails as "missing", when a command appears to hang, or when working across multiple repos with different toolchains.
---

# Project Toolchain

Running the wrong command wastes a cycle. Running a **watch-mode** command hangs the session outright. Both are avoidable by checking before you run.

The rule: **detect, do not assume.** `npm test` means something different in almost every repo.

## Order of resolution

### 1. An explicit project config, if present

Look for `.claude/devflow.json` at the repo root. When it exists it is authoritative — it records what the maintainer knows that detection cannot infer:

```json
{
  "commands": {
    "lint": "npm run lint",
    "lint:fix": "npm run lint:fix",
    "typecheck": "npx tsc --noEmit -p tsconfig.json",
    "test": "npm run test:run",
    "build": "npm run build"
  },
  "avoid": ["npm test", "vitest"],
  "notes": ["`npm test` is bare vitest = watch mode, never exits"]
}
```

A `null` command means **that stage does not exist here** — skip it and say you skipped it. Do not substitute a guess, and do not scaffold the missing tool unless asked.

Anything listed in `avoid` must never be run.

### 2. Otherwise, detect from the manifest

Read the actual manifest rather than pattern-matching on the language:

| Ecosystem | Manifest | Where the commands live |
|---|---|---|
| Node | `package.json` | the `scripts` block — read it, do not guess names |
| Python | `pyproject.toml`, `tox.ini`, `Makefile` | `[tool.poetry.scripts]`, `[tool.ruff]`, tox envs |
| Go | `go.mod` | `go vet`, `go build ./...`, `go test ./...` |
| Rust | `Cargo.toml` | `cargo clippy`, `cargo check`, `cargo test` |
| Java/Kotlin | `pom.xml`, `build.gradle` | `mvn verify`, `./gradlew check` |
| Make-driven | `Makefile` | read the targets; `make lint` / `make test` often wrap everything |

For Node specifically, `scripts` is the source of truth. Do not run `npm run typecheck` because it is a common name — run it only if it is present in that file. If it is absent and the project is TypeScript, use `npx tsc --noEmit` with the project's own `tsconfig.json`.

Also check CI config (`.github/workflows/*.yml`, `.gitlab-ci.yml`). Whatever CI runs is the definition of "green" for that repo, and is usually the most reliable answer.

### 3. If detection is ambiguous

Ask, or run the narrowest safe thing and say what you assumed. Do not invent a command and report its failure as a code problem.

## Commands that hang

A watch-mode process never exits and will stall the session until it is killed. Check before running:

- `vitest` with no `run` subcommand — **watch mode**. Use `vitest run`.
- `jest --watch` / `--watchAll` — watch mode.
- `npm test` where the script is bare `vitest`, `jest --watch`, or similar — inherits the trap.
- `next dev`, `vite`, `react-native start`, `nodemon`, `webpack serve`, `tsc --watch` — long-running servers.
- `cargo watch`, `go run` on a server, `pytest-watch`.

If a long-running process is genuinely needed, run it in the background rather than in the foreground.

## Choosing what to run

Prefer the narrowest check that proves the change:

1. **Lint** the changed files only, not the whole tree.
2. **Typecheck** — usually whole-project by nature; accept that.
3. **Test** the changed test files plus tests covering changed modules. Full suite only when the mapping is unclear or the change is broad.

Skip **builds** during verification. They are slow and prove little that lint and typecheck did not. Build when the user asks, or when the change touches build config itself.

Watch out for lint scripts that carry `--fix`; they mutate the working tree. If the user wanted a read-only check, say that files were rewritten.

## Multiple repos

Never assume two repos share a toolchain, even in the same organisation and the same language. Resolve each independently, and report results per repo rather than merging them into one verdict.

Worktrees inherit their parent repo's toolchain. Resolve the repo root with `git rev-parse --show-toplevel` rather than inferring it from the directory name.

## Do not

- **Do not guess a script name.** Read `scripts` in the manifest. `npm run typecheck` exists in some projects and not others, and the "missing script" error looks like a real failure.
- **Do not run a watch-mode command in the foreground.** It never exits and the session stalls.
- **Do not scaffold a missing tool.** If a project has no test runner, that is information — report it, do not install vitest.
- **Do not report a stage as passing when it was skipped.** Skipped and passed are different outcomes.
- **Do not run a full suite when only a handful of files changed**, unless the mapping to affected tests is genuinely unclear.
- **Do not assume two repos share a toolchain**, even in the same org and language.
