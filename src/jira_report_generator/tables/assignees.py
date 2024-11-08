from pandas import DataFrame

from ..utils.colors import get_danger_color_class
from ..utils.tables import generate_component_columns
from ..utils.tags import TD, TH, TR, Div, Table


def generate_assignees_table(
    df: DataFrame,
    assignees: list,
    **table_options: str,
):
    rows = []
    scrollable_rows = []

    components = sorted(
        df.components.explode().unique().tolist(),
        key=lambda x: getattr(x, "name", ""),
    )

    def _generate_row(name, df, components, estimate, spent, **attrs) -> TR:
        row = TR(**attrs)
        scrollable_row = TR(**attrs)
        left = round(estimate - spent, 1)

        row.append(TD(name))
        row.append(TD(len(df)))
        row.append(TD(estimate))
        row.append(TD(spent, **{
            "class": get_danger_color_class(spent > estimate),
        }))
        row.append(TD(left if estimate and left > 0 else 0))

        # add component columns filled in with values
        for col in generate_component_columns(df, components):
            scrollable_row.append(col)

        return row, scrollable_row

    # header
    header = TR(**{"class": "h50"})
    header.append(TH("Assignee", **{"class": "nowrap"}))
    header.append(TH("Count", **{"class": "hours"}))
    header.append(TH("Estimated", **{"class": "hours"}))
    header.append(TH("Spent", **{"class": "hours"}))
    header.append(TH("Left", **{"class": "hours"}))
    rows.append(header)

    # scrollable header
    scrollable_header = TR(**{"class": "h25"})
    for component in components:
        scrollable_header.append(TH(component.name, **{"colspan": 4}))
    scrollable_rows.append(scrollable_header)

    # scrollable subheader
    scrollable_subheader = TR(**{"class": "h25"})
    kwargs = {"class": "subheader hours"}
    for component in components:
        scrollable_subheader.append(TH("Count", **kwargs))
        scrollable_subheader.append(TH("Estimated", **kwargs))
        scrollable_subheader.append(TH("Spent", **kwargs))
        scrollable_subheader.append(TH("Left", **kwargs))
    scrollable_header.append(scrollable_subheader)

    # body
    for assignee in assignees:
        assignee_issues = df[df["assignee"].apply(
            lambda x: x == assignee,
        )]
        count = len(assignee_issues)

        if count == 0:
            continue

        row, scollable_row = _generate_row(
            getattr(assignee, "displayName", None),
            assignee_issues,
            components,
            round(assignee_issues.estimate.sum(), 1),
            round(assignee_issues.spent.sum(), 1),
            **{
                "data-assignee-id": getattr(assignee, "accountId", None),
            }
        )

        rows.append(row)
        scrollable_rows.append(scollable_row)

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
