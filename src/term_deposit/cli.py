"""Command line entry point: raw CSV in, reported numbers out.

Every figure quoted in README.md and INSIGHTS.md comes from this one command, so the
claims can be checked rather than taken on trust.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # No display in CI or a plain shell.
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.calibration import calibration_curve

from term_deposit.calibration import recalibration_demo
from term_deposit.data import add_campaign_date, load_raw
from term_deposit.experiment import (
    REFERENCE_MODEL,
    fit_reference_model,
    reference_comparison,
    run_grid,
    segment_evaluation,
)
from term_deposit.metrics import gains_curve
from term_deposit.models import SEED
from term_deposit.preprocessing import feature_columns, target_vector

REPORTED_COLUMNS = [
    "split",
    "model",
    "features",
    "roc_auc",
    "pr_auc",
    "precision@10%",
    "lift@10%",
    "base_rate",
    "mean_predicted",
    "brier",
]


def _write_gains_curve(model, test, destination: Path) -> None:
    scores = model.predict_proba(test[feature_columns()])[:, 1]
    called, captured = gains_curve(target_vector(test), scores)

    figure, axis = plt.subplots(figsize=(6, 4.5))
    axis.plot(called, captured, label=REFERENCE_MODEL.replace("_", " "), color="steelblue")
    axis.plot([0, 1], [0, 1], ls="--", color="grey", label="calling at random")
    axis.set_xlabel("share of the customer list called")
    axis.set_ylabel("share of all subscribers reached")
    axis.set_title("Out-of-time gains curve, no leakage")
    axis.legend()
    figure.tight_layout()
    figure.savefig(destination, dpi=150)
    plt.close(figure)


def _write_reliability_curve(frame, seed: int, destination: Path) -> None:
    """Predicted vs observed rate by decile, before and after rolling recalibration."""
    test_y, raw, recalibrated = recalibration_demo(frame, seed=seed)

    figure, axis = plt.subplots(figsize=(6, 4.5))
    for scores, label, colour in (
        (raw, f"raw (mean {raw.mean():.3f})", "indianred"),
        (recalibrated, f"recalibrated (mean {recalibrated.mean():.3f})", "steelblue"),
    ):
        observed, predicted = calibration_curve(test_y, scores, n_bins=10, strategy="quantile")
        axis.plot(predicted, observed, marker="o", label=label, color=colour)
    axis.plot([0, 1], [0, 1], ls="--", color="grey", label="perfectly calibrated")
    axis.set_xlabel("mean predicted probability (decile bins)")
    axis.set_ylabel("observed subscription rate")
    axis.set_title(f"Reliability out of time — observed rate {test_y.mean():.3f}")
    axis.legend()
    figure.tight_layout()
    figure.savefig(destination, dpi=150)
    plt.close(figure)


def _write_coefficients(model, destination: Path) -> None:
    """The reference model's coefficients, sorted — the evidence behind INSIGHTS."""
    coefficients = pd.Series(
        model.named_steps["estimator"].coef_[0],
        index=model.named_steps["features"].get_feature_names_out(),
    ).sort_values(ascending=False)
    table = coefficients.round(3).rename("coefficient").to_frame()
    destination.write_text(
        "# Reference model coefficients\n\n"
        "Standardised inputs, so magnitudes are roughly comparable. Descriptive of the\n"
        "campaign that generated the data — **not** causal effects; see INSIGHTS.md.\n\n"
        + table.to_markdown() + "\n"
    )


def _format_ci(interval) -> str:
    return f"({interval[0]:.4f}, {interval[1]:.4f})"


def _write_reference_comparison(comparison, destination: Path) -> None:
    lines = [
        "# Reference model comparison",
        "",
        "Temporal split, no `duration`. CIs are 95% percentile bootstrap (n=1000); the",
        "delta is a *paired* bootstrap of logistic minus GBM on identical resamples.",
        "A delta interval covering zero means the models cannot be told apart here.",
        "",
        "| metric | logistic | 95% CI | GBM | 95% CI | delta (L−G) 95% CI |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for _, row in comparison.iterrows():
        lines.append(
            f"| {row.metric} | {row.logistic_regression:.4f} "
            f"| {_format_ci(row.logistic_regression_ci)} "
            f"| {row.gradient_boosting:.4f} | {_format_ci(row.gradient_boosting_ci)} "
            f"| {_format_ci(row.delta_ci)} |"
        )
    destination.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data/dataset.csv"))
    parser.add_argument("--artifacts", type=Path, default=Path("artifacts"))
    parser.add_argument("--seed", type=int, default=SEED)
    arguments = parser.parse_args()

    frame = add_campaign_date(load_raw(arguments.data))
    print(f"loaded {len(frame):,} rows spanning "
          f"{frame.campaign_date.min().date()} to {frame.campaign_date.max().date()}")

    results = run_grid(frame, seed=arguments.seed)

    arguments.artifacts.mkdir(parents=True, exist_ok=True)
    results.to_csv(arguments.artifacts / "results.csv", index=False)

    reported = results[REPORTED_COLUMNS].round(4)
    (arguments.artifacts / "results.md").write_text(reported.to_markdown(index=False) + "\n")

    comparison = reference_comparison(frame, seed=arguments.seed)
    _write_reference_comparison(comparison, arguments.artifacts / "reference_comparison.md")

    segments = segment_evaluation(frame, seed=arguments.seed)
    segment_columns = ["segment", "n", "base_rate", "roc_auc", "pr_auc", "precision@10%"]
    (arguments.artifacts / "segments.md").write_text(
        segments[segment_columns].round(4).to_markdown(index=False) + "\n"
    )

    model, test = fit_reference_model(frame, seed=arguments.seed)
    _write_coefficients(model, arguments.artifacts / "coefficients.md")
    _write_gains_curve(model, test, arguments.artifacts / "gains_curve.png")
    _write_reliability_curve(frame, arguments.seed, arguments.artifacts / "reliability_curve.png")

    print(reported.to_string(index=False))
    print(f"\nreference model: {REFERENCE_MODEL} — see reference_comparison.md for why")
    print(f"wrote artifacts to {arguments.artifacts}/")


if __name__ == "__main__":
    main()
