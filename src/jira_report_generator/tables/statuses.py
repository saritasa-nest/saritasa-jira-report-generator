from pandas import DataFrame

from ..utils.colors import get_danger_color_class
from ..utils.tables import generate_component_columns
from ..utils.tags import TD, TH, TR, Table


def generate_statuses_table(
    df: DataFrame,
    statuses: list,
    **table_options: str,
):
    rows = []
    header = TR()
    subheader = TR()

    if "status" not in df.columns:
        return Table(rows, **table_options)

    issues = df[df["status"].apply(lambda x: x in statuses)]
    components = sorted(
        issues.components.explode().unique().tolist(),
        key=lambda x: x.name,
    )

    if issues.empty:
        return Table(rows, **table_options)

    def _generate_row(name, df, components, estimate, spent, **attrs) -> TR:
        row = TR(**attrs)
        left = round(estimate - spent, 1)

        row.append(TD(name))
        row.append(TD(df.id.count()))
        row.append(TD(estimate))
        row.append(TD(spent, **{
            "class": get_danger_color_class(spent > estimate),
        }))
        row.append(TD(left if left > 0 else 0))

        # add component columns filled in with values
        for col in generate_component_columns(df, components):
            row.append(col)

        return row

    # header
    header.append(TH("Status", **{"rowspan": 2}))
    header.append(TH("Count", **{"rowspan": 2, "class": "hours"}))
    header.append(TH("Estimated", **{"rowspan": 2, "class": "hours"}))
    header.append(TH("Spent", **{"rowspan": 2, "class": "hours"}))
    header.append(TH("Left", **{"rowspan": 2, "class": "hours"}))

    for component in components:
        header.append(TH(component.name, **{"colspan": 4}))

    rows.append(header)

    # subheader
    for component in components:
        subheader.append(TH("Count", **{"class": "subheader hours"}))
        subheader.append(TH("Estimated", **{"class": "subheader hours"}))
        subheader.append(TH("Spent", **{"class": "subheader hours"}))
        subheader.append(TH("Left", **{"class": "subheader hours"}))

    rows.append(subheader)

    # body
    for status in statuses:
        status_issues = issues[issues["status"].apply(lambda x: x == status)]

        rows.append(
            _generate_row(
                status.name,
                status_issues,
                components,
                round(status_issues.estimate.sum(), 1),
                round(status_issues.spent.sum(), 1),
                **{
                    "data-status-id": status.id,
                },
            )
        )

    # footer
    rows.append(
        _generate_row(
            "",
            issues,
            components,
            round(issues.estimate.sum(), 1),
            round(issues.spent.sum(), 1),
            **{"class": "summary"},
        )
    )

    return Table(rows, **table_options)
