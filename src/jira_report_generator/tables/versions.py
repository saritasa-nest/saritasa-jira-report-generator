from collections import defaultdict
from typing import List

from jira.resources import Component
from pandas import DataFrame

from ..utils.tags import TD, TH, TR, Div, Table, Input

HOURS_NDIGITS = 1
OVERTIME_NDIGITS = 2

TASKS = "tasks"
ESTIMATED = "estimated"
SPENT = "spent"
OVERTIME = "overtime"
PROJECTION = "projection"

DATA_ROW_VERSION_ID = "data-row-version-id"
DATA_ROW_VERSION_COLUMN_NAME = "data-row-version-column-name"
DATA_COLUMN_NAME = "data-column-name"


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
            columns.append(TD("&nbsp;"))
            columns.append(TD("&nbsp;"))
            columns.append(TD("&nbsp;"))
            columns.append(TD("&nbsp;"))
            columns.append(TD("&nbsp;"))
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
    scrollable_rows = []
    components = sorted(
        filter(
            lambda x: isinstance(x, Component),
            df.components.explode().unique().tolist()
        ),
        key=lambda x: getattr(x, "name", ""),
    )
    overtimes = []
    component_overtimes_map = defaultdict(list)

    # table header
    header = TR(**{"class": "h40"})
    header.append(TH(""))
    header.append(TH("Version"))
    header.append(TH("Start Date"))
    header.append(TH("Release Date"))
    header.append(TH("Tasks", **{"class": "subheader hours"}))
    header.append(TH("Estimated", **{"class": "subheader hours"}))
    header.append(TH("Spent", **{"class": "subheader hours"}))
    header.append(TH("Overtime", **{"class": "subheader hours"}))
    header.append(TH("Projection", **{"class": "subheader hours"}))

    rows.append(header)

    # scrollable header
    scrollable_header = TR(**{"class": "h20"})
    for component in components:
        scrollable_header.append(TH(component.name, **{"colspan": 5}))

    scrollable_rows.append(scrollable_header)

    # scrollable subheader
    scrollable_subheader = TR(**{"class": "h20"})
    kwargs = {"class": "subheader hours"}
    for _ in components:
        scrollable_subheader.append(TH("Tasks", **kwargs))
        scrollable_subheader.append(TH("Estimated", **kwargs))
        scrollable_subheader.append(TH("Spent", **kwargs))
        scrollable_subheader.append(TH("Overtime", **kwargs))
        scrollable_subheader.append(TH("Projection", **kwargs))

    scrollable_header.append(scrollable_subheader)

    # body
    for version in versions:
        row = TR(**{DATA_ROW_VERSION_ID: version.id})
        scrollable_row = TR()
        version_tasks = df[df["versions"].apply(lambda x: version in x)]
        estimate = round(version_tasks.estimate.sum(), HOURS_NDIGITS)
        spent = round(version_tasks.spent.sum(), HOURS_NDIGITS)
        overtime = None
        avg_overtime = None

        if spent and estimate:
            overtime = spent / estimate

        if overtimes:
            avg_overtime = calculate_avg_overtime(overtimes)

        row.append(TD(
            Input(**{
                "type": "checkbox",
                "data-version-id": version.id,
            }),
            **{"class": "center p0"},
        ))
        row.append(TD(version.name, **{
            "class": "success" if version.released else "",
        }))
        row.append(TD(getattr(version, "startDate", "")))
        row.append(TD(getattr(version, "releaseDate", "")))
        row.append(TD(version_tasks.id.count(), **{
            DATA_ROW_VERSION_COLUMN_NAME: TASKS,
        }))
        row.append(TD(estimate, **{
            DATA_ROW_VERSION_COLUMN_NAME: ESTIMATED,
        }))
        row.append(TD(spent, **{
            "class": (
                "danger"
                if estimate != 0 and spent > estimate
                else ""
            ),
            DATA_ROW_VERSION_COLUMN_NAME: SPENT,
        }))

        # overtime
        row.append(TD(
            round(overtime, OVERTIME_NDIGITS)
            if overtime is not None and version.released
            else "",
            **{DATA_ROW_VERSION_COLUMN_NAME: OVERTIME}
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
            scrollable_row.append(col)

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
        scrollable_rows.append(scrollable_row)

    # footer
    row = TR(**{"class": "summary"})
    estimate = round(df.estimate.sum(), HOURS_NDIGITS)
    spent = round(df.spent.sum(), HOURS_NDIGITS)
    avg_overtime = calculate_avg_overtime(overtimes)

    row.append(TD(""))
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

    rows.append(row)
    # add summary component columns filled in with values
    scrollable_summary_row = TR(
        generate_component_columns(
            df,
            components,
            component_overtimes_map,
            display_overtime=False,
            summary=True,
        ),
        **{"class": "summary"},
    )
    scrollable_rows.append(scrollable_summary_row)

    # footer selected row
    row = TR(**{"class": "selected"})

    row.append(TD(""))
    row.append(TD("Selected", colspan=3))
    row.append(TD("", **{DATA_COLUMN_NAME: TASKS}))
    row.append(TD("", **{DATA_COLUMN_NAME: ESTIMATED}))
    row.append(TD("", **{DATA_COLUMN_NAME: SPENT}))
    row.append(TD("", **{DATA_COLUMN_NAME: OVERTIME}))
    row.append(TD("", **{DATA_COLUMN_NAME: PROJECTION}))

    rows.append(row)

    # footer selected scrollable row
    scrollable_selected_row = TR(**{"class": "selected"})

    for component in components:
        data_attr = f"{DATA_COLUMN_NAME}-{component.id}"

        scrollable_selected_row.append(TD("&nbsp;", **{data_attr: TASKS}))
        scrollable_selected_row.append(TD("&nbsp;", **{data_attr: ESTIMATED}))
        scrollable_selected_row.append(TD("&nbsp;", **{data_attr: SPENT}))
        scrollable_selected_row.append(TD("&nbsp;", **{data_attr: OVERTIME}))
        scrollable_selected_row.append(TD("&nbsp;", **{data_attr: PROJECTION}))

    scrollable_rows.append(scrollable_selected_row)

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
