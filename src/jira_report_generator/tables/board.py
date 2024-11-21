from pandas import DataFrame

from ..constants import Status
from ..utils.formatters import format_name
from ..utils.tags import TD, TH, TR, A, Div, NumTD, Table


def generate_board_table(
    df: DataFrame,
    sprints: list,
    component_id: str,
    **table_options: str,
):
    rows = []
    scrollable_rows = []

    # table header
    header = TR(**{"class": "h75"})
    header.append(TH("Summary", **{"class": "summary"}))
    header.append(TH("Type", **{"class": "type"}))
    header.append(TH("Jira ID", **{"class": "key"}))
    header.append(TH("Status", **{"class": "status"}))
    header.append(TH("Assignee", **{"class": "assignee"}))

    rows.append(header)

    # scrollable header
    scrollable_header = TR(**{"class": "h50"})
    for sprint in sprints:
        endDate = getattr(sprint, "endDate", "")[:10]

        scrollable_header.append(TH(
            f"<span class=\"name\">{sprint.name}</span>"
            "<span class=\"collapse\"></span>"
            f"<br/><small>{endDate}</small>",
            **{
                "class": "sprint",
                "colspan": 2,
                "data-sprint-id": str(sprint.id),
                "data-component-id": component_id,
            },
        ))

    scrollable_rows.append(scrollable_header)

    # scrollable subheader
    scrollable_subheader = TR(**{"class": "h25"})
    for sprint in sprints:
        sprint_tasks = df[df["sprint_id"] == sprint.id]
        estimate = round(sprint_tasks.estimate.sum(), 1)
        spent = round(sprint_tasks.spent.sum(), 1)

        scrollable_subheader.append(TH(estimate, **{
            "class": "hours subheader numeric",
            "data-sprint-id": str(sprint.id),
        }))
        scrollable_subheader.append(TH(spent, **{
            "class": (
                "hours subheader danger numeric"
                if estimate != 0 and spent > estimate
                else "hours subheader numeric"
            ),
            "data-sprint-id": str(sprint.id),
        }))

    scrollable_header.append(scrollable_subheader)

    # table body
    for _, item in df.iterrows():
        sprint_ids = []
        tr = TR(**{
            "data-status-id": item.status.id,
            "data-assignee-id": (
                item.assignee.accountId
                if item.assignee
                else ""
            ),
            "data-parent-id": (
                item.parent.id
                if item.parent
                else ""
            ),
        })
        scrollable_tr = TR(**{
            "data-status-id": item.status.id,
            "data-assignee-id": (
                item.assignee.accountId
                if item.assignee
                else ""
            ),
            "data-parent-id": (
                item.parent.id
                if item.parent
                else ""
            ),
        })
        status_attrs = {"class": "status nowrap"}
        background = "default"

        # summary
        tr.append(TD(item.summary, **{
            "class": "summary",
            "title": item.summary,
        }))

        # issue type
        tr.append(TD(item.type, **{"class": "type nowrap"}))

        # link to the issue
        tr.append(
            TD(
                A(item.key, **{
                    "href": item.link,
                    "title": item.key,
                }),
                **{"class": "link nowrap"},
            ),
        )

        if item.status.name in (
                *Status.VERIFIED.value,
                *Status.CLIENT_REVIEW.value,
                *Status.COMPLETED.value,
                *Status.TM_PM_VERIFY.value,
        ):
            status_attrs.update({"class": "status nowrap success"})
            background = "done"
        elif item.status.name in (
                *Status.IN_QA.value,
                *Status.CODE_REVIEW.value,
        ):
            status_attrs.update({"class": "status nowrap warning"})
            background = "in-progress"

        # status
        tr.append(TD(item.status.name, **status_attrs))

        # assignee
        display_name = format_name(getattr(item.assignee, "displayName", ""))
        tr.append(TD(
            display_name,
            **{
                "class": "assignee nowrap",
                "title": display_name,
            },
        ))

        for sprint in sprints:
            if (item.sprint_id == sprint.id):
                sprint_ids.append(str(sprint.id))

                attrs = {
                    "class": f"hours sprint {background}",
                    "data-sprint-id": str(sprint.id),
                }

                spent_attrs = dict(attrs)

                if (item.estimate != 0 and item.spent > item.estimate):
                    spent_attrs.update({
                        "class": f"hours sprint danger {background}",
                        "data-sprint-id": str(sprint.id),
                    })

                scrollable_tr.append(
                    NumTD(
                        round(item.estimate, 1),
                        **attrs,
                    ),
                )
                scrollable_tr.append(
                    NumTD(
                        round(item.spent, 1),
                        **spent_attrs,
                    ),
                )
            else:
                scrollable_tr.append(NumTD("", **{
                    "class": "hours",
                    "data-sprint-id": str(sprint.id),
                }))
                scrollable_tr.append(NumTD("", **{
                    "class": "hours",
                    "data-sprint-id": str(sprint.id),
                }))

        # add sprint ID to rows
        sprint_ids_data_attr = {
            "data-sprint-ids": ",".join(sprint_ids),
            "data-component-id": component_id,
        }
        tr.attrs.update(sprint_ids_data_attr)
        scrollable_tr.attrs.update(sprint_ids_data_attr)

        rows.append(tr)
        scrollable_rows.append(scrollable_tr)

    return Div(
        Div(
            Table(rows, **table_options),
            **{"class": "combined-left"},
        ),
        Div(
            Table(scrollable_rows, **table_options),
            **{"class": "combined-right scrollable"},
        ),
        **{"class": "combined issues"},
    )
