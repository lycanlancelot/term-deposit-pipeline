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

from term_deposit.data import add_campaign_date, load_raw
from term_deposit.experiment import fit_reference_model, run_grid
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
    axis.plot(called, captured, label="gradient boosting", color="steelblue")
    axis.plot([0, 1], [0, 1], ls="--", color="grey", label="calling at random")
    axis.set_xlabel("share of the customer list called")
    axis.set_ylabel("share of all subscribers reached")
    axis.set_title("Out-of-time gains curve, no leakage")
    axis.legend()
    figure.tight_layout()
    figure.savefig(destination, dpi=150)
    plt.close(figure)


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

    model, test = fit_reference_model(frame, seed=arguments.seed)
    _write_gains_curve(model, test, arguments.artifacts / "gains_curve.png")

    print(reported.to_string(index=False))
    print(f"\nwrote results.csv, results.md and gains_curve.png to {arguments.artifacts}/")


if __name__ == "__main__":
    main()
