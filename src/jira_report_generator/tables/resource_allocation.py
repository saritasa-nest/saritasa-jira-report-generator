import collections.abc
import datetime
import typing
import pandas as pd
from ..constants import HOURS_N_DECIMAL_PLACES
from ..utils.colors import get_danger_color_class
from ..utils.tags import TD, TH, TR, NumTD, Table, Div


class AllocationPeriod(typing.Protocol):
    start_date: datetime.date
    end_date: datetime.date


class ResourceAllocation(typing.Protocol):
    user_id: int
    user_name: str
    period: AllocationPeriod
    assigned_hours: float
    spent_hours: float
    spent_billable_hours: float


def generate_resource_allocation_table(
    resources_allocation: collections.abc.Collection[ResourceAllocation],
    jira_account_id_by_user_id: dict[str, str],
    assignees_df: pd.DataFrame,
    **table_options,
):
    allocation_by_user_info: dict[
        tuple[str, str],
        dict[tuple[datetime.date, datetime.date], ResourceAllocation]
    ] = collections.defaultdict(dict)
    allocation_period_summaries: dict[tuple[datetime.date, datetime.date], dict[str, float]] = {}
    for resource in resources_allocation:
        period = (resource.period.start_date, resource.period.end_date)
        allocation_by_user_info[
            (str(resource.user_id), resource.user_name)
        ][period] = resource
        allocation_period_summaries[period] = {
            "total_allocated_hours": 0.0,
            "total_assigned_hours": 0.0,
            "total_spent_hours": 0.0,
            "total_spent_billable_hours": 0.0,
        }

    sorted_periods = sorted(
        allocation_period_summaries.keys(),
        key=lambda period: period[0],
    )

    rows = []
    scrollable_rows = []

    # table header
    header = TR(**{"class": "h50"})
    header.append(TH("Name"))
    header.append(TH("Tasks"))
    header.append(TH("Estimated"))

    rows.append(header)

    # scrollable header
    scrollable_header = TR(**{"class": "h25"})
    scrollable_subheader = TR(**{"class": "h25"})
    subheader_attrs = {"class": "subheader hours"}
    for period_ix, (period_start_date, period_end_date) in enumerate(sorted_periods):
        scrollable_header.append(
            TH(
                f"{period_start_date.strftime('%m/%d')} - {period_end_date.strftime('%m/%d')}",
                **{"colspan": 4},
            ),
        )
        scrollable_subheader.append(
            TH(
                "Allocated",
                **subheader_attrs
                if is_first_period(period_ix)
                else {**subheader_attrs, "colspan": 2}
            ),
        )
        scrollable_subheader.append(
            TH(
                "Assigned",
                **subheader_attrs
                if is_first_period(period_ix)
                else {**subheader_attrs, "colspan": 2}
            ),
        )
        if is_first_period(period_ix):
            scrollable_subheader.append(
                TH("Spent", **subheader_attrs),
            )
            scrollable_subheader.append(
                TH("Billable", **subheader_attrs),
            )

    scrollable_rows.append(scrollable_header)
    scrollable_rows.append(scrollable_subheader)

    total_tasks_count = 0
    total_estimated_hours = 0.0
    for (user_id, user_name), allocation_by_week in allocation_by_user_info.items():
        row = TR()
        row.append(TD(user_name))
        jira_account_id = jira_account_id_by_user_id.get(user_id)
        tasks_count = 0
        estimated_hours = 0.0
        if jira_account_id:
            user_issues = assignees_df[assignees_df["assignee"].apply(
                lambda x: x.accountId == jira_account_id,
            )]
            tasks_count = len(user_issues)
            estimated_hours = round(user_issues.estimate.sum(), HOURS_N_DECIMAL_PLACES)
        total_tasks_count += tasks_count
        total_estimated_hours += estimated_hours

        row.append(NumTD(tasks_count))
        row.append(NumTD(estimated_hours))
        rows.append(row)
        scrollable_row = TR()
        for period_idx, allocation_period in enumerate(sorted_periods):
            resource_allocation = allocation_by_week.get(
                allocation_period,
            )
            assigned_hours = spent_hours = spent_billable_hours = 0.0
            if resource_allocation:
                assigned_hours = round(
                    resource_allocation.assigned_hours,
                    HOURS_N_DECIMAL_PLACES,
                )
                spent_hours = round(
                    resource_allocation.spent_hours,
                    HOURS_N_DECIMAL_PLACES,
                )
                spent_billable_hours = round(
                    resource_allocation.spent_billable_hours,
                    HOURS_N_DECIMAL_PLACES,
                )

            summary = allocation_period_summaries[allocation_period]
            summary["total_assigned_hours"] += assigned_hours
            summary["total_spent_hours"] += spent_hours
            summary["total_spent_billable_hours"] += spent_billable_hours

            period_hours_attrs = {"colspan": 2} if not is_first_period(period_idx) else {}
            scrollable_row.append(TD("", **period_hours_attrs))
            scrollable_row.append(NumTD(assigned_hours, **period_hours_attrs))
            if is_first_period(period_idx):
                scrollable_row.append(
                    NumTD(
                        spent_hours,
                        **{
                            "class": get_danger_color_class(
                                spent_hours > assigned_hours
                            ),
                        },
                    ),
                )
                scrollable_row.append(
                    NumTD(
                        spent_billable_hours,
                        **{
                            "class": get_danger_color_class(
                                spent_billable_hours > assigned_hours),
                        },
                    ),
                )
        scrollable_rows.append(scrollable_row)

    summary_row = TR(**{"class": "summary"})
    summary_row.append(TD("Summary"))
    summary_row.append(NumTD(total_tasks_count))
    summary_row.append(NumTD(round(total_estimated_hours, HOURS_N_DECIMAL_PLACES)))
    rows.append(summary_row)
    scrollable_summary_row = TR(**{"class": "summary"})
    for period_idx, allocation_period in enumerate(sorted_periods):
        summary = allocation_period_summaries[allocation_period]
        period_hours_attrs = {"colspan": 2} if not is_first_period(period_idx) else {}
        total_assigned_hours = round(
            summary["total_assigned_hours"],
            HOURS_N_DECIMAL_PLACES,
        )
        total_spent_hours = round(
            summary["total_spent_hours"],
            HOURS_N_DECIMAL_PLACES,
        )
        total_spent_billable_hours = round(
            summary["total_spent_billable_hours"],
            HOURS_N_DECIMAL_PLACES,
        )
        scrollable_summary_row.append(TD("", **period_hours_attrs))
        scrollable_summary_row.append(
            NumTD(
                total_assigned_hours,
                **period_hours_attrs,
            )
        )
        if is_first_period(period_idx):
            scrollable_summary_row.append(
                NumTD(
                    total_spent_hours,
                    **{
                        "class": get_danger_color_class(
                            total_spent_hours > total_assigned_hours
                        ),
                    },
                ),
            )
            scrollable_summary_row.append(
                NumTD(
                    total_spent_billable_hours,
                    **{
                        "class": get_danger_color_class(
                            total_spent_billable_hours > total_assigned_hours
                        ),
                    },
                ),
            )
    scrollable_rows.append(scrollable_summary_row)

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


def is_first_period(period_idx: int) -> bool:
    return period_idx == 0
