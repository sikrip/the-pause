# The Pause - a phased AI development methodology

> *The value is in the pause, not the speed.*

Skills, slash commands, standards and hooks for building software with an AI agent in three
separate sessions: plan, implement, review. A human decides at every boundary.

An agent is most dangerous when it is confident and unsupervised across a large change. So the work
is split into three roles, **Planner**, **Implementer** and **Reviewer**, each in its own session.
The skills do the mechanics inside a phase. You own the transitions.

Everything here is local files you copy or link into place. Nothing to install, nothing phones home.

---

## The workflow at a glance

A feature goes through three sessions (three terminal tabs, or three Claude Code windows). Each one
commits files the next one reads. That committed spec is the bridge between sessions, not chat
history.

```mermaid
flowchart TD
    subgraph S1["Session 1 · Planner / Architect"]
        direction TB
        A["/grill-change<br/><small>stress-test the idea;<br/>build CONTEXT.md + ADRs</small>"]
        B["/to-prd &lt;feature&gt;<br/><small>synthesize the PRD<br/>from the grilling</small>"]
        C["/to-md-issues &lt;feature&gt;<br/><small>slice the PRD into vertical<br/>tracer-bullet issues</small>"]
        A --> B --> C
    end

    D["<b>Session 2 · Implementer</b><br/>/implement-change &lt;feature&gt;<br/><small>cut feature/&lt;feature&gt; off develop;<br/>walk issues serially, drive tdd,<br/>commit on green; stop at HITL gates</small>"]

    E["<b>Session 3 · Reviewer</b> &nbsp;<small>fresh session, no planning context</small><br/>/review-change &lt;feature&gt;<br/><small>cold-diff feature/&lt;feature&gt; vs develop;<br/>read prd + issues as the spec;<br/>write blockers / nits / questions<br/>to reviews/round-NN.md</small>"]

    C -->|"commit CONTEXT.md, docs/adr/*,<br/>prd.md, issues/* to develop"| D
    D -->|"all work on feature/&lt;feature&gt;"| E
    E -->|"round-NN.md: blockers / nits / questions<br/>(another round needed)"| D
    E ==>|"clean round — no blockers,<br/>nits or questions"| M([Merge feature/&lt;feature&gt; into develop])
    M --> F["/close-change &lt;feature&gt;<br/><small>on develop: PRD/ADR status, prune issues + reviews,<br/>docs grep, fixtures + full suite, debt check</small>"]
```

Why separate sessions: the reviewer must not remember the planning rationale. It judges the diff
against the written spec, the way a new reviewer would. That is what keeps the review honest.

In practice the tabs are named **Architect**, **Developer** and **Reviewer**. A typical moment: the
Developer tab has read the PRD and six issue stubs, printed the dependency order (each issue's
`Blocked by` line links the slices), and stopped for a pre-flight check before cutting the branch.

---

## Session 1 - Planner

Goal: agree on *what* to build and commit it, before any implementation code.

### `grill-change [KEY]`

Start from an idea, a doc or a wiki page pasted into the session. Or pass a ticket key
(`grill-change PROJ-123`) and the skill fetches the ticket and quotes it back first.

It then runs Matt Pocock's `grilling` and `domain-modeling` skills. It interviews you one decision
at a time, down the design tree, with its recommended answer at each branch. Along the way it
updates:

- **`CONTEXT.md`** - the domain glossary. Domain language only, no implementation detail. It calls
  out terms you use that conflict with it.
- **`docs/adr/`** - an ADR, offered sparingly: only for decisions that are hard to reverse,
  surprising without context, and the result of a real trade-off.

You stop when you and the agent agree on what to build.

### `to-prd <feature-name>`

Writes the PRD from the grilling. It does not interview you again. Output:
`docs/features/<feature-name>/prd.md` (problem, solution, user stories, implementation and testing
decisions, out of scope).

### `to-md-issues <feature-name>`

Slices the PRD into vertical tracer-bullet issues: thin end-to-end paths, each demoable on its own.
Each issue gets a **Type** (`AFK`: the agent can build it, `HITL`: a human decides something first)
and a **Verification** (`AFK`, or `HITL`: a human confirms it works). Output:
`docs/features/<feature-name>/issues/<NN>_<slug>.md`, numbered in dependency order.

**End of session 1:** commit `CONTEXT.md`, `docs/adr/*`, `prd.md` and `issues/*` to `develop`.

---

## Session 2 - Implementer

### `implement-change <feature-name>`

Cuts `feature/<feature-name>` off `develop` and walks the issues one at a time:

- one subagent per issue, driving the `tdd` skill (red, green, refactor)
- when it returns: the issue's new tests, then the unit tier; both must be green
- commit on green, then the next issue

The slow tiers (integration, e2e) run once at the end of the run, not per issue.

It runs unattended except at `HITL` issues, where it stops and hands over to you. No worktrees, no
parallelism. The output is a clean sequence of commits on the feature branch.

The same skill implements a rework ticket (`implement-change PROJ-123`). The work items are then the
numbered steps in `docs/rework/PROJ-123/ticket.md`, step 0 is always the characterisation tests, and
the branch is `rework/PROJ-123`.

---

## Session 3 - Reviewer

### `review-change <feature-name>`

Run it in a fresh session with no planning context. It diffs the feature branch against `develop`,
reads `prd.md` and the issues as the spec, and writes findings to
`docs/features/<feature-name>/reviews/round-NN.md`:

- **re-grill** - a decision that goes back to planning
- **blockers**, **nits**, **questions** - for the implementer or for you

Each finding is tagged `introduced`, `amplified` or `pre-existing`, so you can tell what the branch
caused from what it only surfaced.

**The loop:** take `round-NN.md` back to session 2, fix, and review again (`round-02.md`, ...).
Repeat until a round is clean. Then merge and run `close-change <feature-name>` on `develop`. It sets
the PRD and ADR status, deletes the issue stubs and review rounds, greps the docs for anything the
change removed, and runs every test tier. The change is not done until it runs clean.

### `mutation-testing` (optional)

After a clean review, finds gaps in test quality: it mutates the code and reports the mutants your
tests don't catch. It asks for the tool, paths and exclusions before running.

---

## The rework lane - tickets, not features

A refactor, a dead-code removal or a cleanup ticket leaves behaviour unchanged. It has no user
stories, so a PRD would be ceremony. The rework lane keeps the same sessions and skills and swaps
only the spec:

| Stage | Feature lane | Rework lane |
|---|---|---|
| Understand | `grill-change` on the idea | `grill-change <KEY>`: fetches the ticket, quotes it, grills you |
| Freeze | `to-prd` + `to-md-issues` -> `docs/features/<name>/` | `to-rework <KEY>` -> `docs/rework/<KEY>/ticket.md`: ticket, plan, **Acceptance**, numbered **Steps** |
| Implement | `implement-change <name>` on `feature/<name>`, one commit per issue | `implement-change <KEY>` on `rework/<KEY>`, one commit per step; **step 0 is the characterisation tests** |
| Review | `review-change <name>` against the PRD and issues | `review-change <KEY>` against `ticket.md`; the bar is "behaviour unchanged" |
| Close | `close-change <name>`: status headers, prune `issues/` + `reviews/` | `close-change <KEY>`: delete `docs/rework/<KEY>/`; the tracker is the record |

You never tell the skills which lane you are in. They work it out from which spec exists
(`grill-change` from its argument).

### The two lanes side by side, and where the branch is cut

Nothing before `implement-change` touches a branch. Session 1 commits the spec to `develop`, so the
change branch already contains it when it is cut.

```text
Feature lane                            Rework lane
────────────────────────────────────    ────────────────────────────────────
grill-change            (on develop)    grill-change <KEY>        (on develop)
to-prd + to-md-issues   (on develop)    to-rework <KEY>           (on develop)
  └─ commit prd.md + issues/*             └─ commit ticket.md
        to develop                              to develop
                    ↓                                       ↓
implement-change <name>                 implement-change <KEY>
  └─ git checkout -b feature/<name>       └─ git checkout -b rework/<KEY>
        from develop        ◄── BRANCH CREATED HERE ──►      from develop
  └─ one commit per issue                 └─ one commit per step, step 0 first
                    ↓                                       ↓
review-change <name>                    review-change <KEY>
  └─ diffs feature/<name> vs develop      └─ diffs rework/<KEY> vs develop
  └─ writes reviews/round-NN.md           └─ writes reviews/round-NN.md
        on the change branch                    on the change branch
                    ↓                                       ↓
merge to develop                        merge to develop
close-change <name>     (on develop)    close-change <KEY>        (on develop)
```

---

## Supporting skills and commands

| Tool | What it does |
|------|------|
| `to-rework` | Freezes a grilled rework ticket into `docs/rework/<KEY>/ticket.md`. The rework twin of `to-prd`. |
| `close-change` | Closes a merged change so the repo matches reality: status headers, prune specs, docs grep, every test tier, debt check. |
| `handoff` | Compacts the current session into a hand-off doc. Ad hoc, not part of the lanes: use it to pass work to another session or repo, or when a session's context gets large (say 400k+ tokens): `/handoff`, `/clear`, and carry on from the doc. |
| `diagnose` | A debugging loop for hard bugs and perf regressions: reproduce, minimise, hypothesise, instrument, fix, regression-test. |
| `/check` | Runs the quality gate: lint, format, type-check, security scan, tests. Python/Databricks only. |
| `/debt-check` | Flags cognitive debt in current work: magic numbers, undocumented business rules, unvalidated assumptions. |
| `/debt-review` | Turns `.claude/cognitive_debt.md` into a prioritised action list. |

---

## What's in this repo

```
the-pause/
├── README.md                          # this file
├── LICENSE                            # MIT, for everything original here
├── ATTRIBUTION.md                     # who authored which skill, plus upstream licence notice
├── settings.example.json              # hooks + sensible defaults to copy
├── standards/
│   ├── CLAUDE.md                      # stack-agnostic methodology + standards (repo root)
│   └── rules/                         # topic rules → <repo>/.claude/rules/
│       ├── testing.md                 # stack-agnostic testing standards (always install)
│       ├── python-tooling.md          # Python: ruff/pyright/bandit/pytest conventions
│       └── databricks-pipelines.md    # PySpark / Delta / DAB config, patterns, deployment
├── skills/                            # 11 skills (see ATTRIBUTION.md for provenance)
│   ├── tdd/  diagnose/  handoff/                           # Matt Pocock's (vendored)
│   ├── to-prd/  to-md-issues/                              # derived from Matt Pocock's
│   ├── to-rework/                                          # ours (rework-lane twin of to-prd)
│   └── grill-change/  implement-change/  review-change/  close-change/  mutation-testing/   # ours
├── commands/
│   ├── check.md  debt-check.md  debt-review.md             # active
│   └── _deprecated/research.md  _deprecated/spec.md        # see "Evolution" below
└── hooks/
    └── capture_decisions.sh           # appends DECISION/ASSUMPTION/DEBT markers to cognitive_debt.md
```

---

## Setup

1. **Standards.** Copy `standards/CLAUDE.md` to your repo root as `CLAUDE.md`, and
   `standards/rules/testing.md` to `<repo>/.claude/rules/`. On Python + Databricks, add
   `python-tooling.md` and `databricks-pipelines.md` there too. Keep them as separate files, each
   under ~200 lines; that is what keeps the agent following them. The `## Agent skills` block in
   `CLAUDE.md` is already set up for local markdown issues.

2. **Skills.** Symlink each skill into `~/.claude/skills/` (user-wide) or `<repo>/.claude/skills/`:
   `ln -s <the-pause>/skills/<name> ~/.claude/skills/<name>`. One link per skill, so your own skills
   can sit beside them. An edit here is then live in your next session. Copy instead only if the
   profile is on another machine.
   `grill-change` also needs Matt Pocock's `grilling` and `domain-modeling` skills, installed from
   [`mattpocock/skills`](https://github.com/mattpocock/skills); they are not vendored. You can take
   his three vendored skills from there too. See `ATTRIBUTION.md`.

3. **Commands.** Copy `commands/*.md` into `~/.claude/commands/` or `<repo>/.claude/commands/`.
   `/check` assumes Python/Databricks; adapt or skip it.

4. **Hook (optional).** Copy `hooks/capture_decisions.sh` to `<repo>/.claude/hooks/` and merge the
   `PostToolUse` entries from `settings.example.json` into `.claude/settings.json`. It collects
   `# DECISION:`, `# ASSUMPTION NEEDED:` and `# DEBT:` comments into `.claude/cognitive_debt.md`
   (Python files only, for now).

---

## Evolution of the planning phase

Planning used to be two slash commands, `/research` and `/spec`, that each wrote a document for
sign-off. They are kept under `commands/_deprecated/` as history. Don't use them.

A document written *for* the human gets rubber-stamped. An interview that forces a decision at every
branch surfaces the disagreements a document hides. So the grilling skills replaced them: the
conversation is where the shared understanding forms, and `CONTEXT.md`, the ADRs and the PRD fall
out of it.

---

## Credits

The planning and TDD skills come from **Matt Pocock**
([`mattpocock/skills`](https://github.com/mattpocock/skills)). [`ATTRIBUTION.md`](./ATTRIBUTION.md)
says exactly what is his, what is derived, and what is original here.
