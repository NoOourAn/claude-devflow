---
description: Research a rough idea or empty ticket and write it up as a proper spec
argument-hint: [ticket-id or description] [--post] [--create]
allowed-tools: Bash, Read, Grep, Glob, WebFetch, WebSearch, TodoWrite, Skill, Agent, mcp__*
---

# Spec

Turn a rough request into a ticket an engineer can start from without a meeting.

Input: **$ARGUMENTS**

## Preflight

Load the `work-artifacts` skill and run its preflight. Check for an existing `.devflow/<ticket>/` first — if there is a spec from a previous session, read it and continue from there instead of starting over.

Report anything blocking as one batch, not one question at a time.

## Run the process

Load the `product-spec` skill and follow it. The order is not optional — **investigate before writing**. A spec written without reading the code is a guess.

Resolve the input first:

- A ticket ID → fetch the ticket **and its comments** from the connected tracker. Comments usually hold prior discussion the description does not.
- Free text → treat it as the raw request.
- `--create` → no ticket exists yet; create one once the spec is agreed.

Then work through the skill: understand the request → read the code → check external constraints and docs → decide scope → write testable acceptance criteria → surface open questions with recommendations → note risk and dependencies.

Use whatever is connected and relevant: documentation lookup for library and API contracts, web search for standards or regulations, data sources for how often the situation actually occurs, design tools for existing mockups. If a third-party system is involved, its schema constrains the design — find out what it requires before proposing a shape.

Search the real repositories rather than reasoning from the ticket title. Cite concrete paths (`file.ts:42`).

## Output

Present the draft spec in the conversation first, plus:

- **What I verified in code** versus **what I inferred** — so the reader knows which parts to trust.
- Anything already built that changes the shape of the work.
- The open questions, each with your recommendation and who needs to decide.

## Writing to the tracker

**Do not write to the tracker until the draft is agreed**, unless `--post` was passed.

When posting:

- The **spec** goes in the description.
- Any step-by-step implementation plan goes in a **comment**, not the description.
- Set labels, priority, and estimate only where you have a defensible basis.
- Do not overwrite an existing non-empty description without showing what would be lost and getting agreement.

Once agreed, also save the spec to `.devflow/<ticket>/spec.md` so `/devflow:ship` can pick it up in a later session without re-deriving it.

If the tracker is unavailable, still write the artifact, hand back the exact text to paste in, and say plainly that the tracker was not updated.

Report the ticket URL when done.
