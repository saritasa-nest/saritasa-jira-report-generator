import collections.abc
import typing

from ..constants import HOURS_N_DECIMAL_PLACES
from ..utils.colors import get_danger_color_class
from ..utils.tags import TD, TH, TR, NumTD, Table


class ResourceAllocation(typing.Protocol):
    user_id: int
    user_name: int
    assigned_hours: float
    spent_hours: float
    spent_billable_hours: float


def generate_resource_allocation_table(
    resources_allocation: collections.abc.Collection[ResourceAllocation],
    **table_options,
):
    rows = []

    # table header
    header = TR()
    header.append(TH("Name"))
    header.append(TH("Assigned"))
    header.append(TH("Spent"))
    header.append(TH("Billable"))
    header.append(TH("Left"))

    rows.append(header)

    total_assigned_hours = 0.0
    total_spent_hours = 0.0
    total_spent_billable_hours = 0.0
    total_remaining_hours = 0.0

    for resource_allocation in resources_allocation:
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
        remaining_hours = assigned_hours - spent_hours
        row = TR()
        row.append(TD(resource_allocation.user_name))
        row.append(NumTD(assigned_hours))
        row.append(
            NumTD(
                spent_hours,
                **{
                    "class": get_danger_color_class(
                        spent_hours > assigned_hours
                    ),
                },
            ),
        )
        row.append(
            NumTD(
                spent_billable_hours,
                **{
                    "class": get_danger_color_class(
                        spent_billable_hours > assigned_hours),
                },
            ),
        )
        row.append(NumTD(remaining_hours))
        rows.append(row)

        total_assigned_hours += resource_allocation.assigned_hours
        total_spent_hours += resource_allocation.spent_hours
        total_spent_billable_hours += resource_allocation.spent_billable_hours
        total_remaining_hours += remaining_hours

    row = TR(**{"class": "summary"})
    row.append(TD(""))
    row.append(NumTD(round(total_assigned_hours, HOURS_N_DECIMAL_PLACES)))
    row.append(
        NumTD(
            round(total_spent_hours, HOURS_N_DECIMAL_PLACES),
            **{
                "class": get_danger_color_class(
                    total_spent_hours > total_assigned_hours
                ),
            },
        ),
    )
    row.append(
        NumTD(
            round(
                total_spent_billable_hours,
                HOURS_N_DECIMAL_PLACES,
            ),
            **{
                "class": get_danger_color_class(
                    total_spent_billable_hours > total_assigned_hours
                ),
            },
        ),
    )
    row.append(NumTD(round(
        total_remaining_hours,
        HOURS_N_DECIMAL_PLACES,
    )))

    rows.append(row)

    return Table(rows, **table_options)
