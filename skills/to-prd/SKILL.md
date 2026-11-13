---
name: to-prd
description: Turn the current conversation context into a PRD markdown file at ./docs/features/<feature-name>/prd.md. If the PRD already exists, amends it in place instead of rewriting it. Use when user wants to create a PRD from the current context, or to land a reopened decision in an existing one. Requires a feature name as input.
---

<!--
Derived from Matt Pocock's `to-prd` skill, adapted for the-pause
local-markdown workflow (output under ./docs/features/<name>/). Original authored
by Matt Pocock. See ATTRIBUTION.md.
-->

This skill takes the current conversation context and codebase understanding and produces a PRD. Do NOT interview the user — just synthesize what you already know.

## Required input

The user must provide a **feature name** (kebab-case, short, descriptive — e.g. `csv-export`, `rate-limit`, `lapser-anti-spam`). If the user invokes this skill without a feature name, ask for one before proceeding.

## Output location

The PRD is written as a markdown file at:

```
./docs/features/<feature-name>/prd.md
```

(relative to the project root, i.e. the current working directory). Create the `./docs/features/<feature-name>/` directory if it does not exist. This file is committed to git alongside the code that implements the feature — it is not a personal scratchpad. Do not publish to an issue tracker — output is markdown-only.

## If the PRD already exists — amend it, do not rewrite it

A `prd.md` already at that path means the change is in progress and a decision was reopened: a
Re-grill finding from review, merge request feedback that changes what is built, or a change of
mind. This session holds the amendment, not the original grilling, so regenerating the PRD from the
conversation would silently drop everything that was not re-discussed.

- Read the existing PRD in full first. If it carries `> Status: implemented`, stop: on its own change
  branch the close commit must be reverted first, and anywhere else the feature has shipped and the
  new work needs a new feature name.
- Change only the sections the reopened decision touches. Leave every other line as it is.
- User stories keep their numbers, because issue stubs cite them. Add new stories at the end of the
  list. A story that no longer holds is struck through with a one-line reason, not deleted.
- Add one line under **Further Notes**: the date, what changed, and what reopened it.
- Show the user the intended edits as a diff and wait for an explicit OK before writing.

The process below applies to a new PRD. For an amendment, step 2's module sketch is redone only if
the amendment changes which modules are built.

## Process

1. Explore the repo to understand the current state of the codebase, if you haven't already. Use the project's domain glossary vocabulary throughout the PRD, and respect any ADRs in the area you're touching.

2. Sketch out the major modules you will need to build or modify to complete the implementation. Actively look for opportunities to extract deep modules that can be tested in isolation.

A deep module (as opposed to a shallow module) is one which encapsulates a lot of functionality in a simple, testable interface which rarely changes.

Check with the user that these modules match their expectations. Check with the user which modules they want tests written for.

3. Write the PRD using the template below to `./docs/features/<feature-name>/prd.md`. Confirm the path to the user once written.

<prd-template>

## Problem Statement

The problem that the user is facing, from the user's perspective.

## Solution

The solution to the problem, from the user's perspective.

## User Stories

A LONG, numbered list of user stories. Each user story should be in the format of:

1. As an <actor>, I want a <feature>, so that <benefit>

<user-story-example>
1. As a mobile bank customer, I want to see balance on my accounts, so that I can make better informed decisions about my spending
</user-story-example>

This list of user stories should be extremely extensive and cover all aspects of the feature.

## Implementation Decisions

A list of implementation decisions that were made. This can include:

- The modules that will be built/modified
- The interfaces of those modules that will be modified
- Technical clarifications from the developer
- Architectural decisions
- Schema changes
- API contracts
- Specific interactions

Do NOT include specific file paths or code snippets. They may end up being outdated very quickly.

## Testing Decisions

A list of testing decisions that were made. Include:

- A description of what makes a good test (only test external behavior, not implementation details)
- Which modules will be tested
- Prior art for the tests (i.e. similar types of tests in the codebase)

## Out of Scope

A description of the things that are out of scope for this PRD.

## Further Notes

Any further notes about the feature.

</prd-template>
