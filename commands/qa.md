---
description: Deploy the current work to QA, wait for the pipeline, then smoke-test it in the real environment
argument-hint: [ticket-id] [--no-test] [--repos a,b]
allowed-tools: Bash, Read, Grep, Glob, TodoWrite, Skill, WebFetch, Agent, mcp__*
---

# QA

Get the current work onto QA and **prove it actually works there** — not just that the pipeline went green.

Target: **$ARGUMENTS**

## Step 1 — Work out what ships

Load `work-artifacts` and check `.devflow/<ticket>/` for what was built and in which repos. Otherwise infer from the current branch across repos.

Determine the QA branch and which repos actually have a QA deploy path. **A repo with no QA pipeline must be skipped and reported as skipped** — never imply something deployed when nothing did.

If a project skill documents the QA environment (URLs, logins, which repos deploy), load it and use it rather than guessing. `--repos` narrows the set explicitly.

Confirm the repo list and what will happen before pushing anything. Deploying is outward-facing: say which branches you are about to move, then proceed.

## Step 2 — Merge and push

For each repo, in the same dependency order used to merge the PRs (schema/API first):

```bash
git -C <repo> fetch origin
git -C <repo> checkout <qa-branch>
git -C <repo> pull --ff-only origin <qa-branch>
git -C <repo> merge <feature-branch>
git -C <repo> push origin <qa-branch>
```

If the QA branch has drifted far behind and the merge conflicts heavily, merge `origin/<default-branch>` into the QA branch **first**, then merge the feature branch. Say that you did.

**Never force-push a shared deploy branch.** If a merge conflicts in a way you cannot resolve confidently, stop, leave the branch untouched, and report exactly which files conflict. A wrong conflict resolution on a shared QA branch is worse than a failed deploy.

## Step 3 — Wait for the pipeline

Watch the run each push triggered, per repo:

```bash
gh run list --repo <org/repo> --branch <qa-branch> --limit 1
gh run watch <run-id> --repo <org/repo>
```

Poll rather than blocking indefinitely, and report which repos are still building. If a run **fails**, stop here — pull the failing step's log, give the actual error, and do not proceed to testing. A smoke test against a stale deploy produces a confident false pass, which is the worst possible outcome.

Wait for the deploy to be genuinely live before testing. A green pipeline can precede propagation — for a CDN-backed SPA the invalidation needs to land, for a rolling service the new tasks need to be serving.

## Step 4 — Smoke-test against the acceptance criteria

Stop unless every relevant pipeline is green.

Drive the real environment in a browser. Take the **ticket's acceptance criteria as the test plan** — each criterion is one check. This is scoped smoke-testing, not regression: test what this change claims to do.

For each criterion, record what you did, what you expected, and what actually happened. Cover the negative cases the criteria specify (blocked submission, rejected input, hidden-when-flag-off) — those are where real bugs live, and they are the ones that get skipped.

Capture a screenshot for anything visual, so the result is evidence rather than assertion.

Skip with `--no-test` when you only want the deploy.

**Report failures honestly.** A criterion that fails is the entire point of running this. Never soften it, and never mark something verified that you could not actually reach.

### When the UI is not reachable, test at the API and the database

A blocked frontend deploy, a missing login, a criterion with no visible surface — none of these mean "unverified". Drop a layer instead of giving up:

- **Call the API directly.** Introspect the deployed schema to prove the build actually landed, then exercise the mutation the criterion is about. This is often *stronger* evidence than clicking, because you control the exact actor and payload.
- **Query the database** for what the UI would have shown you: the row that was written, the flag it was written with, the notification that was or was not queued.
- **Check the seed data before trusting a negative result.** "I could not find a user in that role" is a finding about the environment, not a pass. A permission test against an account that happens to be an admin proves nothing.

If a project skill documents QA credentials, use them. Credentials belong in a file **outside every git repo** (e.g. `~/.claude/devflow/qa-db.env`, `chmod 600`) and are referenced by path — never pasted into a command, a skill, or any tracked file. `scripts/qa-db.mjs` in this repo reads that file and refuses non-`SELECT` statements unless given `--write`, because QA is shared.

Writing to QA is sometimes legitimate — issuing yourself a login code, seeding a fixture the criteria need. Keep it minimal, reversible, and say in the report exactly what you wrote and whether you cleaned it up.

**A criterion tested at the data layer is verified.** Say which layer you used, so the reader knows a green check means the API returned 403 rather than that a button looked disabled.

## Step 5 — Only if the smoke test fails: diagnose

Do **not** run this while things are passing — it is wasted effort.

When a check fails, work out whether the change is wrong or the environment is:

- **Did the deploy actually land?** Compare the deployed commit to what you pushed. For a service, check the running task definition revision; for an SPA, confirm the bundle changed rather than a cached one being served.
- **Are the services healthy?** Check that tasks are running and stable rather than crash-looping, and read recent error logs for the affected service.
- **Did migrations run?** A schema change that did not apply presents exactly like a broken feature — the UI errors on a column that does not exist. Check migration status before blaming the code.
- **Is it environment config?** Missing or stale env vars produce behaviour that looks like a bug but is a deploy problem.
- **Is the environment's data unrepresentative?** Check the actual roles, permissions and memberships of the account you tested with. A permission check that passes because every seeded user is an admin has told you nothing, and a rule keyed on a permission the environment does not grant will behave differently here than in production.

Say plainly which it is: *"the feature is broken"* versus *"the deploy did not land"* versus *"the migration has not run"*. They lead to completely different next steps, and conflating them wastes the most time.

## Report

```
PROJ-123 → QA

api         pushed → run 123 ✔   (2m14s)
web         pushed → run 456 ✔   (1m02s)
worker      pushed → run 789 ✔   (58s)
mobile-app  SKIPPED — no QA pipeline

Smoke test (5 acceptance criteria):
  ✔ date field shows when the option is enabled
  ✔ submission blocked without a date
  ✘ past date accepted — expected rejection    ← real bug
  ✔ field hidden when flag off
  — bulk entry: not reachable, needs a product decision on Q1
```

State the overall verdict in one line: safe to hand to QA, or not. Then list what is broken and what you could not verify.
