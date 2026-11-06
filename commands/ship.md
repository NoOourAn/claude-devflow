---
description: Take a ticket from plan to PR, across every repo it touches
argument-hint: [ticket-id-or-description] [--plan-only] [--draft]
allowed-tools: Bash, Read, Write, Edit, Grep, Glob, TodoWrite, Skill, AskUserQuestion, WebFetch
---

# Ship

Drive one piece of work from plan to pull request. Handles the multi-repo case, where the usual failure is one repo's PR merging while another repo's half is still unbuilt.

Work item: **$ARGUMENTS**

## Step 0 — Preflight and resume

Load the `work-artifacts` skill and run its preflight.

**Check `.devflow/<ticket>/` before anything else.** If a spec or plan is already there from a previous session, read it and say what you found — then continue from where it stopped rather than re-deriving it. Reconcile against the current code first; if the repo has moved on, say so.

Report blockers as one batch.

## Step 1 — Get the requirements

If the argument looks like a ticket ID and an issue tracker is connected (Linear, Jira, GitHub Issues), fetch the ticket **and its comments** — prior technical discussion usually lives in comments, not the description. If a tracker supports it, move the ticket to *In Progress* now rather than at the end.

If there is no tracker, treat the argument as the spec.

Restate the acceptance criteria in your own words before writing code. If a criterion is ambiguous in a way that would change what you build, ask now. Otherwise state your assumption and continue.

## Step 2 — Decide the repo set

Determine which repos the work actually touches. Check for sibling repos in the same workspace when the change looks like it crosses a boundary — an API change that a client consumes, a shared library and its dependents.

State the repo set and the **merge order** before writing code. The ordering rule is dependency direction: whatever provides an interface merges before whatever consumes it. An API or schema change lands first; clients follow.

If it turns out to be one repo, say so and move on. Do not manufacture cross-repo work that is not there.

## Step 3 — Plan

Write a short plan per repo: files to touch, the approach, and the risk you are most worried about.

Propose the **simplest correct** implementation. Pick one approach and justify it in a sentence — do not present a menu of options you will not pursue.

Record the plan where the team will see it: a ticket comment if a tracker is connected, otherwise in your response. Do not overwrite a ticket description; that holds the spec.

Also write it to `.devflow/<ticket>/plan.md`, and start `.devflow/<ticket>/progress.md`. Keep progress updated **as each repo lands**, not at the end — including decisions, with who made them.

Stop here if `--plan-only`.

## Step 4 — Branch

One branch per repo, **the same name in each** so they read as a set.

Branch from the repo's default branch, freshly fetched — not from whatever is currently checked out, which is often a stale deploy or release branch:

```bash
git -C <repo> fetch origin
git -C <repo> checkout -b <type>/<slug> origin/$(git -C <repo> symbolic-ref --short refs/remotes/origin/HEAD | sed 's|origin/||')
```

If the work belongs to an existing multi-repo effort with a shared branch, reuse that branch name rather than inventing a new one.

## Step 5 — Implement

Work repo by repo in merge order. Match the surrounding code — its naming, structure, comment density, and idioms. Keep comments minimal; write them only where the reasoning is genuinely non-obvious.

Use the patterns the codebase already has rather than introducing new ones. If a project skill or convention doc covers the area, follow it.

## Step 6 — Verify

Run `/devflow:verify` in **every** repo you touched. All must be green before any PR opens.

Report failures honestly, including ones you could not fix.

## Step 7 — Pull requests

One PR per repo. Each body carries:

- What changed and why, in plain language.
- A link to the ticket, if there is one.
- The cross-repo dependency stated at the top when one exists: *"Merge after `org/other-repo#123`."*
- What you verified, and anything you could not verify.

**Open every PR as ready for review.** Reaching this step means the work is implemented and verified, so it is ready for someone else to look at. A merge-order dependency is **not** a reason to draft a PR — that is what the "Merge after `…#123`" line at the top of the body is for, and a dependent PR still needs review while its dependency is in flight.

Open as draft **only** when `--draft` is passed.

Finish by listing every PR URL in merge order — in a ticket comment if there is a tracker, otherwise in your response — so a reviewer gets the whole set in one place.

## Guardrails

- Commit and push only as part of this flow. Never push work the user did not ask for.
- Never force-push.
- If part of the work is blocked, finish everything that is not, then say explicitly what you left out and why. Scaling the work down is the user's call.
