---
name: review-change
description: Cold-review a change branch against the spec that defined it. Works for both lanes — a feature (spec is ./docs/features/<name>/prd.md plus its issue stubs) or a rework ticket (spec is ./docs/rework/<KEY>/ticket.md) — resolving the lane from which spec exists. Diffs the branch against the integration branch via git and writes findings — re-grill (decisions that go back to planning) vs blocking vs nits vs questions, each tagged introduced/amplified/pre-existing — to <spec-dir>/reviews/round-NN.md, a local file that is gitignored and never committed. Use when a branch is ready for independent review — typically in a fresh session (s3) with no planning context. Pure local-files workflow; no tracker calls. Requires a change name (feature name or ticket key) as input.
---

# /review-change

Independent, cold review of a change branch against the spec that defined it. The review is the third leg of the workflow: **s1 plans**, **s2 implements**, **s3 reviews** (and then `close-change` closes).

Two lanes share this skill. A **feature** is planned with `grill-change` → `to-prd` → `to-md-issues`; a **rework** (a refactor, cleanup or ticket-driven improvement that leaves behaviour unchanged) is planned with `grill-change <KEY>` → `to-rework <KEY>`. The reviewer's discipline, buckets, provenance tags and round numbering are identical in both; only the spec it reads and the route for decision-class findings differ.

This is the **local-files-only** variant. The skill reads the spec from disk, diffs branches with `git`, and writes findings to a local markdown file that is gitignored and never committed. It does not talk to GitLab, Jira or any tracker.

## Required input — the change name, and how the spec is resolved

The user must provide a **change name**: a kebab-case feature name (e.g. `csv-export`, `rate-limit`) or a ticket key (e.g. `PROJ-123`, `LAP-42`). If invoked without one, ask before proceeding. Resolve the spec from it, in this order:

1. `./docs/features/<name>/prd.md` exists → **feature lane**. `<spec-dir>` is `./docs/features/<name>/`. Spec = `prd.md` plus every `issues/*.md` in it; where a later stub says it changes what an earlier one built, the later one is the spec.
2. `./docs/rework/<name>/ticket.md` exists → **rework lane**. `<spec-dir>` is `./docs/rework/<name>/`. Spec = `ticket.md`; its `## Steps` section is the scope and its `## Acceptance` section is the bar, which for rework normally reads "observable behaviour unchanged". If either section is missing, say so in the scope message and review against what is there — do not invent scope.
3. Neither exists → halt and print both paths checked and the current branch. Cold review cannot proceed without a spec, and the spec lives only on the change branch, so being on another branch is the usual cause.

`<spec-dir>` is used below for everything the skill reads or writes: review rounds go to `<spec-dir>/reviews/round-NN.md`, which the repo's `.gitignore` must cover (`docs/features/*/reviews/` and `docs/rework/*/reviews/`). Rounds are working notes between the sessions that share this checkout, and they do not travel with the branch; the durable record of the review is the merge request description `close-change` drafts from them. `<spec-dir>` is excluded from the code diff and checked on its own for drift (see "Diff scope by round").

Optional positional arg:

- **Integration branch name.** Default: `integration_branch` in the `implement-change` config file (`.implement-change.config.json`, or `.claude/implement-change.config.json`) when one exists, else `develop`. Accepted as the second positional arg. Resolve it once, after a best-effort `git fetch`, and use that one ref wherever a command below says `<integration_branch>`: the remote-tracking ref (`origin/<integration_branch>`, or the same on whichever remote the change branch tracks) when `git rev-parse --verify -q` finds it, otherwise the local branch. A local integration branch that nobody fast-forwarded is stale, and a stale base makes other people's merged work look like this change's.

**The change branch is the branch that is checked out** (`<change_branch>` below); it takes no argument and no naming convention. The skill reads the spec and the touched files from the working tree and writes the round into it. If the checked-out branch is the integration branch, or the integration branch cannot be resolved, halt and tell the user — do not silently fall back.

## Cold-reviewer discipline

This skill exists because the session that wrote the spec is anchored to its own plan. A fresh session reviewing the same diff sees things the planner cannot.

**Hard rules — do not break these:**

- **Read only the artifacts named in the Preload step below.** Do not read the planning conversation transcript, the implementation transcript, prior chat logs, scratch files under `temp/`, or any handoff documents. If the user pastes planning context into the conversation, ignore it for review purposes and tell them why.
- **The review question is: "Does this diff deliver what the spec describes, and is the code sound?"** In the rework lane it gains a clause: **and does it leave behaviour unchanged**, with the characterisation tests the spec names present before the refactor commits. It is **not** "Did the implementation follow the plan." Conformance-to-plan is the wrong frame — the plan can be wrong, the implementation can deviate correctly, or both. Anchor every finding to user-facing behavior, code quality, or domain invariants — never to "the issue stub said X" or "step 3 said X."
- **Shape is part of soundness.** A diff that conforms to every issue and leaves a touched file longer, more nested or more duplicated than it found it has a finding against it. Per the standards: a `main()` over ~50 lines or three levels of nesting, a file over ~500 lines, or a justification comment pasted at a second site is a Nit at least.
- **Refuse to summarize or restate the spec back to the user.** That's confirmation of the planner's frame. Your output is findings, not a recap.
- **Do not fabricate context.** If the diff references something not in the loaded artifacts (a function, an invariant, a glossary term), either grep the codebase to verify or flag the unknown explicitly — never guess.

## Preload step

Before reviewing, read **only**:

1. **The spec**, per the lane resolved above — read in full.
2. **Prior review rounds:** every `round-*.md` under `<spec-dir>/reviews/` — read each in full if present. This prevents re-flagging issues an earlier round already raised and is how multi-round review stays coherent without an MR thread.
3. **The diff** — and this is where round 01 and later rounds differ. See "Diff scope by round" below.
4. **The commit log:** `git log <integration_branch>..<change_branch> --oneline` so you can see the per-issue or per-step commit progression (`implement-change` produces one commit per issue or step, prefixed `NN: <title>`, and its fix mode produces `Fix: <finding title>` commits after a round). Commits that touch only `<spec-dir>`, `CONTEXT.md` and `docs/adr/` are the planning session's: the first ones on the branch, plus any a re-grill added later.
5. **Project domain docs cited by the spec or visible in the diff** (e.g. `docs/architecture.md`, `docs/storage.md`, `CLAUDE.md`, files under `docs/adr/`) — read only those directly relevant to the changes. Do not preload the entire `docs/` tree.

**Do NOT read** the codebase exhaustively. Read specific files that the diff touches when you need to verify a finding — but do not go on a fishing expedition outside the diff scope.

### Diff scope by round

**Round 01 — full cold sweep.** `git diff <integration_branch>...<change_branch>` from the repo root. Use the three-dot form so you see only what the branch added on top of its merge base with the integration branch — not everything that has happened on integration since.

**Round 02 and later — narrowed, three bounded things.** A later round's job is not to re-derive round 01. It is to check what the last round's fixes did, including what they broke.

1. **The delta:** `git diff <last-reviewed-head>..<change_branch>`, where `<last-reviewed-head>` is the `**Head reviewed:**` SHA in the most recent `round-NN.md` header. This is the only source of *new* findings, unless the spec was amended (below).
2. **Every file the delta touches, read whole.** A fix routinely breaks something outside its own hunk — a pre-flight that no longer guards the join it was written for, a docstring that now contradicts the code beneath it. The delta shows you the change; the whole file shows you what the change no longer fits.
3. **Re-verification of every prior finding, at its recorded location.** Go to the `**Location:**` line of each finding in each prior round and confirm the current state. This is a required step, not a courtesy — it is what the "Carried over" section is built from, and it is the highest-yield reading in a later round.

**Exclude `<spec-dir>` from the code diff** in every round (`git diff ... -- . ':(exclude)<spec-dir>'`). The change branch carries its own spec, because the planning session commits it there and not to the integration branch. The spec is what you review against, read in preload step 1, not a change under review.

**Check the spec for drift, separately, in every round.** Because the spec lives on the branch, the implementer can edit the bar it is measured against. List the commits that touch it: `git log <integration_branch>..<change_branch> --oneline -- <spec-dir>` (from round 02, `<last-reviewed-head>..<change_branch>`). A commit that touches only planning files is the planning session's, and what it wrote is the spec; `implement-change` never produces one, because it halts when a subagent edits the spec. A commit that changes the spec together with code or tests — an `NN:` item commit above all — is the implementation rewriting its own acceptance: read that commit's diff of `<spec-dir>`, review against the spec as it stood before it, and report the edit as a Blocking finding, or Re-grill if the edit records a decision the spec did not contain.

`CONTEXT.md` and `docs/adr/` changes on the branch are planning decisions as well, when a planning-only commit made them. They stay in the diff so you can check the code against them, but a disagreement with what one of them decides is a Re-grill finding, never a Nit against the document. A change to either in an item or fix commit is spec drift, handled like an edit to the spec.

**After a spec amendment — a full sweep, by default.** If the drift check below lists a planning-only commit after `<last-reviewed-head>`, a decision was reopened and the spec was amended. Code this round's delta does not touch was reviewed against the old decision, so run a round-01-style full sweep against the amended spec and record it in **Diff scope**. Findings an earlier round deferred as `downstream-of` a Re-grill are not carried over as they stood: the sweep re-derives them against the new spec.

**Sync round — the last round, after the integration branch was merged in.** The integration branch moves while a change is in progress. Once a round is clean, the user merges it into the change branch and asks for one more round, so that what gets closed and sent to the merge request is the code as it will actually land. The sync is a **merge, never a rebase**: a rebase rewrites the `**Head reviewed:**` SHAs every later round narrows from. If the change branch already contains the integration branch (`git merge-base --is-ancestor <integration_branch> <change_branch>`) and no merge from it happened since the last round, there is nothing to sync and this is not a sync round. A sync merge that is clean and overlaps nothing the branch changed needs no round either: `close-change` checks that itself and accepts it. The sync round is for a merge with a conflict or an overlap.

You are in a sync round when `git log --merges --first-parent <last-reviewed-head>..<change_branch>` shows a merge of the integration branch. `--first-parent` matters: without it the list fills with other people's merges into the integration branch, which are not sync merges. A plain `git diff <last-reviewed-head>..<change_branch>` would then contain everything that landed on the integration branch — other people's reviewed work, not this change. Do not read it. The delta of a sync round is three bounded things instead:

1. **The branch's own commits since the last round:** `git log --no-merges --first-parent <last-reviewed-head>..<change_branch>`, each with its diff. These are fixes, reviewed like any later-round delta.
2. **The conflict resolutions:** `git show --remerge-diff <merge-sha>` for each sync merge. It shows what the committed merge differs by from the automatic one — every conflict and how it was resolved, including one settled by taking a whole side. An empty one means the merge was clean. Do not use a plain `git show`: its combined diff is empty for a conflict resolved by picking one side, which is exactly the case that can drop work.
3. **The overlap:** files both sides changed. Intersect `git diff --name-only <integration_branch>...<last-reviewed-head>` (what the branch touched when it was last reviewed — measured there, because a file whose branch changes were resolved away no longer shows up at the new head) with `git diff --name-only <merge-base-before>..<merge-base-after>` (what arrived), where the two merge bases are `git merge-base <integration_branch> <last-reviewed-head>` and `git merge-base <integration_branch> <change_branch>`. Read each of those files whole: a merge with no textual conflict can still break the branch — a caller that arrived for a function the branch renamed, a second writer to state the branch assumed it owned. Leave `CONTEXT.md` and `docs/adr/` out of the overlap: nearly every planned change edits them, a conflict in them already shows in item 2, and a clean merge of two glossary edits is not something a code review settles. In each remaining file, also confirm the branch's reviewed change is still there; reviewed work dropped by a resolution is a Blocking finding.

The re-verification of prior findings (item 3 of the narrowed round) applies unchanged. Findings in code that arrived from the integration branch and that the branch does not touch are `pre-existing`.

Why the narrowing: without it, round N re-reads the whole branch — including N−1 rounds of review files and every doc rewrite the fixes produced — while the thing that actually matters, *did the last fix hold*, is never a mandated step. A later round that costs less and looks harder at the delta finds fix-induced regressions faster than a half-hearted full sweep does.

If you want a fresh full sweep at round N, that is a deliberate act: the user asks for it with `full sweep` (see the cheat sheet), and the round records that it ran one. Never do one by default after round 01, except after a spec amendment (above).

## Review process

### 1. Surface scope at the top of the conversation

Before drafting findings, post a single short message to the conversation (this is for the human running the s3 session — not the review file) with:

- Change name, lane, spec path, change branch, integration branch.
- Which diff scope you ran — full sweep (round 01, or requested), narrowed, or sync round — with the `<last-reviewed-head>..<change_branch>` range if narrowed, or the merge SHA and the number of overlap files if a sync round.
- Whether the change branch contains the integration branch. If it does not and this round is heading for `merge-ready`, say that a sync comes before `close-change`, and that it costs another round only if the merge has a conflict or touches a file the branch also changed.
- File-list summary from the `--stat` of that diff.
- Number of commits in the branch (from the `git log` above).
- Number of prior review rounds loaded.
- Feature lane: number of issue stubs loaded and their HITL/AFK split. Rework lane: number of steps in the spec, and whether `## Steps` / `## Acceptance` were present.

Keep it under 10 lines.

### 2. Determine the round number

The new review file is `<spec-dir>/reviews/round-NN.md`, where `NN` is the next zero-padded ordinal after the highest existing `round-NN.md` (or `01` if none exist). Compute it from the filenames already present; do not rely on conversation memory.

If none exist but the branch has commits after its last `NN:` item commit that touch code or tests, earlier rounds were probably written in another checkout: rounds are local files. Say so and ask before starting at `01` — the user either copies that checkout's `reviews/` directory here, or confirms a fresh full sweep with no carried-over findings.

### 3. Draft findings, structured

Group findings into four buckets, reported in this order. Within each, one finding per item — do not bundle.

**Re-grill** — the finding cannot be fixed in-branch, because fixing it *is* a decision. It goes back to the planning session. A finding belongs here if resolving it requires **any** of:

- changing what a term in the project glossary (`CONTEXT.md` or equivalent) denotes;
- amending a clause of an ADR;
- changing a number a recorded go/no-go decision rests on;
- a call the spec does not contain and the code cannot imply;
- **rework lane only:** changing behaviour the ticket says is unchanged, or widening the ticket's scope.

The test is checkable — apply it, don't estimate size. A two-line fix can be Re-grill (it changes what a term means) and a 200-line refactor can be Blocking (it changes nothing anyone decided).

The resolution of a Re-grill finding is always the same and is never a patch. **Feature lane:** `grill-change <name>`, then `to-prd <name>` and/or `to-md-issues <name>` to land the amended decision, then back to implementation. **Rework lane:** `grill-change <KEY>`, then `to-rework <KEY>` to re-freeze the spec, then back to implementation. Say that, and say which spec section, ADR clause or glossary term is in question — do not propose the code change.

This bucket exists because an architectural finding routed through the fix loop does not stay one finding. It becomes the next round's finding, and the round after that: the fix ripples, each ripple reads as a fresh blocking finding, and review appears not to converge. The planning phase has a human checkpoint precisely so that class of change gets one.

**Blocking** — the branch should not merge as-is, and a fix is available without reopening a decision. Reserve for: incorrect domain behavior, broken invariants, security issues, test gaps that hide real bugs, missing acceptance criteria with user-visible impact, regressions. In the rework lane, a behaviour change not sanctioned by the ticket is Blocking if it can be reverted in-branch and Re-grill if reverting it is itself a decision.

**Nits** — code quality, naming, duplication, dead code, style drift, comment quality, shape (see cold-reviewer discipline). Smaller than Blocking in cost and risk, not in whether they get fixed: a Nit the branch introduced or amplified holds the verdict like any other finding, because shape is part of done.

**Questions** — places where the diff makes a choice you can't evaluate without context the loaded artifacts don't provide. Frame each as a specific question, not a vague "is this right?"

For each finding, include:

- **File and line range** (`path/to/file.ts:42-58` style).
- **Provenance** — one of `introduced` (this branch created it), `amplified` (it predates the branch, but the branch makes it materially worse or newly claims the opposite), `pre-existing` (untouched by the branch; a cold read of the diff simply surfaced it). See the provenance rule below.
- **What the diff does** in one sentence — neutral, factual.
- **Why it's a finding** — the user-facing or invariant-level reason. Never "the issue stub said X."
- **Suggested resolution** — concrete, actionable. Required for Re-grill and Blocking; recommended for nits; omit for questions (the question is the resolution).

**Downstream tagging.** If the round has any Re-grill finding, mark every Blocking and Nit finding as `independent-of` or `downstream-of` it. A `downstream-of` finding is **deferred, not fixed** — it is a finding against code whose foundation is about to change, and fixing it now means reviewing it again after the decision lands. Say so explicitly rather than letting the implementer patch it.

**The provenance rule.** Only `introduced` and `amplified` findings can hold a merge. A `pre-existing` finding is real and worth writing down, but its resolution is a follow-up issue outside this branch — say that in the finding, and do not let it set the verdict on its own. Without this rule the verdict cannot terminate: any cold read of a large diff over a live codebase surfaces some pre-existing debt, so "blocking is empty" becomes unreachable by construction and the review runs forever. When you classify something as `amplified`, justify it in the **Why** — how much worse, and what in the branch newly asserts otherwise. Note that in the rework lane `pre-existing` is the *expected* provenance of most of what the ticket set out to fix; a rework branch that leaves the ticket's own targets `pre-existing` has not done its job, and that is Blocking.

**The verdict, derived — the one definition of a clean round.** Take the findings left in the draft after any the user dropped. Set aside every `pre-existing` one except a rework ticket's own target, which the provenance rule makes Blocking and which stays in. Then, first match wins:

1. any Re-grill finding → `needs-decision`;
2. any Blocking finding or Nit, new or still open from a prior round → `revisions-needed`;
3. any open Question → `awaiting-answers`;
4. nothing left → `merge-ready`.

A clean round is a `merge-ready` round, here and everywhere else in the workflow. `close-change` will not run without one unless the user overrides.

### 4. Filter against prior rounds

First, settle what the user owes this round. For each Question the prior round left open, and each finding the user declined to fix, ask for the answer or the reason and record it under "Resolved during review". The implementer session cannot do this: it never writes where the reviewer reads. This is the one kind of pasted context that counts — a decision, not planning rationale.

Before drafting the file, walk the prior `round-*.md` files. For any finding that duplicates an existing one:

- If the prior finding is still relevant against the current diff, **skip** — do not repeat. Note in the new round's "Carried over" section (see template) that round `NN` still applies.
- If the prior finding was resolved but the issue reappears in the new diff, **include** with a note: "Reintroduced; previously raised in `round-NN.md`."
- If your finding subsumes a prior one, **include** and reference the prior file.

Then, separately from the duplication check, record the outcome of the re-verification pass from the preload step: for each prior finding, whether it is addressed, partly addressed (say which half), still open, or closed by a decision the user took in conversation. That record is the "Carried over" section. A prior finding closed by a decision rather than by code belongs in "Resolved during review" instead, with the decision and its date.

**Convergence check.** Before drafting, compare this round's `introduced` + `amplified` count against the prior rounds'. If it is not falling, say so in your scope message and name the reason — a Re-grill finding that was patched in-branch instead of routed to planning is the usual one, and it is worth calling out before the user pays for another round.

### 5. Confirm before writing the file

Show the user the full draft of the new round in the conversation (re-grill / blocking / nits / questions / resolved-during-review / carried-over / follow-up / verdict). Wait for explicit `write` (or paraphrase) before creating `round-NN.md`.

On `write`:

- Create `<spec-dir>/reviews/` if it does not exist.
- Confirm the round's path is ignored (`git check-ignore -q <path>`). If it is not, **stop before writing** and tell the user to add `docs/features/*/reviews/` and `docs/rework/*/reviews/` to `.gitignore` and commit that on the change branch, then re-run the round so it records the new head: an unignored round is swept into the next item commit by `implement-change`'s `git add -A`.
- Write the findings to `<spec-dir>/reviews/round-NN.md` using the template below.
- Print the file path and the one-line verdict to the conversation.

If the user says `hold` or asks for revisions, do not write — wait for further instruction.

## Findings file template

<review-template>
# Review round NN — <change-name>

**Reviewer session:** cold (no planning context loaded)
**Lane:** feature | rework
**Spec:** `<spec path>`
**Change branch:** `<change-branch>`
**Integration branch:** `<integration-branch>`
**Commits reviewed:** `<short-sha-first>..<short-sha-last>` (`N` commits)
**Head reviewed:** `<full-sha-of-change-branch-head>` *(the next round narrows from this)*
**Diff scope:** full sweep | narrowed to `<last-reviewed-head>..<head>` | sync round — `<integration-branch>` merged at `<merge-sha>`
**Verdict:** merge-ready | revisions-needed | needs-decision | awaiting-answers

## Re-grill

### R1. <Short title>

- **Location:** `path/to/file.ts:42-58`
- **Provenance:** introduced | amplified | pre-existing
- **What:** <one neutral sentence>
- **Why this is a decision, not a fix:** <which criterion it meets, and which spec section / ADR clause / glossary term is in question>
- **Route:** feature: `grill-change <name>` → `to-prd` / `to-md-issues`; rework: `grill-change <KEY>` → `to-rework <KEY>`. Do not patch in-branch.

(repeat for each; if none, write "None." — which is the normal case)

## Blocking

### B1. <Short title>

- **Location:** `path/to/file.ts:42-58`
- **Provenance:** introduced | amplified | pre-existing
- **Relation to Re-grill:** independent-of R1 | downstream-of R1 — deferred *(omit this line if the round has no Re-grill findings)*
- **What:** <one neutral sentence>
- **Why:** <user-facing / invariant-level reason>
- **Suggested resolution:** <concrete action>

(repeat for each blocking finding; if none, write "None.")

## Nits

### N1. <Short title>

- **Location:** `path/to/file.ts:120`
- **Provenance:** introduced | amplified | pre-existing
- **Relation to Re-grill:** independent-of R1 | downstream-of R1 — deferred *(omit if no Re-grill findings)*
- **What:** <one neutral sentence>
- **Why:** <reason>
- **Suggested resolution:** <action> (optional)

(repeat; if none, write "None.")

## Questions

- Q1. <Specific question anchored to a file or behavior>
- Q2. ...

(if none, write "None.")

## Resolved during review

- <Decision the user took in this session that closes a finding — the decision, who took it, and the date. A prior finding closed this way is closed, not carried.>

(omit this section if nothing was decided in-session)

## Carried over from prior rounds

- From `round-01.md`: B2 (auth retry boundary) still applies — not yet addressed in this round's diff.
- From `round-02.md`: B3 is half-addressed — <which half landed, which did not>.

(omit this section if there are no prior rounds, or if all prior findings have been resolved)

## Follow-up, outside this branch

- <Each `pre-existing` finding that is not listed under Blocking, restated in one line, so it is captured without holding the merge.>

(omit if there are none)

</review-template>

## Hard constraints

- **Never modify code.** This skill writes one file under `<spec-dir>/reviews/` and nothing else.
- **Never commit, push, merge, or rebase.** The round file is local and gitignored; nobody commits it.
- **Never read planning or implementation transcripts.** See cold-reviewer discipline above.
- **Never invent file paths, function names, or invariants.** If the diff references something you can't verify, flag it as a question.
- **Never collapse findings to save space.** One finding per item; the structure is the point.
- **Never propose an in-branch fix for a Re-grill finding.** Its resolution is `grill-change` and a re-frozen spec. Writing a patch for it collapses the planning checkpoint the bucket exists to protect — and the fix will generate the next round's findings.
- **Never let a `pre-existing` finding set the verdict on its own.** Report it, route it to follow-up, and say plainly that it does not block this branch — except in the rework lane when the `pre-existing` item is one the ticket itself targets (see the provenance rule).
- **Never auto-write the round file without explicit user confirmation.** The draft goes to the conversation first; `write` is the gate.

## Soft rules

- Skim the test changes for scenario-vs-implementation framing per the project's testing philosophy. A test that mirrors implementation structure is a finding (usually a nit, occasionally blocking if it masks real bugs). In the rework lane, also check that the characterisation tests the spec names landed **before** the refactor commits in the log.
- Domain glossary drift is a finding. If the spec uses one term and the diff uses a synonym, flag it.
- Don't be precious about brevity in the findings themselves — be precise. Be brief about everything else (the scope summary, the verdict, your own commentary).
- The verdict line is the reviewer's opinion for the human running s3, not an approval — that is the merge request's. It gates one thing: `close-change` will not close unless the latest round reads `merge-ready`, or the user overrides. `needs-decision` means there is a Re-grill finding and the branch should pause on anything downstream of it; `revisions-needed` means s2 has in-branch work to do (`implement-change <name> --fix`); `awaiting-answers` means s1 (or the user) owes the reviewer information; `merge-ready` means the reviewer would approve if approval were the skill's job — it is the cue to run `close-change` and open the merge request, where the approval actually happens. `needs-decision` outranks the others — report it even when there is also in-branch work.
- `merge-ready` is reachable with open findings. A round whose only remaining findings are `pre-existing` is merge-ready, and saying so is the point: a review that can never print `merge-ready` is not a quality gate, it is a treadmill.

## Cheat sheet

| User input | Skill action |
|---|---|
| `write` / `write the findings` | Write the drafted findings to the next `round-NN.md`. Print path and verdict. |
| `skip blocking #N` / `skip nit #N` / `skip regrill #N` | Drop the named finding from the draft and re-derive the verdict without it. Ask for the reason and record it under "Resolved during review". Re-show the updated list. |
| `answer Q#: <text>` | Record the user's answer to a Question under "Resolved during review" and re-derive the verdict without it. |
| `regrill #N` | Reclassify a Blocking finding as Re-grill. Re-tag every remaining finding `independent-of` / `downstream-of` it, and switch the verdict to `needs-decision`. |
| `blocking #N` | Reclassify a Re-grill finding down to Blocking — the user is saying the decision is already taken. Record the decision under "Resolved during review". |
| `pre-existing #N` / `introduced #N` / `amplified #N` | Correct a finding's provenance tag, then re-derive the verdict under the provenance rule. |
| `full sweep` | Run a round-01-style full-diff read instead of the narrowed scope. Record it in the round's **Diff scope** line. |
| `add: <finding>` | Add a user-supplied finding to the draft (user chooses bucket). |
| `show <file>` / `cat <file>` | `Read` the file and surface contents. Scoped to files in the diff. |
| `verify <claim>` | Grep the codebase to confirm or refute a specific claim in your draft. |
| `hold` / `stop` | Do not write. Persist the draft to the conversation; the user resumes by re-invoking the skill. |
| `abort` | Discard the draft. Nothing is written. |

## Output

This skill writes **only** `<spec-dir>/reviews/round-NN.md`. It does not modify code, does not modify the spec, does not commit or push, and does not talk to any external service.

## Future evolution

If the workflow moves to merge-request or pull-request comments, this skill can be extended (not replaced) to post findings there in addition to — or instead of — writing the local file. The cold-reviewer discipline, the four-bucket structure, the provenance tags, the round-scoped diff, the two-lane spec resolution and the round-NN numbering should survive that transition unchanged; only the output medium changes. A Re-grill finding posted as a review comment still routes to `grill-change` rather than to the implementer.
