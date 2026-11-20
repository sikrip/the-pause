---
name: walk-me-through
description: Lay out Claude's own understanding of a problem as a short sequence of steps the user can check one at a time, instead of delivering the analysis and a recommendation in one block. Each step is at most seven lines, says what is checked and what is inferred, and waits for the user before the next. Use when the user says "unpack your understanding", "walk me through it", "step by step", "one step at a time", "N lines at most each time", or pushes back on a long answer about a problem they are still forming a view on.
---

# /walk-me-through

An analysis delivered whole asks the user to trust it whole. Somewhere in it is a claim read off the
wrong file or a number inferred from totals, and the user cannot find it because it is buried in a
conclusion they have not yet reached themselves. Walking the same content in small steps lets them
stop at the first thing that looks wrong.

## Step 1 — build the steps, silently

Order them from what is known toward what is proposed. Leave out the ones that do not apply:

1. **What we received** — the request, file, feed or message, in its own terms.
2. **What our system does with it today** — the path through the code, not the intent.
3. **What the outside world actually sees** — the page, the consumer, the customer.
4. **What is missing or inconsistent in the input.**
5. **The options** — the user's own idea first if they offered one, stated fairly.
6. **The recommendation** — always last.

Five to eight steps. The recommendation never moves earlier, even if it is already obvious.

## Step 2 — one step per turn

Each turn is one step and nothing else:

- A heading: **Step N of M: what it covers.**
- At most **seven lines**. If a step needs more, it is two steps; split it and renumber rather than
  dropping something that matters. A small table counts as its rows.
- One closing line naming the next step. Then wait.

**Mark what is checked and what is not.** A claim read from the code, the data or the live system is
stated plainly. A claim inferred — from totals, from a default, from memory, from a sample — says so
in the same line: "inferred from the totals, not a row-by-row join". An unmarked claim is a promise
that it was checked.

## Step 3 — respond to what the user does

- **"next":** the next step.
- **A question:** answer it for this step, within the same limit.
- **"Close that gap" / "are you sure?":** go and check — read the code, run the query, open the
  page — then restate the step corrected, saying what changed. If the check contradicts an earlier
  step, say which one and correct it too.
- **A correction from the user:** verify it before recording it when it can be verified cheaply.
  The user can be wrong about a detail as easily as you can; say which of you the evidence backs.
- **"Note that for the reply / the comment":** add it to a running list and show the list. Do not
  draft the message mid-walk; it is written once at the end from the whole list.
- **A new angle** ("what if we did it in their admin instead"): slot it in as an option in step 5,
  and say what would have to be true for it to work.

## Step 4 — verify before the recommendation stands

When the question turns on what **another system** does — a partner's admin, a consumer's page, a
third-party API — a recommendation built on reading our own code is a guess. Before it is accepted:

- look at the real thing, in a test environment first and production second, reads only;
- compare a sample of real records end to end: what we send against what is shown;
- report what was confirmed, what changed, and the limits of the check.

Expect this to move the conclusion. Record what was learned where it will be found again.

## Step 5 — close

After the last step: the running list, drafted as the message or comment it was collected for, and
one line naming what comes next — `grill-change` when a design follows, an estimate, or nothing.

## Output

Nothing on disk. Drafts are shown, not sent, unless the user asks.
