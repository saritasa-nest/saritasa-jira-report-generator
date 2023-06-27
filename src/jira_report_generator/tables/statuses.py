from pandas import DataFrame

from ..utils.colors import get_danger_color_class
from ..utils.tables import generate_component_columns
from ..utils.tags import TD, TH, TR, Div, Table


def generate_statuses_table(
    df: DataFrame,
    statuses: list,
    **table_options: str,
):
    rows = []
    scrollable_rows = []

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
        scrollable_row = TR(**attrs)
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
            scrollable_row.append(col)

        return row, scrollable_row

    # header
    header = TR(**{"class": "h40"})
    header.append(TH("Status"))
    header.append(TH("Count", **{"class": "hours"}))
    header.append(TH("Estimated", **{"class": "hours"}))
    header.append(TH("Spent", **{"class": "hours"}))
    header.append(TH("Left", **{"class": "hours"}))

    rows.append(header)

    # scrollable header
    scrollable_header = TR(**{"class": "h20"})
    for component in components:
        scrollable_header.append(TH(component.name, **{"colspan": 4}))

    scrollable_rows.append(scrollable_header)

    # scrollable subheader
    scrollable_subheader = TR(**{"class": "h20"})
    kwargs = {"class": "subheader hours"}
    for component in components:
        scrollable_subheader.append(TH("Count", **kwargs))
        scrollable_subheader.append(TH("Estimated", **kwargs))
        scrollable_subheader.append(TH("Spent", **kwargs))
        scrollable_subheader.append(TH("Left", **kwargs))

    scrollable_header.append(scrollable_subheader)

    # body
    for status in statuses:
        status_issues = issues[issues["status"].apply(lambda x: x == status)]
        row, scrollable_row = _generate_row(
            status.name,
            status_issues,
            components,
            round(status_issues.estimate.sum(), 1),
            round(status_issues.spent.sum(), 1),
            **{
                "data-status-id": status.id,
            },
        )

        rows.append(row)
        scrollable_rows.append(scrollable_row)

    # footer
    footer_row, footer_scrollable_row = _generate_row(
        "",
        issues,
        components,
        round(issues.estimate.sum(), 1),
        round(issues.spent.sum(), 1),
        **{"class": "summary"},
    )
    rows.append(footer_row)
    scrollable_rows.append(footer_scrollable_row)

    if not components:
        return Table(rows, **table_options)

    return Div(
        Div(
            Table(rows, **table_options),
            **{"class": "combined-left"},
        ),
        Div(
            Table(scrollable_rows, **table_options),
            **{"class": "combined-right scrollable"},
        ),
        **{"class": "combined"},
    )
