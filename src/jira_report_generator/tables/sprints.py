from collections import defaultdict
from typing import List

from jira.resources import Component
from pandas import DataFrame

from ..utils.tags import TD, TH, TR, Div, Input, NumTD, Table

HOURS_NDIGITS = 1
OVERTIME_NDIGITS = 2

TASKS = "tasks"
ESTIMATED = "estimated"
SPENT = "spent"
OVERTIME = "overtime"
PROJECTION = "projection"

DATA_ROW_SPRINT_ID = "data-row-sprint-id"
DATA_ROW_SPRINT_COLUMN_NAME = "data-row-sprint-column-name"
DATA_COLUMN_NAME = "data-column-name"

CLOSED = "closed"


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
            lambda x: component in x,
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
                component_overtimes_map[component.id],
            )

        if summary and avg_component_overtime:
            component_overtime = avg_component_overtime

        columns.append(NumTD(component_tasks.id.count()))
        columns.append(NumTD(component_estimate))
        columns.append(NumTD(component_spent, **{
            "class": (
                "danger"
                if component_estimate != 0
                    and component_spent > component_estimate
                else ""
            ),
        }))
        columns.append(NumTD(
            round(component_overtime, OVERTIME_NDIGITS)
            if component_overtime and (display_overtime or summary)
            else "",
        ))
        columns.append(NumTD(
            round(predict_estimate(
                component_estimate,
                avg_component_overtime,
            ), HOURS_NDIGITS)
            if avg_component_overtime
            else "",
            title=f"{component_estimate}*{avg_component_overtime}",
        ))

    return columns


def generate_sprints_table(
    df: DataFrame,
    sprints: list,
    **table_options: str,
):
    rows = []
    scrollable_rows = []
    components = sorted(
        filter(
            lambda x: isinstance(x, Component),
            df.components.explode().unique().tolist(),
        ),
        key=lambda x: getattr(x, "name", ""),
    )
    overtimes = []
    component_overtimes_map = defaultdict(list)

    # table header
    header = TR(**{"class": "h50"})
    header.append(TH(""))
    header.append(TH("Sprint"))
    header.append(TH("Start Date"))
    header.append(TH("Release Date"))
    header.append(TH("Tasks", **{"class": "subheader hours"}))
    header.append(TH("Estimated", **{"class": "subheader hours"}))
    header.append(TH("Spent", **{"class": "subheader hours"}))
    header.append(TH("Overtime", **{"class": "subheader hours"}))
    header.append(TH("Projection", **{"class": "subheader hours"}))

    rows.append(header)

    # scrollable header
    scrollable_header = TR(**{"class": "h25"})
    for component in components:
        scrollable_header.append(TH(component.name, **{"colspan": 5}))

    scrollable_rows.append(scrollable_header)

    # scrollable subheader
    scrollable_subheader = TR(**{"class": "h25"})
    kwargs = {"class": "subheader hours"}
    for _ in components:
        scrollable_subheader.append(TH("Tasks", **kwargs))
        scrollable_subheader.append(TH("Estimated", **kwargs))
        scrollable_subheader.append(TH("Spent", **kwargs))
        scrollable_subheader.append(TH("Overtime", **kwargs))
        scrollable_subheader.append(TH("Projection", **kwargs))

    scrollable_header.append(scrollable_subheader)

    # body
    for sprint in sprints:
        row = TR(**{DATA_ROW_SPRINT_ID: sprint.id})
        scrollable_row = TR()
        sprint_tasks = df[df["sprint_id"] == sprint.id]
        estimate = round(sprint_tasks.estimate.sum(), HOURS_NDIGITS)
        spent = round(sprint_tasks.spent.sum(), HOURS_NDIGITS)
        overtime = None
        avg_overtime = None

        if spent and estimate:
            overtime = spent / estimate

        if overtimes:
            avg_overtime = calculate_avg_overtime(overtimes)

        row.append(TD(
            Input(**{
                "type": "checkbox",
                "data-sprint-id": sprint.id,
            }),
            **{"class": "center p05"},
        ))

        row.append(TD(sprint.name, **{
            "class": f"name {'released' if sprint.state == CLOSED else ''}",
            "title": sprint.name,
        }))

        row.append(TD(getattr(sprint, "startDate", "")[:10], **{
            "class": "date",
        }))
        row.append(TD(getattr(sprint, "endDate", "")[:10], **{
            "class": "date",
        }))
        row.append(NumTD(sprint_tasks.id.count(), **{
            DATA_ROW_SPRINT_COLUMN_NAME: TASKS,
        }))
        row.append(NumTD(estimate, **{
            DATA_ROW_SPRINT_COLUMN_NAME: ESTIMATED,
        }))
        row.append(NumTD(spent, **{
            "class": (
                "danger"
                if estimate != 0 and spent > estimate
                else ""
            ),
            DATA_ROW_SPRINT_COLUMN_NAME: SPENT,
        }))

        # overtime
        row.append(NumTD(
            round(overtime, OVERTIME_NDIGITS)
            if overtime is not None and sprint.state == CLOSED
            else "",
            **{DATA_ROW_SPRINT_COLUMN_NAME: OVERTIME},
        ))

        # estimate prediction
        row.append(NumTD(
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
                sprint_tasks,
                components,
                component_overtimes_map,
                display_overtime=(sprint.state == CLOSED),
                summary=False,
        ):
            scrollable_row.append(col)

        # add overtime prediction
        if sprint.state == CLOSED and overtime:
            overtimes.append(overtime)

            # generate and store component overtimes map
            for component in components:
                component_tasks = sprint_tasks[
                    sprint_tasks["components"].apply(
                        lambda x: component in x,
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
    row.append(NumTD(df.id.count()))
    row.append(NumTD(estimate))
    row.append(NumTD(spent, **{
        "class": (
            "danger"
            if estimate != 0
                and spent > estimate
            else ""
        ),
    }))
    row.append(NumTD(
        round(avg_overtime, OVERTIME_NDIGITS) or "",
    ))
    row.append(NumTD(
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
    row.append(NumTD("", **{DATA_COLUMN_NAME: TASKS}))
    row.append(NumTD("", **{DATA_COLUMN_NAME: ESTIMATED}))
    row.append(NumTD("", **{DATA_COLUMN_NAME: SPENT}))
    row.append(NumTD("", **{DATA_COLUMN_NAME: OVERTIME}))
    row.append(NumTD("", **{DATA_COLUMN_NAME: PROJECTION}))

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
