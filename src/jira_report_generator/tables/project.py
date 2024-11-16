from pandas import DataFrame

from ..utils.tags import TD, TH, TR, Table, NumTD

HOURS_NDIGITS = 1


def generate_project_table(
        versioned_df: DataFrame,
        unversioned_df: DataFrame,
        backlog_df: DataFrame,
        **table_options: str,
):
    rows = []

    # table header
    header = TR()
    header.append(TH("", **{"class": "summary"}))
    header.append(TH("Count", **{"class": "hours"}))
    header.append(TH("Estimated", **{"class": "hours"}))
    header.append(TH("Spent", **{"class": "hours"}))
    header.append(TH("Left", **{"class": "hours"}))

    rows.append(header)

    # versioned row
    versioned_row = TR()
    versioned_count = versioned_df.id.count()
    versioned_estimate = versioned_df.estimate.sum()
    versioned_spent = versioned_df.spent.sum()
    versioned_left = versioned_estimate - versioned_spent

    versioned_row.append(TD("Versioned"))
    versioned_row.append(NumTD(versioned_count))
    versioned_row.append(NumTD(round(versioned_estimate, HOURS_NDIGITS)))
    versioned_row.append(NumTD(round(versioned_spent, HOURS_NDIGITS)))
    versioned_row.append(NumTD(round(versioned_left, HOURS_NDIGITS)))

    rows.append(versioned_row)

    # unversioned row
    unversioned_row = TR()
    unversioned_count = unversioned_df.id.count()
    unversioned_estimate = unversioned_df.estimate.sum()
    unversioned_spent = unversioned_df.spent.sum()
    unversioned_left = unversioned_estimate - unversioned_spent

    unversioned_row.append(TD("Unversioned"))
    unversioned_row.append(NumTD(unversioned_count))
    unversioned_row.append(NumTD(round(unversioned_estimate, HOURS_NDIGITS)))
    unversioned_row.append(NumTD(round(unversioned_spent, HOURS_NDIGITS)))
    unversioned_row.append(NumTD(round(unversioned_left, HOURS_NDIGITS)))

    rows.append(unversioned_row)

    # backlog row
    backlog_row = TR()
    backlog_count = backlog_df.id.count()
    backlog_estimate = backlog_df.estimate.sum()
    backlog_spent = backlog_df.spent.sum()
    backlog_left = backlog_estimate - backlog_spent

    backlog_row.append(TD("Backlog"))
    backlog_row.append(NumTD(backlog_count))
    backlog_row.append(NumTD(round(backlog_estimate, HOURS_NDIGITS)))
    backlog_row.append(NumTD(round(backlog_spent, HOURS_NDIGITS)))
    backlog_row.append(NumTD(round(backlog_left, HOURS_NDIGITS)))

    rows.append(backlog_row)

    # table footer
    count_sum = versioned_count + unversioned_count + backlog_count
    estimate_sum = versioned_estimate + unversioned_estimate + backlog_estimate
    spent_sum = versioned_spent + unversioned_spent + backlog_spent
    left_sum = versioned_left + unversioned_left + backlog_left

    row = TR(**{"class": "summary"})
    row.append(TD("Summary"))
    row.append(NumTD(count_sum))
    row.append(NumTD(round(estimate_sum, HOURS_NDIGITS)))
    row.append(NumTD(round(spent_sum, HOURS_NDIGITS)))
    row.append(NumTD(round(left_sum, HOURS_NDIGITS)))

    rows.append(row)

    return Table(rows, **table_options)
