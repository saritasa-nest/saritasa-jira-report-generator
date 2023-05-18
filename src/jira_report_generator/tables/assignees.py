from numpy import nan
from pandas import DataFrame

from ..utils.colors import get_danger_color_class
from ..utils.tables import generate_component_columns
from ..utils.tags import TD, TH, TR


def generate_assignees_table(df: DataFrame, assignees: list):
    rows = []
    header = TR()
    subheader = TR()

    components = sorted(
        filter(
            lambda x: x is not nan,
            df.components.explode().unique().tolist(),
        ),
        key=lambda x: getattr(x, "name", ""),
    )

    def _generate_row(name, df, components, estimate, spent, **attrs) -> TR:
        row = TR(**attrs)
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
            row.append(col)

        return row

    # header
    header.append(TH("Assignee", **{"class": "nowrap", "rowspan": 2}))
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
    for assignee in assignees:
        assignee_issues = df[df["assignee"].apply(
            lambda x: x == assignee,
        )]
        count = len(assignee_issues)

        if count == 0:
            continue

        rows.append(
            _generate_row(
                getattr(assignee, "displayName", None),
                assignee_issues,
                components,
                round(assignee_issues.estimate.sum(), 1),
                round(assignee_issues.spent.sum(), 1),
                **{
                    "data-assignee-id": getattr(assignee, "accountId", None),
                }
            )
        )

    return rows
