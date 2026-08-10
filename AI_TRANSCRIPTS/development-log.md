# Development log

How the repository was built, in order, including the parts that went wrong.

Tool: Claude Code (Opus 5) in the VS Code extension. The agent had a project `CLAUDE.md`
in place from the start, asking for simplicity over cleverness, surgical changes, stated
assumptions, and verification loops rather than declarations of success. That file is
committed, so its influence on the code is visible.

---

## 1. Setup

Reset the working directory to the freshly-downloaded exercise zip and initialised the
repository. Two things I made the agent handle carefully:

- The exercise brief PDF was in the initial commit. Since the repository is public, it
  was removed from history with `filter-branch` before the first push, so Ferocia's
  material is not republished. The dataset stayed — it is the public UCI *Bank Marketing*
  set.
- I renamed `claude.md` to `CLAUDE.md` mid-operation, which landed the agent's `--amend`
  on my commit instead of its own and left the PDF in the root commit. It caught this
  when verifying the push, purged the blob, and split my rename back out into its own
  commit so the history stayed truthful.

## 2. Research before code

I asked for research first, rather than starting with the model. Two agents ran in
parallel: one on prior art for this dataset, one on the role and company (the latter is
private preparation and is not included here).

The dataset research changed the plan in two concrete ways:

- **Provenance.** The widely-cited AUC 0.80 / ALIFT 0.70 benchmark comes from Moro,
  Cortez & Rita (2014), which used a *different and richer* extract with 22 features
  including the Euribor rate. The file in this exercise is from the 2011 CRISP-DM paper.
  Without this I would have quoted the wrong benchmark, and the absence of macroeconomic
  variables would not have made it into `INSIGHTS.md` as the first-order gap it is.
- **What an honest score looks like.** Published results without `duration` sit around
  0.76–0.80 ROC-AUC, against the ~0.93 that public notebooks report with it. That gave me
  a falsifiable expectation before training anything: the pipeline produced 0.803 on the
  random split, which is the range it should be in.

It also confirmed that recovering the campaign year from month rollovers appears to be
undocumented for this file, and that there is no published out-of-time protocol for it —
so `PLAN.md` states that the argument rests on author precedent and first principles
rather than pretending a citation exists.

## 3. Plan, then implement one step at a time

`PLAN.md` was written before the pipeline and updated as decisions changed. Each step
below is one commit.

**EDA → year recovery → preprocessing → metrics → models → CLI.**

Metrics deliberately came before models, so the definition of "good" was fixed before
seeing any scores.

## 4. Three things the agent got wrong, and how they surfaced

All three were caught by tests or warnings rather than by review, which is the argument
for writing them.

**A test that asserted something impossible.** It wrote a test claiming shuffled rows
would be rejected by the year reconstruction. The test failed. The reason is interesting:
a backwards month step is *defined* as a year boundary, so month-level disorder is
silently reinterpreted as another year and cannot be detected at all. The guard only
catches disorder within a single month. Rather than delete the test, it now documents the
limitation, and the docstring says so — the reconstruction is only trustworthy because
the recovered span matches the dataset's published date range.

**Ranking ties broken by row order.** `precision@k` used a stable sort, so customers with
identical scores were ranked by their position in the file. The prior baseline predicts
one constant for everybody, so its entire ranking was the CSV's ordering — which is
contact date, along which the subscription rate drifts from 3% to 61%. The baseline would
have been scored against that drift instead of against chance. Ties are now broken by a
fixed shuffle, and the baseline lands on exactly 0.5 ROC-AUC as it should.

**An imputer that silently dropped a column.** A warning during the model tests revealed
that no customer has a prior contact before 2008-10-21, so early training windows are
100% sentinel for `pdays`; a median is undefined there and scikit-learn drops the feature
entirely, changing the feature set depending on which period you train on. Switched to a
constant fill outside the observed range with `keep_empty_features=True`. Chasing that
warning is also what surfaced the 10.4% → 49.1% shift in prior-contact share between
periods, which became a substantive point in `INSIGHTS.md`.

## 5. Where I overrode it

- **`class_weight="balanced"`** was in the original plan as a reflex for the 11.7%
  positive rate. Removed: it barely moves a ranking, it inflates predicted probabilities,
  and calibration is already the weakest part of the out-of-time result.
- **Scope.** The consistent failure mode was proposing more abstraction, more model
  variants and more configurability than three hours or the brief justified. The
  `CLAUDE.md` rules helped, but this still needed active pushback.
- **Analytical precision in the write-up.** A draft of `INSIGHTS.md` presented "lift as a
  share of its ceiling" and "top-decile precision" as two separate findings. They are the
  same quantity — the ratio reduces algebraically to `precision@k`. Corrected to state it
  once, with the derivation.

## 6. What the agent was genuinely good at

Catching its own errors when asked to verify rather than assert; refusing to publish the
brief PDF publicly without flagging the consequence first; and research breadth — the
provenance correction in §2 is something I would not have found on my own inside the time
budget.
