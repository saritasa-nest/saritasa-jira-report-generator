from collections import defaultdict
from typing import List

from jira.resources import Component
from pandas import DataFrame

from ..utils.tags import TD, TH, TR, Table

HOURS_NDIGITS = 1
OVERTIME_NDIGITS = 2


def calculate_avg_overtime(overtimes: List[float]) -> float:

    try:
        result = sum(overtimes) / len(overtimes)
    except ZeroDivisionError:
        result = 0.0

    return result


def predict_estimate(estimate: float, overtime: float) -> float:
    return estimate * overtime


def generate_component_columns(
        df: DataFrame,
        components: list,
        component_overtimes_map: dict = None,
        display_overtime: bool = False,
        summary: bool = False,
) -> List[TD]:
    columns = []

    for component in components:
        component_tasks = df[df["components"].apply(
            lambda x: component in x
        )]
        avg_component_overtime = None

        # generate empty columns
        if component_tasks.empty:
            columns.append(TD())
            columns.append(TD())
            columns.append(TD())
            columns.append(TD())
            columns.append(TD())
            continue

        component_estimate = round(
            component_tasks.estimate.sum(),
            HOURS_NDIGITS,
        )
        component_spent = round(
            component_tasks.spent.sum(),
            HOURS_NDIGITS,
        )
        component_overtime = None

        # calculate overtime only for non-summary rows
        if component_spent and component_estimate and not summary:
            component_overtime = component_spent / component_estimate

        # calculate component avg overtime
        if component_overtimes_map:
            avg_component_overtime = calculate_avg_overtime(
                component_overtimes_map[component.id]
            )

        if summary and avg_component_overtime:
            component_overtime = avg_component_overtime

        columns.append(TD(component_tasks.id.count()))
        columns.append(TD(component_estimate))
        columns.append(TD(component_spent, **{
            "class": (
                "danger"
                if component_estimate != 0
                    and component_spent > component_estimate
                else ""
            ),
        }))
        columns.append(TD(
            round(component_overtime, OVERTIME_NDIGITS)
            if component_overtime and (display_overtime or summary)
            else "",
        ))
        columns.append(TD(
            round(predict_estimate(
                component_estimate,
                avg_component_overtime,
            ), HOURS_NDIGITS)
            if avg_component_overtime
            else "",
            title=f"{component_estimate}*{avg_component_overtime}"
        ))

    return columns


def generate_versions_table(
    df: DataFrame,
    versions: list,
    **table_options: str,
):
    rows = []
    header = TR()
    subheader = TR()
    components = sorted(
        filter(
            lambda x: isinstance(x, Component),
            df.components.explode().unique().tolist()
        ),
        key=lambda x: getattr(x, "name", ""),
    )
    overtimes = []
    component_overtimes_map = defaultdict(list)

    # header
    header.append(TH("Version", **{"rowspan": 2}))
    header.append(TH("Start Date", **{"rowspan": 2}))
    header.append(TH("Release Date", **{"rowspan": 2}))
    header.append(TH("Tasks", **{
        "rowspan": 2,
        "class": "subheader hours",
    }))
    header.append(TH("Estimated", **{
        "rowspan": 2,
        "class": "subheader hours",
    }))
    header.append(TH("Spent", **{
        "rowspan": 2,
        "class": "subheader hours",
    }))
    header.append(TH("Overtime", **{
        "rowspan": 2,
        "class": "subheader hours",
    }))
    header.append(TH("Projection", **{
        "rowspan": 2,
        "class": "subheader hours",
    }))

    for component in components:
        header.append(TH(component.name, **{"colspan": 5}))

    rows.append(header)

    # add components
    for _ in components:
        subheader.append(TH("Count", **{"class": "subheader hours"}))
        subheader.append(TH("Estimated", **{"class": "subheader hours"}))
        subheader.append(TH("Spent", **{"class": "subheader hours"}))
        subheader.append(TH("Overtime", **{"class": "subheader hours"}))
        subheader.append(TH("Projection", **{"class": "subheader hours"}))

    rows.append(subheader)

    # body
    for version in versions:
        row = TR()
        version_tasks = df[df["versions"].apply(lambda x: version in x)]
        estimate = round(version_tasks.estimate.sum(), HOURS_NDIGITS)
        spent = round(version_tasks.spent.sum(), HOURS_NDIGITS)
        overtime = None
        avg_overtime = None

        if spent and estimate:
            overtime = spent / estimate

        if overtimes:
            avg_overtime = calculate_avg_overtime(overtimes)

        row.append(TD(version.name, **{
            "class": "success" if version.released else "",
        }))
        row.append(TD(getattr(version, "startDate", "")))
        row.append(TD(getattr(version, "releaseDate", "")))
        row.append(TD(version_tasks.id.count()))
        row.append(TD(estimate))
        row.append(TD(spent, **{
            "class": (
                "danger"
                if estimate != 0 and spent > estimate
                else ""
            ),
        }))

        # overtime
        row.append(TD(
            round(overtime, OVERTIME_NDIGITS)
            if overtime is not None and version.released
            else ""
        ))

        # estimate prediction
        row.append(TD(
            round(predict_estimate(
                estimate,
                avg_overtime,
            ), HOURS_NDIGITS)
            if avg_overtime
            else "",
            title=f"{estimate}*{avg_overtime}",
        ))

        # add component columns filled in with values
        for col in generate_component_columns(
                version_tasks,
                components,
                component_overtimes_map,
                display_overtime=version.released,
                summary=False,
        ):
            row.append(col)

        # add overtime prediction
        if version.released and overtime:
            overtimes.append(overtime)

            # generate and store component overtimes map
            for component in components:
                component_tasks = version_tasks[
                    version_tasks["components"].apply(
                        lambda x: component in x
                    )
                ]
                component_estimate = component_tasks.estimate.sum()
                component_spent = component_tasks.spent.sum()

                if not component_estimate and not component_spent:
                    continue

                component_overtimes_map[component.id].append(
                    (component_spent / component_estimate),
                )

        rows.append(row)

    # footer
    row = TR(**{"class": "summary"})
    estimate = round(df.estimate.sum(), HOURS_NDIGITS)
    spent = round(df.spent.sum(), HOURS_NDIGITS)
    avg_overtime = calculate_avg_overtime(overtimes)

    row.append(TD("Summary", colspan=3))
    row.append(TD(df.id.count()))
    row.append(TD(estimate))
    row.append(TD(spent, **{
        "class": (
            "danger"
            if estimate != 0
                and spent > estimate
            else ""
        ),
    }))
    row.append(TD(
        round(avg_overtime, OVERTIME_NDIGITS) or ""
    ))
    row.append(TD(
        round(predict_estimate(
            estimate,
            avg_overtime,
        ), HOURS_NDIGITS) or "",
        title=f"{estimate}*{avg_overtime}",
    ))

    # add summary component columns filled in with values
    for col in generate_component_columns(
            df,
            components,
            component_overtimes_map,
            display_overtime=False,
            summary=True,
    ):
        row.append(col)

    rows.append(row)

    return Table(rows, **table_options)
