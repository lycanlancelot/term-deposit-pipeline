# Plan

Working plan for the exercise: predict term-deposit subscription from bank
marketing campaign data. Written before implementation so the reasoning is
visible, and updated as decisions change.

Time budget is three hours, split roughly 40% Part A (pipeline) / 60% Part B
(insights). Model performance is explicitly out of scope, so effort goes into
evaluation honesty and into the critique.

## The data

45,211 rows x 17 columns, semicolon-delimited. Target `y` is 11.70% positive
(5,289 / 39,922). This is the UCI *Bank Marketing* dataset, `bank-full.csv`.

**Provenance.** This file is the dataset from Moro, Laureano & Cortez (2011),
*Using Data Mining for Bank Direct Marketing* (ESM'11) — a CRISP-DM case study.
It is **not** the dataset behind the better-known Moro, Cortez & Rita (2014),
*Decision Support Systems* 62:22-31, which used a richer 2008-2013 extract with
22 features including socio-economic indicators (Euribor 3-month rate,
employment variation). That paper's headline **AUC 0.80 / ALIFT 0.70** is
therefore *not* a benchmark for this file, and I will not present it as one.

Three properties drive most of the design decisions below.

### 1. `duration` is target leakage

`duration` is the length of the call whose outcome we are predicting. It is
unknown before the call is placed, and once the call ends the outcome is known
anyway. UCI's own `bank-names.txt` says so:

> this attribute highly affects the output target (e.g., if duration=0 then
> y='no'). Yet, the duration is not known before a call is performed. Also,
> after the end of the call y is obviously known. Thus, this input should only
> be included for benchmark purposes and should be discarded if the intention
> is to have a realistic predictive model.

**Decision: drop `duration` from the model.** I will train one model *with* it
purely to quantify the gap, because that gap is the point: public notebooks
that keep `duration` report roughly 0.93-0.94 ROC-AUC, whereas honest published
results without it sit around **0.77-0.80 ROC-AUC**. If my number lands near
0.93, something is still leaking.

### 2. There is no year column, but the rows are chronological

`month` runs `may ... nov` with exactly **2 backwards steps** across the file,
so the data spans **three campaign years (May 2008 - Nov 2010)** in order. The
year can be recovered by counting those rollovers.

This matters because a random split scatters temporally adjacent rows across
train and test, leaking future into past and flattering the score — and this
period contains the GFC, so drift is real rather than hypothetical. The 2014
authors used a rolling-window out-of-time evaluation on their own data.

**Decision: recover the year, split out-of-time (train on earlier campaigns,
test on the latest), and report the random split alongside it** to show the
optimism gap rather than assert it. Note honestly: I found no published
out-of-time protocol for *this* file; the justification is author precedent and
first principles, not a citable dataset-specific critique.

### 3. `pdays = -1` is a sentinel, not a number

81.7% of rows have `pdays = -1`, meaning "never previously contacted". Scaled or
imputed as a numeric it becomes nonsense distance. It is also near-perfectly
collinear with `poutcome = "unknown"` (36,954 vs 36,959 rows), so naive one-hot
encoding double-counts the same fact.

**Decision:** split into a `contacted_before` boolean plus a conditional value,
and note the collinearity rather than silently encoding it twice.

## Part A — pipeline

Sequence, one commit per step:

1. **EDA notebook** — target rate, distributions, and evidence for the three
   findings above. Committed as the record of what was actually looked at.
2. **Year recovery + splitters** — derive campaign year from month rollovers;
   temporal and random splits behind one interface.
3. **Preprocessing** as a scikit-learn `ColumnTransformer`/`Pipeline`, so
   fit-on-train-only is structural rather than a thing I remember to do:
   one-hot categoricals, scale numerics, `pdays` sentinel handling, `duration`
   quarantined behind an explicit flag.
4. **Models** — prior/majority baseline, logistic regression, gradient boosting
   (`HistGradientBoostingClassifier`). No tuning beyond defaults and class
   weighting; the brief says not to optimise.
5. **Metrics** — PR-AUC, **lift / precision@k**, and a calibration check.
   Accuracy is excluded deliberately: predicting "no" for everyone scores 88.3%.
   Precision@k is framed as agent-hours — "if we can make k calls, how many
   subscribers do we reach?" — which mirrors the ALIFT metric the original
   authors used and is the form a business decision actually takes.
6. **One entry point** (`make train`) reproducing every number in the README
   from the raw CSV, with a fixed seed.
7. **Tests** on the load-bearing logic only — year recovery, `pdays` handling,
   split boundary (assert no temporal bleed). Not comprehensive coverage; see
   Concessions.

## Part B — INSIGHTS.md

The larger share of the effort. Structure follows the three questions asked.

1. **Assumptions and failure modes.** The spine is causal, not statistical:
   customers were selected for calling by the bank, not at random, so a model
   fit on call outcomes learns *the existing targeting policy* plus propensity,
   not customer behaviour. Also: leakage (above), non-stationarity (2008-2010
   macro conditions, and the strongest driver in the 2014 study — the Euribor
   rate — is absent from this file entirely), class imbalance, and the business
   flaw that ranking "who says yes when called" is not "who needs calling".
   Customer experience is treated as a real constraint here — call fatigue and
   trust are costs, and a bank that optimises purely for conversion erodes both.
2. **How to evolve it.** Reframe to **incremental response (uplift)**: target
   the persuadable, not the already-willing. State the blocking constraint
   plainly — uplift needs a randomised control group, every row in this dataset
   was contacted, so there is no untreated counterfactual and this data
   *structurally cannot* support it. Realistic intermediate steps given
   observational data: propensity scoring, difference-in-differences across
   campaign waves, instrumental-variable framing where an assignment quirk
   allows. Plus cost-sensitive thresholding from call cost vs. deposit value.
3. **Experiment.** A randomised A/B on call lists (baseline ranking vs. new
   ranking) with a genuine untreated control, which also generates the data
   Part 2 needs. Specify: primary metric (incremental subscriptions per 1,000
   calls), guardrails (contact fatigue, complaint rate, per-segment fairness),
   a power calculation off the 11.7% base rate, and pre-registered analysis to
   avoid peeking. One precise sentence on Australian anti-hawking rules — noting
   that basic deposit products are generally exempt — rather than a paragraph
   overstating the constraint.

## Deliverables

- [ ] Source code / pipeline (Part A)
- [ ] `INSIGHTS.md` (Part B)
- [ ] `README.md` with setup, results, and a **Tool Stack** section
- [ ] `AI_TRANSCRIPTS/` with session exports
- [ ] Granular git history showing iteration, not one squashed commit

## Concessions (deliberate, given three hours)

Stated here and in the README rather than left implicit:

- **Tests cover the load-bearing functions only**, not the whole pipeline. In
  production every preprocessing function gets unit-tested; one or two here
  demonstrate the intent.
- **No hyperparameter search.** Defaults plus class weighting. Out of scope by
  instruction.
- **No serving, packaging, or infrastructure** — out of scope by instruction,
  though the pipeline is written to be re-runnable end-to-end from raw data.
- **No macro/socio-economic features**, because the dataset has none. Flagged in
  INSIGHTS as a known and material gap rather than quietly ignored.

## Verification

- `uv run pytest` passes.
- `make train` runs from the raw CSV to reported metrics with a fixed seed, and
  a second run reproduces identical numbers.
- Out-of-time and random split results are reported side by side; the gap is
  discussed rather than hidden.
- The no-`duration` model lands near 0.77-0.80 ROC-AUC. Materially higher means
  leakage is still present and the pipeline is wrong.
