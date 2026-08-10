# Insights, recommendations and next steps

Every number quoted here is produced by `make train` and lives in
[artifacts/results.csv](artifacts/results.csv), or comes from
[notebooks/01_eda.ipynb](notebooks/01_eda.ipynb).

**The short version.** The Part A model answers "who says yes when we call them?" The
business question is "who should we call?" Those are different questions, and the gap
between them is not a modelling deficiency I can close with better features — it is
baked into how the data was collected. Everyone in this dataset was called, so there is
no untreated comparison group, and the model necessarily learns the bank's existing
targeting policy alongside genuine customer propensity. My recommendation is to change
what we estimate, from *response* to *incremental response*, and to accept that doing so
requires collecting data this dataset cannot provide.

---

## 1. What this modelling strategy assumes, and where it breaks

### 1.1 That the data describes the decision we are about to make

Every row is a customer someone chose to call. We observe
`P(subscribe | called, customer)` and never `P(subscribe | not called, customer)`.

A model fitted on this is therefore a mixture of two things: how customers behave, and
how the bank's existing targeting worked. Ranking by it reproduces the current policy's
preferences and calls that "prediction". If the campaign team already avoided calling,
say, customers with low balances, the model learns that low balance predicts non-response
partly because the few low-balance customers who *were* called are an unusual subset of
them.

This gets worse on contact with reality. Deploy the ranking, and next year's training
data is filtered by *this model's* choices. The selection tightens with each round, the
model looks increasingly accurate on the population it selects, and the segments it
writes off are never sampled again to prove it wrong.

**This is the central problem, and no amount of feature engineering touches it.**

### 1.2 That a subscription following a call was caused by the call

Without a control group, response and causation are indistinguishable. Some customers
would have subscribed anyway — the model happily ranks them at the top, the campaign
takes the credit, and the agent-hours were wasted. Others might have been actively
annoyed. In uplift terms the population divides four ways:

| | would subscribe if called | would not |
| --- | --- | --- |
| **would subscribe if not called** | sure things — calling wastes effort | sleeping dogs — calling *loses* the sale |
| **would not if not called** | persuadables — the only ones worth calling | lost causes |

A response model scores sure things and persuadables identically, because from its
perspective they look the same: called, and subscribed. The strongest signal in the
data is a clue that this matters — customers whose previous campaign ended in success
convert at **64.7%** (n=1,511) against **9.2%** for those with no campaign history. Some
large share of that 64.7% is very likely sure things. We cannot tell which, and the model
will keep sending agents to them.

### 1.3 That the relationship is stable enough to extrapolate

It is not, and the pipeline measures how badly. Splitting out of time rather than at
random:

| evaluation (gradient boosting) | ROC-AUC |
| --- | --- |
| random split, with `duration` | 0.934 |
| random split, no `duration` | 0.803 |
| **out-of-time split, no `duration`** | **0.679** |

Roughly half of the usual headline figure is leakage and the other half is the split.
The 0.803 matches the range published for honest random-CV treatments of this dataset,
which suggests the pipeline is behaving normally and it is the *evaluation protocol*
that is usually flattering.

The instability is not subtle. Across the campaign the monthly subscription rate moves
between **3.2% and 61.3%**. My training period converts at **6.7%** and my test period at
**31.1%**. The data spans May 2008 – Nov 2010, so the macroeconomic backdrop is the
financial crisis, and the published work on the richer version of this dataset found the
Euribor rate to be the single strongest driver of subscription — a variable that is
**entirely absent from the file we were given**. We are modelling a phenomenon whose
main cause we cannot see.

### 1.4 That the test period is even the same problem

Two population facts, not just rate drift:

- No customer has a prior contact before **2008-10-21** — early rows are 100% "never
  contacted", because the campaign had not run yet.
- Customers with a prior contact are **10.4%** of my training period and **49.1%** of my
  test period.

So the later campaign is substantially a *re-contact* operation aimed at a warm list,
while the earlier one was cold calling. Training on one to predict the other is closer to
transfer learning than to interpolation. A model reporting a single accuracy number
conceals that entirely.

### 1.5 That a good ranking is a good decision

It is not, because a decision needs a level, not just an order. The out-of-time model
predicts a mean probability of **0.148** against an observed **0.311** — it is
systematically under-confident by a factor of two, because it was fitted on a 6.7% period
and applied to a 31% one. Anyone multiplying its output by an expected deposit value to
compute revenue per call would be wrong by more than half, and any fixed decision
threshold calibrated on the training period would be meaningless on the test period.

Ranking survives drift far better than calibration does. That is worth knowing before
someone builds a business rule on the probability.

### 1.6 That "lift" means what it appears to mean

My own headline metric needs the same scepticism. Lift@10% is **1.69** out of time and
**4.46** on the random split, which reads as the random split producing a far better
model. It is not. Lift is bounded by `1 / base_rate`, and the two base rates differ
(31.1% vs 11.7%), so the ceilings are 3.21 and 8.55 respectively.

Expressed as a share of its own ceiling, lift reduces exactly to precision@k:

```
lift@k / (1 / base_rate)  =  (precision@k / base_rate) × base_rate  =  precision@k
```

And precision@10% is **0.527** out of time against **0.522** on the random split. The
2.6× difference in lift is entirely an artefact of the denominators — the two models put
essentially the same proportion of genuine subscribers in their top decile.

The honest reading: out of time, the model's *top decile* is just as good, and its
*overall ranking* is worse (AUC 0.679 vs 0.803) because it orders the middle and tail
badly. That distinction matters operationally — if we only ever call the top 10%, the
drift costs us much less than the AUC drop implies.

### 1.7 That the target is the business objective

`y` records whether a customer subscribed during this campaign. It says nothing about:

- **Deposit size or term**, so a $2,000 twelve-month deposit and a $200,000 five-year one
  are the same event. Ranking by probability rather than expected value is almost
  certainly leaving money on the table.
- **Margin**, which for a term deposit depends on the rate paid versus the wholesale
  curve. A model that maximises subscriptions can happily maximise the sale of the
  bank's least profitable product.
- **Cannibalisation.** A customer moving an existing at-call savings balance into a term
  deposit generates a "success" while producing little or no new funding. Without balance
  history we cannot separate new money from shuffled money.
- **What happens next** — retention at maturity, or whether the customer stays engaged.

### 1.8 That contacting people is free

There is no cost side anywhere in this model. The data shows one customer contacted **63
times** in a single campaign. Optimising conversion alone gives a system no reason to
stop, and the costs it ignores are real: agent time, and the more expensive one, customer
trust. For a bank whose relationship with customers is its actual product, a term deposit
sold by pestering someone can be a net negative even when the model counts it as a win.

### 1.9 Smaller data-quality traps that would mislead a reader

- **`duration` is target leakage** and is excluded. Alone it reaches **0.808 ROC-AUC**,
  and its inclusion is what produces the ~0.93 figures common in public notebooks. It is
  the duration of the call being predicted, so it cannot inform who to call.
- **`pdays = -1` is a sentinel**, not a small number, and is collinear with
  `poutcome = "unknown"` — they disagree on 5 of 45,211 rows. One-hot encoding both hands
  the model the same fact twice and makes any coefficient story unreliable.
- **`contact = "unknown"` converts at 4.1%** against 14.9% for cellular. That looks like
  a customer attribute and is more plausibly an artefact of record-keeping: it is likely
  telling us *when the record was created*, not something about the person.
- **The year is not in the data.** I reconstructed it by counting backwards steps in the
  month sequence; the recovered span (May 2008 – Nov 2010) matches the published
  description, which is the only external check available. A backwards step is *defined*
  as a year boundary, so the method cannot detect genuinely out-of-order rows.

### 1.10 Fairness, in a regulated consumer-banking setting

The model uses `age`, `marital`, `job` and `education`. These are legitimate predictors
of interest in a term deposit and also proxies for characteristics a bank should be
careful about targeting on. Nothing here is unlawful on its face, but "our model said to
call retirees" is a position that needs a considered answer, and I would want the
fairness analysis done before deployment rather than after a complaint.

---

## 2. How I would evolve the approach

### 2.1 Change the estimand: from response to incremental response

The objective should not be `P(subscribe | called)` but the **uplift**

```
τ(customer) = P(subscribe | called) − P(subscribe | not called)
```

and, one step further, expected incremental *margin* per contact rather than probability.
This targets persuadables and deliberately skips sure things, which is where the wasted
agent-hours currently go. The standard toolkit is well established — two-model/T-learner
approaches, class-transformation methods, uplift trees, causal forests — evaluated with
Qini/AUUC rather than AUC.

### 2.2 The constraint that blocks it, stated plainly

**This dataset cannot support uplift estimation.** Every row was contacted. There is no
untreated group, and treatment was not randomised. No estimator recovers a counterfactual
that was never observed; a model trained to "predict uplift" on this data would be
producing a number with no referent.

I would rather say that than quietly fit a two-model uplift estimator and present the
output as causal, which is the common failure mode here.

### 2.3 What can honestly be done with the data as it stands

Short of a randomised holdout, there is still useful causal work, provided the claims stay
matched to what the design supports:

- **Propensity-score work on the treatment variation we *do* observe.** Contact channel
  varies (cellular / telephone / unknown), as does contact order and timing. Comparing
  *variants of treatment* among the treated is defensible in a way that comparing treated
  to a non-existent control is not. "Does cellular outperform landline once we adjust for
  who gets called on which?" is answerable now.
- **Difference-in-differences across campaign waves**, if customer identifiers and
  pre-period balances can be recovered from the source systems — comparing customers who
  entered a wave against similar customers who had not yet been reached.
- **Instrumental variables**, where operational quirks assign calls in ways unrelated to
  propensity — agent rostering, list ordering, capacity constraints. This dataset carries
  no such instrument, but the call-centre logs plausibly do.
- **Cost-sensitive ranking now**, without any new data: rank by expected value rather than
  probability once deposit value is joined in, and recalibrate on a rolling window so the
  probability level tracks the current period instead of the training period.

### 2.4 The data I would need, in priority order

1. **A randomised holdout** — a genuine untreated control group, permanently. Everything
   causal depends on this one item.
2. **Outcome economics** — deposit amount, term, and margin, so the objective can be
   expected value rather than a click-like event.
3. **Customer panel data** — balances and product holdings before and after, to measure
   new funding rather than internal transfers, and to enable difference-in-differences.
4. **Call metadata** — agent, timestamp, attempt sequence, disposition. Also the raw
   material for fatigue modelling and for instruments.
5. **Macroeconomic covariates** — the cash rate and the term-deposit-to-wholesale spread.
   The literature on the richer version of this dataset found this to be the dominant
   driver, and its absence here is a first-order gap.
6. **Consent and suppression state**, which is a hard constraint on the eligible
   population rather than a feature.

### 2.5 What I would keep

The out-of-time evaluation, the leakage quarantine, and the rank-based metrics. Whatever
replaces the current model still has to be evaluated on a future period it has not seen,
and still has to be judged on what the top of its list is worth.

---

## 3. An experiment to prove the new approach is better

### 3.1 Design

A three-arm randomised trial, assigned at the **customer** level (not the call level, so
that repeat contacts cannot contaminate arms), stratified by prior-contact status and
segment because those shift so much between periods.

| arm | who is called | purpose |
| --- | --- | --- |
| **A — untreated holdout** | nobody | provides the counterfactual; the whole point |
| **B — baseline** | top-ranked by the Part A response model | the incumbent to beat |
| **C — treatment** | top-ranked by expected incremental margin | the proposal |

Arms B and C get the **same call capacity**, so the comparison is like-for-like: the same
number of agent-hours spent on two different lists.

Arm A is the part that usually gets negotiated away, and it is the part I would defend
hardest. It is not merely a measurement device — it is the *only* mechanism that generates
the untreated outcomes needed to train any uplift model at all. Without it, the next
iteration is stuck exactly where this one is. Its cost is the foregone subscriptions from
customers we deliberately do not call, which is bounded, quantifiable up front, and small
relative to the value of finally being able to measure causally.

### 3.2 Metrics

**Primary:** incremental subscriptions per 1,000 contacts, C versus B. One metric, chosen
before the test starts.

**Secondary:** incremental *margin* per agent-hour (the metric the business actually
cares about, kept secondary only because margin data quality is usually worse);
uplift-model quality on arm A data via the Qini coefficient; calibration on the live
period.

**Guardrails**, any one of which halts or reverses a rollout regardless of the primary:

- complaint and opt-out rate per thousand contacts
- contacts per customer per period, with a hard fatigue cap
- outcomes across age, job and education segments, checking we have not built something
  that works by concentrating calls on one group
- net new funding rather than transfers from existing savings, to catch cannibalisation
- retention at deposit maturity, to catch a short-term win that costs a relationship

### 3.3 Statistical validity

**Sizing.** From `term_deposit.power.required_sample_size`, at 80% power and α = 0.05
two-sided:

| base rate | +10% relative | +20% | +30% |
| --- | --- | --- | --- |
| 11.7% (overall) | 12,354 / arm | 3,211 / arm | 1,480 / arm |
| 31.1% (recent period) | 3,566 / arm | 910 / arm | 411 / arm |

This is the uncomfortable and important part. At this campaign's average volume of about
**1,500 calls a month** — and the final six months of the data average nearer **230** — a
three-arm test powered to detect a 10% relative improvement would run for **years**. The
honest conclusions are: power the test for an effect worth acting on (20–30%, not 10%),
run it on a materially larger contactable population than this campaign used, or accept
a longer horizon. Promising a quick read on a small effect would be the dishonest option.

**Protecting the result:**

- Pre-register the primary metric, the segments, and the analysis before launch.
- No peeking at the primary. If interim looks are needed operationally, use a
  group-sequential design with alpha spending, or always-valid confidence sequences.
- Run an **A/A test first** to validate the randomisation and the measurement plumbing.
- Use **CUPED** with pre-period balance and tenure as covariates. Variance reduction here
  is the cheapest way to shorten the test, and it does not cost any statistical validity.
- Run across at least a full seasonal cycle, or block by month. The monthly rate ranges
  from 3.2% to 61.3%, so a short test could measure the calendar instead of the model.
- Treat all segment-level results as exploratory, and correct for multiplicity if any
  becomes a decision.

**Decision rule.** Ship C if the primary improves with the confidence interval excluding
zero, *and* every guardrail holds. If the primary is flat but the fatigue and complaint
guardrails improve at equal conversion, that is still a win worth taking — a shorter call
list at the same result is cheaper and less intrusive.

### 3.4 One compliance note

Outbound calls offering a financial product engage Australia's anti-hawking provisions
(Corporations Act ss 992A/992AA), though basic banking products — which term deposits
generally are — sit outside the prohibition, and there are existing-client carve-outs.
Direct marketing also engages APP 7 under the Privacy Act. I would want this confirmed by
someone who does it for a living before designing the contact strategy, rather than
asserted by me from the outside; I flag it because "the model said to call them" is not a
defence, and because the untreated holdout arm raises no such issue at all.

---

## What I would do with more time

In rough order of expected value:

1. **Join deposit value and margin**, and re-rank by expected value rather than
   probability. Probably the largest single improvement available without new experiments.
2. **Rolling-origin evaluation** instead of one out-of-time cut, so drift is characterised
   as a trend rather than a single before/after comparison.
3. **Recalibration on a rolling window** (isotonic or Platt on the most recent period),
   which addresses §1.5 directly and cheaply.
4. **Fairness analysis** across age, job and education before any deployment.
5. **Sensitivity analysis** for §1.1 — bounds on how strong unobserved confounding would
   have to be to overturn the ranking, since we cannot eliminate it.
6. **Comprehensive unit tests.** I have tested the load-bearing logic — year recovery,
   the sentinel handling, split leakage, the metrics — but in production every
   preprocessing function would be tested, and the pipeline would have an end-to-end
   regression test pinning the reported numbers.
7. **Hyperparameter search and richer feature engineering**, deliberately last. It is the
   part with the smallest effect on the business outcome, and the exercise explicitly
   scopes it out.
