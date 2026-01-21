from pandas import DataFrame

from ..constants import HOURS_N_DECIMAL_PLACES
from ..utils.tags import TD, TH, TR, NumTD, Table


def generate_project_table(
    versioned_df: DataFrame,
    internal_df: DataFrame,
    unversioned_df: DataFrame,
    backlog_df: DataFrame,
    other_df: DataFrame,
    **table_options: str,
):
    rows = []

    # table header
    header = TR()
    header.append(TH(""))
    header.append(TH("Count"))
    header.append(TH("Estimated", **{"class": "numeric"}))
    header.append(TH("Spent"))
    header.append(TH("Left"))

    rows.append(header)

    count_sum = 0
    estimate_sum = 0.0
    spent_sum = 0.0
    left_sum = 0.0

    for label, category_df in (
        ("Versioned", versioned_df),
        ("Internal", internal_df),
        ("Unversioned", unversioned_df),
        ("Backlog", backlog_df),
        ("Other", other_df),
    ):
        count, estimate, spent, left = _get_row_stats(category_df)
        count_sum += count
        estimate_sum += estimate
        spent_sum += spent
        left_sum += left

        row = TR()
        row.append(TD(label))
        row.append(NumTD(count))
        row.append(NumTD(round(estimate, HOURS_N_DECIMAL_PLACES)))
        row.append(NumTD(round(spent, HOURS_N_DECIMAL_PLACES)))
        row.append(NumTD(round(left, HOURS_N_DECIMAL_PLACES)))
        rows.append(row)

    row = TR(**{"class": "summary"})
    row.append(TD("Summary"))
    row.append(NumTD(count_sum))
    row.append(NumTD(round(estimate_sum, HOURS_N_DECIMAL_PLACES)))
    row.append(NumTD(round(spent_sum, HOURS_N_DECIMAL_PLACES)))
    row.append(NumTD(round(left_sum, HOURS_N_DECIMAL_PLACES)))

    rows.append(row)

    return Table(rows, **table_options)


def _get_row_stats(df: DataFrame) -> tuple[int, float, float, float]:
    count = df.id.count()
    estimate = df.estimate.sum()
    spent = df.spent.sum()
    left = estimate - spent
    return count, estimate, spent, left
