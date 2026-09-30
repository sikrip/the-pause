# Attribution

This repository bundles agent skills with three different provenances. We want to be precise about
what was authored where — both to credit the original authors and to be clear about what is ours.

## Skills authored by Matt Pocock (vendored unmodified)

The following skills are **Matt Pocock's work**, vendored here unchanged from
[`github.com/mattpocock/skills`](https://github.com/mattpocock/skills):

| Skill | Upstream path |
|-------|---------------|
| `tdd` | `skills/engineering/tdd/` |
| `diagnose` | `skills/engineering/diagnose/` |
| `handoff` | `skills/productivity/handoff/` |

All credit for these belongs to Matt Pocock. They are included only to make this workflow
self-contained, under the upstream MIT licence reproduced at the end of this file. If you prefer,
install them directly from `mattpocock/skills` instead of using the copies here.

## Skills derived from Matt Pocock's work (modified by us)

These started from Matt Pocock's skills and were adapted for this methodology's local-markdown,
`docs/features/<name>/` convention. Each carries a derivation note in its `SKILL.md`:

| Our skill | Derived from | What changed |
|-----------|--------------|--------------|
| `to-prd` | Matt's `to-prd` (`skills/engineering/to-prd/`) | Output moved from `./temp/prds/<name>_prd.md` to `./docs/features/<name>/prd.md`; PRD is committed to git alongside the code. |
| `to-md-issues` | Matt's `to-issues` (`skills/engineering/to-issues/`) | Reworked to emit local markdown files under `./docs/features/<name>/issues/` instead of creating issues in a remote tracker (GitHub/GitLab). |

The design and prompt structure originate with Matt Pocock; the modifications are ours.

## Skills authored by us (original)

These were written for this methodology and are not derived from anyone else's skills:

- `implement-change` (formerly `implement-feature-auto`) — the serial, unattended variant of an old `implement-feature` (a
  parallel, review-checkpointed orchestrator from Matt Pocock).
- `grill-change` — the lane entry point. Fetches a ticket when given a key, then runs Matt Pocock's
  `grilling` and `domain-modeling` skills (installed from upstream, not vendored). Replaces the vendored
  `grill-with-docs`, whose body was the same one-line delegation.
- `review-change`
- `close-change`
- `to-rework` — the rework-lane twin of `to-prd`; structure mirrors it, content is ours
- `mutation-testing`

## Slash commands, standards, and hooks

The slash commands (`/check`, `/debt-check`, `/debt-review`, and the deprecated
`/research`, `/spec`), the engineering standards (`standards/`), and the decision-capture hook
(`hooks/capture_decisions.sh`) are ours.

---

## Upstream licence

The vendored and derived skills above are used under the following licence from
[`mattpocock/skills`](https://github.com/mattpocock/skills):

```text
MIT License

Copyright (c) 2026 Matt Pocock

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
