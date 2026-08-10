"""Sample sizing for the experiment proposed in INSIGHTS.md.

Kept as code rather than a number in prose so the arithmetic behind "this test needs N
customers per arm" can be checked and re-run with different assumptions.
"""

from __future__ import annotations

import math

from scipy.stats import norm


def required_sample_size(
    baseline_rate: float,
    relative_lift: float,
    alpha: float = 0.05,
    power: float = 0.80,
) -> int:
    """Customers per arm needed to detect `relative_lift` on `baseline_rate`.

    Two-sided test of two independent proportions, using the normal approximation — the
    counts involved here are far into the range where that holds.
    """
    if not 0 < baseline_rate < 1:
        raise ValueError(f"baseline_rate must be in (0, 1), got {baseline_rate}")
    if relative_lift <= 0:
        raise ValueError(f"relative_lift must be positive, got {relative_lift}")

    treated_rate = baseline_rate * (1 + relative_lift)
    if treated_rate >= 1:
        raise ValueError(f"a {relative_lift:.0%} lift on {baseline_rate} exceeds 1.0")

    z_alpha = norm.ppf(1 - alpha / 2)
    z_power = norm.ppf(power)
    variance = baseline_rate * (1 - baseline_rate) + treated_rate * (1 - treated_rate)

    # Rounded up: a fractional customer cannot be recruited, and rounding down would
    # leave the test slightly under-powered.
    return math.ceil((z_alpha + z_power) ** 2 * variance / (treated_rate - baseline_rate) ** 2)
