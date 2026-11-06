---
name: work-artifacts
description: Persist spec and plan output to disk under .devflow/<ticket>/ so multi-repo, multi-session work survives a lost context window and can be resumed. Use when starting, resuming, or handing off work on a ticket, and whenever a spec or implementation plan is produced.
---

# Work Artifacts

Work that spans several repos and several sessions loses its context window long before it lands. When that happens the plan is gone, and it gets re-derived slightly differently the second time.

Fix: **write each phase to disk as you go.** Cheap to produce, and it makes the work resumable.

## Where

```
.devflow/<TICKET-ID>/
  spec.md      # the agreed spec (mirrors the tracker description)
  plan.md      # per-repo implementation plan, in merge order
  progress.md  # what is done, what is in flight, what is blocked
```

Use the ticket ID when there is one (`PROJ-123`), otherwise a short kebab slug.

`.devflow/` is working state, not a deliverable — add it to `.gitignore` unless the team has agreed to commit it. It is not a replacement for the tracker: the tracker stays the source of truth for anything another person needs to see. These files exist so **you** can resume.

## Check before you start

At the beginning of any spec or ship work, look for `.devflow/<ticket>/` first.

If it exists, read it and say what you found — "there's a plan from a previous session; the API is done, the web app is not". Then continue from there rather than starting over. If the code has moved on since it was written, say so and reconcile before trusting it.

Never silently overwrite an existing artifact. Update it, or say what changed and why.

## Keep progress.md honest

Update it as you finish each repo, not at the end. It is only useful if it is true.

```markdown
# PROJ-123 — progress

Updated: 2026-01-15

## Done
- api: entity + migration + DTOs — PR acme/api#412

## In flight
- web: date input — branch pushed, no PR yet

## Blocked
- worker: waiting on api#412 to merge (schema dependency)

## Decisions
- Date is required, not optional (Q1) — confirmed by product 2026-01-15
```

Record **decisions** as they are made, with who made them. Re-litigating a settled question is the most common way this work goes backwards.

## Preflight

Before starting a phase, check the things that make it fail halfway through, and report them together rather than one at a time:

- In a git repo? (`git rev-parse --show-toplevel`)
- Ticket ID well-formed, and does it resolve in the tracker?
- Is the tracker MCP actually connected?
- Are the repos you are about to touch clean, or do they have uncommitted work?

If the **tracker is unavailable**, do not stop. Do the work, write the artifacts to disk, and hand back the exact text to paste in, saying clearly that the tracker was not updated. Degrading to manual is fine; silently skipping the update is not.
