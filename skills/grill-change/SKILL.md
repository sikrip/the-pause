---
name: grill-change
description: Entry point of both lanes. Grill a plan until shared understanding is reached — a feature idea already in the conversation, or a ticket (grill-change <KEY>) that the skill fetches from Jira or GitLab first and treats as the plan. Runs Matt Pocock's grilling and domain-modeling skills; writes nothing except the CONTEXT.md / ADR updates those make. Use when the user wants to stress-test an idea or a ticket before to-prd + to-md-issues or to-rework.
---

# /grill-change [KEY]

The understand step of the four-session flow, shared by both lanes. It settles one thing before the questions start: **where the plan comes from.**

| Invocation | Lane | Plan |
|---|---|---|
| `grill-change` | feature | the idea, doc or pasted page already in the conversation |
| `grill-change <KEY>` | rework (usually) | the ticket, fetched now and quoted into the conversation |

Freeze afterwards in the same session with `to-prd` + `to-md-issues` (feature) or `to-rework <KEY>` (rework). Both read the grilling from the conversation, and `to-rework` halts unless the ticket text is present — which is why this skill quotes it.

## Step 1 — get the plan into the conversation

**No argument.** Use what the user has described or pasted. If there is nothing to grill yet, ask for the idea in one line; do not start asking questions about an empty plan.

**A ticket key.** Fetch it before anything else and quote it back — key, title, status, description, acceptance criteria if any, linked issues — in a short block the user can correct. Then work from the quoted text, not from the tracker link.

- Jira key (`PROJ-123`, `LAP-42`): Atlassian MCP `getJiraIssue`. Load it with `ToolSearch("select:mcp__claude_ai_Atlassian__getJiraIssue")`; pass the site host as `cloudId` (the host your tickets live on, e.g. `your-org.atlassian.net`). If the host is rejected, call `getAccessibleAtlassianResources` and use the returned UUID.
- GitLab issue (`#118`, `group/project#118`, or an issue URL): `glab issue view <iid> -R <project>`.
- Fetch fails (no MCP, no auth, unknown key): say so and ask the user to paste the ticket text. Do not grill from the key alone, and do not guess the content.

## Step 2 — grill

Run the `grilling` skill, using the `domain-modeling` skill for `CONTEXT.md` and ADRs. This is the one line `grill-with-docs` consists of; that skill is human-only (`disable-model-invocation: true`), which is why the line lives here instead of a call to it.

Two additions when the plan is a ticket:

- **First decision: what "unchanged" means.** Before any design question, agree the observable behaviour the rework must preserve — the surface step 0's characterisation tests will pin. Name concrete inputs and outputs, not "the same as now".
- **Watch for lane drift.** If an answer changes behaviour — a new column, a changed default, a contract change — say so at once: the change is now a feature, and the freeze step is `to-prd`, not `to-rework`. A rework must not absorb a behaviour change silently.

Cross-reference the ticket against the code as you go. A ticket written weeks ago often describes a state that has moved; where the code disagrees with the ticket, the code is the fact and the ticket is the intent.

## Output

Nothing on disk except what `domain-modeling` writes (`CONTEXT.md`, `docs/adr/`). The result is the locked decisions in the conversation plus the quoted ticket. Close by naming the freeze skill to run next and any open decision that would block it.
