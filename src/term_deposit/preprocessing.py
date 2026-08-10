"""Feature preparation.

Everything lives inside a scikit-learn `ColumnTransformer` so that fitting on the
training set only is structural rather than a discipline I have to remember. Statistics
like the median used for imputation and the category vocabulary are learned in `fit` and
merely applied in `transform`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

from term_deposit.data import TARGET

#: `-1` means "never contacted before" rather than a quantity, so it is not comparable
#: with the real day counts and must not be scaled alongside them.
PDAYS_SENTINEL = -1

#: Stand-in for "not applicable". Observed values start at 1, so this cannot be confused
#: with a real gap, and the paired indicator tells the model which rows it applies to.
PDAYS_FILL = 0

NUMERIC_FEATURES = ("age", "balance", "day", "campaign", "previous")
SENTINEL_FEATURES = ("pdays",)
CATEGORICAL_FEATURES = (
    "job",
    "marital",
    "education",
    "default",
    "housing",
    "loan",
    "contact",
    "month",
    "poutcome",
)

#: Excluded on purpose. `duration` is the outcome of the call being predicted; the
#: campaign date columns are the split key, and `campaign_year` would hand the model a
#: value it has never seen at prediction time.
EXCLUDED_COLUMNS = (TARGET, "duration", "campaign_date", "campaign_year")


def _sentinel_to_missing(values: pd.DataFrame) -> pd.DataFrame:
    """Turn the -1 sentinel into genuine missingness so the imputer can flag it."""
    return values.mask(values == PDAYS_SENTINEL)


def feature_columns(include_duration: bool = False) -> list[str]:
    """The columns the model is allowed to see."""
    columns = [*NUMERIC_FEATURES, *SENTINEL_FEATURES, *CATEGORICAL_FEATURES]
    return [*columns, "duration"] if include_duration else columns


def target_vector(frame: pd.DataFrame) -> pd.Series:
    """Encode the target as 1 for a subscription."""
    return frame[TARGET].eq("yes").astype(int)


def build_preprocessor(include_duration: bool = False) -> ColumnTransformer:
    """Assemble the feature transformer.

    `include_duration` exists only to quantify the cost of the leakage decision; it must
    stay off for any model whose output would inform who to call.
    """
    numeric = [*NUMERIC_FEATURES, "duration"] if include_duration else list(NUMERIC_FEATURES)

    sentinel_pipeline = Pipeline(
        [
            ("sentinel", FunctionTransformer(_sentinel_to_missing, feature_names_out="one-to-one")),
            # add_indicator keeps "was this customer ever contacted before?" as its own
            # signal instead of hiding it inside the imputed value.
            #
            # The fill is a constant outside the observed range (real values start at 1)
            # rather than the median. "Days since a contact that never happened" has no
            # meaningful central value, and the indicator already carries the fact. A
            # median would also be undefined early in the campaign: nobody has a prior
            # contact before 2008-10-21, so the first months are 100% sentinel and a
            # median imputer silently drops the column.
            (
                "impute",
                SimpleImputer(
                    strategy="constant",
                    fill_value=PDAYS_FILL,
                    add_indicator=True,
                    # Without this, scikit-learn drops a column it saw no values for,
                    # which is exactly the all-sentinel case described above.
                    keep_empty_features=True,
                ),
            ),
            ("scale", StandardScaler()),
        ]
    )

    return ColumnTransformer(
        [
            ("numeric", StandardScaler(), numeric),
            ("sentinel", sentinel_pipeline, list(SENTINEL_FEATURES)),
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False, dtype=np.float64),
                list(CATEGORICAL_FEATURES),
            ),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )
