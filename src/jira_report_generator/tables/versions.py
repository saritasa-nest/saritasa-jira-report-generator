from collections import defaultdict
from typing import List

from jira.resources import Component
from pandas import DataFrame

from ..constants import HOURS_N_DECIMAL_PLACES
from ..utils.data import is_task_version
from ..utils.formatters import get_full_date, get_short_date
from ..utils.tags import TD, TH, TR, A, Div, Input, NumTD, Table

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
    return (estimate or 1) * overtime


def generate_component_columns(
        df: DataFrame,
        components: list,
        component_overtimes_map: dict = None,
        display_overtime: bool = False,
        summary: bool = False,
) -> List[TD]:
    columns = []
    gc = "group-component"

    for component in components:
        component_tasks = df[df["components"].apply(
            lambda x: component in x,
        )]
        avg_component_overtime = None

        # generate empty columns
        if component_tasks.empty:
            columns.append(TD("&nbsp;", **{"class": gc}))
            columns.append(TD("&nbsp;", **{"class": gc}))
            columns.append(TD("&nbsp;", **{"class": gc}))
            columns.append(TD("&nbsp;", **{"class": gc}))
            columns.append(TD("&nbsp;", **{"class": gc}))
            continue

        component_estimate = round(
            component_tasks.estimate.sum(),
            HOURS_N_DECIMAL_PLACES,
        )
        component_spent = round(
            component_tasks.spent.sum(),
            HOURS_N_DECIMAL_PLACES,
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

        columns.append(NumTD(component_tasks.id.count(), **{"class": gc}))
        columns.append(NumTD(component_estimate, **{"class": gc}))
        columns.append(NumTD(component_spent, **{
            "class": (
                f"danger {gc}"
                if component_estimate != 0
                    and component_spent > component_estimate
                else gc
            ),
        }))
        columns.append(NumTD(
            round(component_overtime, OVERTIME_NDIGITS)
            if component_overtime and (display_overtime or summary)
            else "",
            **{"class": gc},
        ))
        columns.append(NumTD(
            round(predict_estimate(
                component_estimate,
                avg_component_overtime,
            ), HOURS_N_DECIMAL_PLACES)
            if avg_component_overtime
            else "",
            title=f"{component_estimate}*{avg_component_overtime}",
            **{"class": gc},
        ))

    return columns


def generate_label_columns(
        df: DataFrame,
        labels: list,
        label_overtimes_map: dict = None,
        display_overtime: bool = False,
        summary: bool = False,
) -> List[TD]:
    columns = []
    gl = "group-label"

    for label in labels:
        label_tasks = df[df["labels"].apply(
            lambda x: label in x,
        )]
        avg_label_overtime = None

        # generate empty columns
        if label_tasks.empty:
            columns.append(TD("&nbsp;", **{"class": gl}))
            columns.append(TD("&nbsp;", **{"class": gl}))
            columns.append(TD("&nbsp;", **{"class": gl}))
            columns.append(TD("&nbsp;", **{"class": gl}))
            columns.append(TD("&nbsp;", **{"class": gl}))
            continue

        label_estimate = round(
            label_tasks.estimate.sum(),
            HOURS_N_DECIMAL_PLACES,
        )
        label_spent = round(
            label_tasks.spent.sum(),
            HOURS_N_DECIMAL_PLACES,
        )
        label_overtime = None

        # calculate overtime only for non-summary rows
        if label_spent and label_estimate and not summary:
            label_overtime = label_spent / label_estimate

        # calculate label avg overtime
        if label_overtimes_map:
            avg_label_overtime = calculate_avg_overtime(
                label_overtimes_map[label],
            )

        if summary and avg_label_overtime:
            label_overtime = avg_label_overtime

        columns.append(NumTD(label_tasks.id.count(), **{"class": gl}))
        columns.append(NumTD(label_estimate, **{"class": gl}))
        columns.append(NumTD(label_spent, **{
            "class": (
                f"danger {gl}"
                if label_estimate != 0
                    and label_spent > label_estimate
                else gl
            ),
        }))
        columns.append(NumTD(
            round(label_overtime, OVERTIME_NDIGITS)
            if label_overtime and (display_overtime or summary)
            else "",
            **{"class": gl},
        ))
        columns.append(NumTD(
            round(predict_estimate(
                label_estimate,
                avg_label_overtime,
            ), HOURS_N_DECIMAL_PLACES)
            if avg_label_overtime
            else "",
            title=f"{label_estimate}*{avg_label_overtime}",
            **{"class": gl},
        ))

    return columns


def generate_versions_table(
    df: DataFrame,
    versions: list,
    version_index_map: dict[int, list[int]] | None = None,
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
    labels = sorted(
        set(df.labels.explode().dropna().unique().tolist()),
    )
    overtimes = []
    component_overtimes_map = defaultdict(list)
    label_overtimes_map = defaultdict(list)

    # table header
    header = TR(**{"class": "h50"})
    header.append(TH(""))
    header.append(TH("Version"))
    header.append(TH("Start"))
    header.append(TH("Release"))
    header.append(TH("Tasks"))
    header.append(TH("Estimated", **{"class": "numeric"}))
    header.append(TH("Spent"))
    header.append(TH("Overtime", **{"class": "numeric"}))
    header.append(TH("Projection", **{"class": "numeric"}))

    rows.append(header)

    # scrollable header
    scrollable_header = TR(**{"class": "h25"})
    for component in components:
        scrollable_header.append(TH(component.name, **{"colspan": 5, "class": "group-component"}))
    for label in labels:
        scrollable_header.append(TH(f"🏷 {label}", **{"colspan": 5, "class": "group-label"}))

    scrollable_rows.append(scrollable_header)

    # scrollable subheader
    scrollable_subheader = TR(**{"class": "h25"})
    component_subheader_kwargs = {"class": "subheader numeric group-component"}
    for _ in components:
        scrollable_subheader.append(TH("Tasks", **component_subheader_kwargs))
        scrollable_subheader.append(TH("Estimated", **component_subheader_kwargs))
        scrollable_subheader.append(TH("Spent", **component_subheader_kwargs))
        scrollable_subheader.append(TH("Overtime", **component_subheader_kwargs))
        scrollable_subheader.append(TH("Projection", **component_subheader_kwargs))
    label_subheader_kwargs = {"class": "subheader numeric group-label"}
    for _ in labels:
        scrollable_subheader.append(TH("Tasks", **label_subheader_kwargs))
        scrollable_subheader.append(TH("Estimated", **label_subheader_kwargs))
        scrollable_subheader.append(TH("Spent", **label_subheader_kwargs))
        scrollable_subheader.append(TH("Overtime", **label_subheader_kwargs))
        scrollable_subheader.append(TH("Projection", **label_subheader_kwargs))

    scrollable_header.append(scrollable_subheader)

    # body
    index_set = set(df.index) if version_index_map is not None else None
    for version in versions:
        row = TR(**{DATA_ROW_VERSION_ID: version.id})
        scrollable_row = TR()
        if version_index_map is not None:
            indices = [
                index
                for index in version_index_map.get(str(version.id), [])
                if index in index_set
            ]
            version_tasks = (
                df.loc[indices]
                if indices
                else df.iloc[0:0]
            )
        else:
            version_tasks = df[df["versions"].apply(
                lambda task_versions, current_version=version: is_task_version(
                    version=current_version,
                    task_versions=task_versions,
                )
            )]
        estimate = round(version_tasks.estimate.sum(), HOURS_N_DECIMAL_PLACES)
        spent = round(version_tasks.spent.sum(), HOURS_N_DECIMAL_PLACES)
        overtime = None
        avg_overtime = None
        start_date = getattr(version, "startDate", "")
        release_date = getattr(version, "releaseDate", "")
        short_start_date = get_short_date(start_date)
        short_release_date = get_short_date(release_date)
        full_start_date = get_full_date(start_date)
        full_release_date = get_full_date(release_date)

        if spent and estimate:
            overtime = spent / estimate

        if overtimes:
            avg_overtime = calculate_avg_overtime(overtimes)

        row.append(TD(
            Input(**{
                "type": "checkbox",
                "data-version-id": version.id,
            }),
            **{"class": "center p05"},
        ))

        row.append(TD(
            A(version.name, **{
                "href": getattr(version, "permalink", ""),
                "title": version.name,
                "class": "released" if version.released else "",
            }),
            **{
                "class": "name",
            },
        ))
        row.append(TD(short_start_date, **{
            "class": "date",
            "title": full_start_date,
        }))
        row.append(TD(short_release_date, **{
            "class": "date",
            "title": full_release_date,
        }))
        row.append(NumTD(version_tasks.id.count(), **{
            DATA_ROW_VERSION_COLUMN_NAME: TASKS,
        }))
        row.append(NumTD(estimate, **{
            DATA_ROW_VERSION_COLUMN_NAME: ESTIMATED,
        }))
        row.append(NumTD(spent, **{
            "class": (
                "danger"
                if estimate != 0 and spent > estimate
                else ""
            ),
            DATA_ROW_VERSION_COLUMN_NAME: SPENT,
        }))

        # overtime
        row.append(NumTD(
            round(overtime, OVERTIME_NDIGITS)
            if overtime is not None and version.released
            else "",
            **{DATA_ROW_VERSION_COLUMN_NAME: OVERTIME},
        ))

        # estimate prediction
        row.append(NumTD(
            round(predict_estimate(
                estimate,
                avg_overtime,
            ), HOURS_N_DECIMAL_PLACES)
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

        # add label columns filled in with values
        for col in generate_label_columns(
                version_tasks,
                labels,
                label_overtimes_map,
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
                        lambda x: component in x,
                    )
                ]
                component_estimate = component_tasks.estimate.sum()
                component_spent = component_tasks.spent.sum()

                if not component_estimate and not component_spent:
                    continue

                component_overtimes_map[component.id].append(
                    (component_spent or 1) / (component_estimate or 1),
                )

            # generate and store label overtimes map
            for label in labels:
                label_tasks = version_tasks[
                    version_tasks["labels"].apply(
                        lambda x: label in x,
                    )
                ]
                label_estimate = label_tasks.estimate.sum()
                label_spent = label_tasks.spent.sum()

                if not label_estimate and not label_spent:
                    continue

                label_overtimes_map[label].append(
                    (label_spent or 1) / (label_estimate or 1),
                )

        rows.append(row)
        scrollable_rows.append(scrollable_row)

    # footer
    row = TR(**{"class": "summary"})
    estimate = round(df.estimate.sum(), HOURS_N_DECIMAL_PLACES)
    spent = round(df.spent.sum(), HOURS_N_DECIMAL_PLACES)
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
        ), HOURS_N_DECIMAL_PLACES) or "",
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
        ) + generate_label_columns(
            df,
            labels,
            label_overtimes_map,
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

        scrollable_selected_row.append(TD("&nbsp;", **{"class": "group-component", data_attr: TASKS}))
        scrollable_selected_row.append(TD("&nbsp;", **{"class": "group-component", data_attr: ESTIMATED}))
        scrollable_selected_row.append(TD("&nbsp;", **{"class": "group-component", data_attr: SPENT}))
        scrollable_selected_row.append(TD("&nbsp;", **{"class": "group-component", data_attr: OVERTIME}))
        scrollable_selected_row.append(TD("&nbsp;", **{"class": "group-component", data_attr: PROJECTION}))

    for label in labels:
        data_attr = f"{DATA_COLUMN_NAME}-label-{label}"

        scrollable_selected_row.append(TD("&nbsp;", **{"class": "group-label", data_attr: TASKS}))
        scrollable_selected_row.append(TD("&nbsp;", **{"class": "group-label", data_attr: ESTIMATED}))
        scrollable_selected_row.append(TD("&nbsp;", **{"class": "group-label", data_attr: SPENT}))
        scrollable_selected_row.append(TD("&nbsp;", **{"class": "group-label", data_attr: OVERTIME}))
        scrollable_selected_row.append(TD("&nbsp;", **{"class": "group-label", data_attr: PROJECTION}))

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
