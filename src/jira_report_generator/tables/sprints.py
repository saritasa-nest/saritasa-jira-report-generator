from collections import defaultdict
from typing import List

from jira.resources import Component
from pandas import DataFrame

from ..constants import Status, HOURS_N_DECIMAL_PLACES, GroupBy
from ..utils.formatters import get_short_date
from ..utils.tags import TD, TH, TR, Abbr, Div, Input, NumTD, Table

CPI_NDIGITS = 2

TASKS = "tasks"
ESTIMATED = "estimated"
SPENT = "spent"
CPI = "cpi"
PROJECTION = "projection"
LIMIT = "limit"
BUDGET = "budget"

DATA_ROW_SPRINT_ID = "data-row-sprint-id"
DATA_ROW_SPRINT_COLUMN_NAME = "data-row-sprint-column-name"
DATA_COLUMN_NAME = "data-column-name"

CLOSED = "closed"
ACTIVE = "active"


def calculate_avg_cpi(cpis: List[float]) -> float:

    try:
        result = sum(cpis) / len(cpis)
    except ZeroDivisionError:
        result = 0.0

    return result


def filter_completed(df: DataFrame) -> DataFrame:
    """Returns completed tasks."""

    if df.empty:
        return df

    statuses = (
        *Status.VERIFIED.value,
        *Status.COMPLETED.value,
        *Status.TM_PM_VERIFY.value,
    )

    return df[df["status"].apply(
        lambda x: x.name in statuses
    )]


def filter_affected(df: DataFrame) -> DataFrame:
    """Returns affected tasks -- with logged time."""

    if df.empty:
        return df

    return df[df["spent"] > 0]


def predict_estimate(estimate: float, cpi: float) -> float:
    return estimate * cpi


def generate_component_columns(
        df: DataFrame,
        components: list,
        components_cpi_map: dict = None,
        display_cpi: bool = False,
        summary: bool = False,
        is_active_sprint: bool = False,
) -> List[TD]:
    columns = []
    gc = "group-component"

    for component in components:
        component_tasks = df[df["components"].apply(
            lambda x: component in x,
        )]

        # generate empty columns
        if component_tasks.empty:
            columns.append(TD("&nbsp;", **{"class": gc}))
            columns.append(TD("&nbsp;", **{"class": gc}))
            columns.append(TD("&nbsp;", **{"class": gc}))
            columns.append(TD("&nbsp;", **{"class": gc}))
            continue

        completed_component_tasks = filter_completed(component_tasks)
        affected_component_tasks = filter_affected(component_tasks)
        component_estimate = round(
            component_tasks.estimate.sum(),
            HOURS_N_DECIMAL_PLACES,
        )
        component_spent = round(
            component_tasks.spent.sum(),
            HOURS_N_DECIMAL_PLACES,
        )
        component_cpi = None

        columns.append(NumTD(component_tasks.id.count(), **{
            "class": gc,
            "title": f"{completed_component_tasks.id.count()} completed",
        }))
        columns.append(NumTD(component_estimate, **{"class": gc}))
        columns.append(NumTD(component_spent, **{
            "class": (
                f"danger {gc}"
                if component_estimate != 0
                    and component_spent > component_estimate
                else gc
            ),
        }))

        # re-calculate cpi if sprint is active
        if is_active_sprint:
            component_estimate = round(
                affected_component_tasks.estimate.sum(),
                HOURS_N_DECIMAL_PLACES,
            )
            component_spent = round(
                affected_component_tasks.spent.sum(),
                HOURS_N_DECIMAL_PLACES,
            )

        # calculate cpi only for non-summary rows
        if component_spent and component_estimate and not summary:
            component_cpi = component_estimate / component_spent

        columns.append(NumTD(
            round(component_cpi, CPI_NDIGITS)
            if component_cpi and (display_cpi or summary) else "",
            **{"class": gc, "title": f"{component_estimate}/{component_spent}"},
        ))

    return columns


def generate_label_columns(
        df: DataFrame,
        labels: list,
        labels_cpi_map: dict = None,
        display_cpi: bool = False,
        summary: bool = False,
        is_active_sprint: bool = False,
) -> List[TD]:
    columns = []
    gl = "group-label"

    for label in labels:
        label_tasks = df[df["labels"].apply(
            lambda x: label in x,
        )]

        # generate empty columns
        if label_tasks.empty:
            columns.append(TD("&nbsp;", **{"class": gl}))
            columns.append(TD("&nbsp;", **{"class": gl}))
            columns.append(TD("&nbsp;", **{"class": gl}))
            columns.append(TD("&nbsp;", **{"class": gl}))
            continue

        completed_label_tasks = filter_completed(label_tasks)
        affected_label_tasks = filter_affected(label_tasks)
        label_estimate = round(
            label_tasks.estimate.sum(),
            HOURS_N_DECIMAL_PLACES,
        )
        label_spent = round(
            label_tasks.spent.sum(),
            HOURS_N_DECIMAL_PLACES,
        )
        label_cpi = None

        columns.append(NumTD(label_tasks.id.count(), **{
            "class": gl,
            "title": f"{completed_label_tasks.id.count()} completed",
        }))
        columns.append(NumTD(label_estimate, **{"class": gl}))
        columns.append(NumTD(label_spent, **{
            "class": (
                f"danger {gl}"
                if label_estimate != 0
                    and label_spent > label_estimate
                else gl
            ),
        }))

        # re-calculate cpi if sprint is active
        if is_active_sprint:
            label_estimate = round(
                affected_label_tasks.estimate.sum(),
                HOURS_N_DECIMAL_PLACES,
            )
            label_spent = round(
                affected_label_tasks.spent.sum(),
                HOURS_N_DECIMAL_PLACES,
            )

        # calculate cpi only for non-summary rows
        if label_spent and label_estimate and not summary:
            label_cpi = label_estimate / label_spent

        columns.append(NumTD(
            round(label_cpi, CPI_NDIGITS)
            if label_cpi and (display_cpi or summary) else "",
            **{"class": gl, "title": f"{label_estimate}/{label_spent}"},
        ))

    return columns


def generate_sprints_table(
    df: DataFrame,
    sprints: list,
    show_sprint_limit_column: bool = False,
    show_project_budget_column: bool = False,
    group_by: GroupBy = GroupBy.COMPONENT,
    **table_options: str,
):
    rows = []
    scrollable_rows = []
    if group_by == GroupBy.COMPONENT:
        components = sorted(
            filter(
                lambda x: isinstance(x, Component),
                df.components.explode().unique().tolist(),
            ),
            key=lambda x: getattr(x, "name", ""),
        )
        labels = []
    else:
        components = []
        labels = sorted(
            set(df.labels.explode().dropna().unique().tolist()),
        )
    cpis = []
    components_cpi_map = defaultdict(list)
    labels_cpi_map = defaultdict(list)

    # table header
    header = TR(**{"class": "h50"})
    header.append(TH(""))
    header.append(TH("Sprint"))
    header.append(TH("Start"))
    header.append(TH("Release"))
    header.append(TH("Tasks"))

    if show_project_budget_column:
        header.append(TH(
            Abbr("BAC", **{"title": "Budget At Completion"}),
            **{"class": "budget"}
        ))

    if show_sprint_limit_column:
        header.append(TH(
            Abbr("PV", **{"title": "Planned Value"}),
            **{"class": "limit"},
        ))

    header.append(TH(
        Abbr("EV", **{"title": "Estimated Value"}),
        **{"class": "numeric"},
    ))
    header.append(TH(
        Abbr("AC", **{"title": "Actual Cost"}),
    ))
    header.append(TH(
        Abbr("CPI", **{"title": "Cost Performance Index"}),
    ))

    rows.append(header)

    # scrollable header
    scrollable_header = TR(**{"class": "h25"})
    for component in components:
        scrollable_header.append(TH(component.name, **{"colspan": 4, "class": "group-component"}))
    for label in labels:
        scrollable_header.append(TH(f"🏷 {label}", **{"colspan": 4, "class": "group-label"}))

    scrollable_rows.append(scrollable_header)

    # scrollable subheader
    scrollable_subheader = TR(**{"class": "h25"})
    component_kwargs = {"class": "subheader hours group-component"}
    for _ in components:
        scrollable_subheader.append(TH("Tasks", **component_kwargs))
        scrollable_subheader.append(TH(
            Abbr("EV", **{"title": "Estimated Value"}),
            **component_kwargs,
        ))
        scrollable_subheader.append(TH(
            Abbr("AC", **{"title": "Actual Cost"}),
            **component_kwargs,
        ))
        scrollable_subheader.append(TH(
            Abbr("CPI", **{"title": "Cost Performance Index"}),
            **component_kwargs,
        ))
    label_kwargs = {"class": "subheader hours group-label"}
    for _ in labels:
        scrollable_subheader.append(TH("Tasks", **label_kwargs))
        scrollable_subheader.append(TH(
            Abbr("EV", **{"title": "Estimated Value"}),
            **label_kwargs,
        ))
        scrollable_subheader.append(TH(
            Abbr("AC", **{"title": "Actual Cost"}),
            **label_kwargs,
        ))
        scrollable_subheader.append(TH(
            Abbr("CPI", **{"title": "Cost Performance Index"}),
            **label_kwargs,
        ))

    scrollable_header.append(scrollable_subheader)

    # body
    for sprint in sprints:
        row = TR(**{DATA_ROW_SPRINT_ID: sprint.id})
        scrollable_row = TR()
        sprint_tasks = df[df["sprint_id"] == sprint.id]
        completed_sprint_tasks = filter_completed(sprint_tasks)
        affected_sprint_tasks = filter_affected(sprint_tasks)
        estimate = round(sprint_tasks.estimate.sum(), HOURS_N_DECIMAL_PLACES)
        spent = round(sprint_tasks.spent.sum(), HOURS_N_DECIMAL_PLACES)
        sprint_cpi = None
        avg_cpi = None
        start_date = getattr(sprint, "startDate", "")
        end_date = getattr(sprint, "endDate", "")
        short_start_date = get_short_date(start_date, "%Y-%m-%dT%H:%M:%S.%fZ")
        short_end_date = get_short_date(end_date, "%Y-%m-%dT%H:%M:%S.%fZ")

        if spent and estimate:
            sprint_cpi = estimate / spent

        if cpis:
            avg_cpi = calculate_avg_cpi(cpis)

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

        row.append(TD(short_start_date, **{
            "class": "date",
            "title": start_date,
        }))
        row.append(TD(short_end_date, **{
            "class": "date",
            "title": end_date,
        }))
        row.append(NumTD(sprint_tasks.id.count(), **{
            DATA_ROW_SPRINT_COLUMN_NAME: TASKS,
            "title": f"{completed_sprint_tasks.id.count()} completed",
        }))

        if show_project_budget_column:
            row.append(NumTD("", **{
                DATA_ROW_SPRINT_COLUMN_NAME: BUDGET,
            }))

        if show_sprint_limit_column:
            row.append(NumTD("", **{
                DATA_ROW_SPRINT_COLUMN_NAME: LIMIT,
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

        # CPI
        if sprint.state == ACTIVE:
            estimate = round(
                affected_sprint_tasks.estimate.sum(),
                HOURS_N_DECIMAL_PLACES,
            )
            spent = round(
                affected_sprint_tasks.spent.sum(),
                HOURS_N_DECIMAL_PLACES,
            )
            if spent and estimate:
                sprint_cpi = estimate / spent

        row.append(NumTD(
            round(sprint_cpi, CPI_NDIGITS)
            if sprint_cpi is not None else "",
            **{
                DATA_ROW_SPRINT_COLUMN_NAME: CPI,
                "title": f"{estimate}/{spent}",
            },
        ))

        # add component columns filled in with values
        for col in generate_component_columns(
                sprint_tasks,
                components,
                components_cpi_map,
                display_cpi=True,
                summary=False,
                is_active_sprint=(sprint.state == ACTIVE),
        ):
            scrollable_row.append(col)

        # add label columns filled in with values
        for col in generate_label_columns(
                sprint_tasks,
                labels,
                labels_cpi_map,
                display_cpi=True,
                summary=False,
                is_active_sprint=(sprint.state == ACTIVE),
        ):
            scrollable_row.append(col)

        rows.append(row)
        scrollable_rows.append(scrollable_row)

        # component CPI
        if not sprint_cpi:
            continue

        cpis.append(sprint_cpi)

    # footer
    row = TR(**{"class": "summary"})
    estimate = round(df.estimate.sum(), HOURS_N_DECIMAL_PLACES)
    spent = round(df.spent.sum(), HOURS_N_DECIMAL_PLACES)
    avg_cpi = calculate_avg_cpi(cpis)

    row.append(TD(""))
    row.append(TD("Summary", colspan=3))
    row.append(NumTD(df.id.count()))

    if show_project_budget_column:
        row.append(NumTD(""))

    if show_sprint_limit_column:
        row.append(NumTD(""))

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
        round(avg_cpi, CPI_NDIGITS) or "",
    ))

    rows.append(row)
    # add summary component columns filled in with values
    scrollable_summary_row = TR(
        generate_component_columns(
            df,
            components,
            components_cpi_map,
            display_cpi=False,
            summary=True,
        ) + generate_label_columns(
            df,
            labels,
            labels_cpi_map,
            display_cpi=False,
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

    if show_project_budget_column:
        row.append(NumTD("", **{DATA_COLUMN_NAME: BUDGET}))

    if show_sprint_limit_column:
        row.append(NumTD("", **{DATA_COLUMN_NAME: LIMIT}))

    row.append(NumTD("", **{DATA_COLUMN_NAME: ESTIMATED}))
    row.append(NumTD("", **{DATA_COLUMN_NAME: SPENT}))
    row.append(NumTD("", **{DATA_COLUMN_NAME: CPI}))

    rows.append(row)

    # footer selected scrollable row
    scrollable_selected_row = TR(**{"class": "selected"})

    for component in components:
        data_attr = f"{DATA_COLUMN_NAME}-{component.id}"

        scrollable_selected_row.append(TD("&nbsp;", **{"class": "group-component", data_attr: TASKS}))
        scrollable_selected_row.append(TD("&nbsp;", **{"class": "group-component", data_attr: ESTIMATED}))
        scrollable_selected_row.append(TD("&nbsp;", **{"class": "group-component", data_attr: SPENT}))
        scrollable_selected_row.append(TD("&nbsp;", **{"class": "group-component", data_attr: CPI}))

    for label in labels:
        data_attr = f"{DATA_COLUMN_NAME}-label-{label}"

        scrollable_selected_row.append(TD("&nbsp;", **{"class": "group-label", data_attr: TASKS}))
        scrollable_selected_row.append(TD("&nbsp;", **{"class": "group-label", data_attr: ESTIMATED}))
        scrollable_selected_row.append(TD("&nbsp;", **{"class": "group-label", data_attr: SPENT}))
        scrollable_selected_row.append(TD("&nbsp;", **{"class": "group-label", data_attr: CPI}))

    scrollable_rows.append(scrollable_selected_row)

    if not components and not labels:
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
