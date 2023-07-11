from pandas import DataFrame

from ..constants import Status
from ..utils.formatters import format_name
from ..utils.tags import TD, TH, TR, A, Table, Div


def generate_issues_table(
    df: DataFrame,
    versions: list,
    **table_options: str,
):
    rows = []
    scrollable_rows = []

    # table header
    header = TR(**{"class": "h60"})
    header.append(TH("Summary", **{"class": "summary"}))
    header.append(TH("Type", **{"class": "type"}))
    header.append(TH("Jira ID", **{"class": "key"}))
    header.append(TH("Status", **{"class": "status"}))
    header.append(TH("Assignee", **{"class": "assignee"}))

    rows.append(header)

    # scrollable header
    scrollable_header = TR(**{"class": "h40"})
    for version in versions:
        releaseDate = getattr(version, "releaseDate", "")

        scrollable_header.append(TH(
            f"{version.name}<br/><small>{releaseDate}</small>",
            **{"class": "version", "colspan": 2},
        ))

    scrollable_rows.append(scrollable_header)

    # scrollable subheader
    scrollable_subheader = TR(**{"class": "h20"})
    for version in versions:
        version_tasks = df[df["versions"].apply(lambda x: version in x)]
        estimate = round(version_tasks.estimate.sum(), 1)
        spent = round(version_tasks.spent.sum(), 1)

        scrollable_subheader.append(TH(estimate, **{
            "class": "hours subheader",
        }))
        scrollable_subheader.append(TH(spent, **{
            "class": (
                "hours subheader danger"
                if estimate != 0 and spent > estimate
                else "hours subheader"
            )
        }))

    scrollable_header.append(scrollable_subheader)

    # table body
    for _, item in df.iterrows():
        version_ids = []
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
        tr.append(TD(item.type, **{"class": "type"}))

        # link to the issue
        tr.append(
            TD(
                A(item.key, **{"href": item.link}),
                **{"class": "nowrap"},
            )
        )

        if item.status.name in (
                Status.VERIFIED.value,
                Status.CLIENT_REVIEW.value,
                Status.COMPLETED.value,
                Status.TM_PM_VERIFY.value,
        ):
            status_attrs.update({"class": "status nowrap success"})
            background = "done"
        elif item.status.name in (
                Status.IN_QA.value,
                Status.CODE_REVIEW.value,
        ):
            status_attrs.update({"class": "status nowrap warning"})
            background = "in-progress"

        # status
        tr.append(TD(item.status.name, **status_attrs))

        # assignee
        tr.append(TD(
            format_name(getattr(item.assignee, "displayName", "")),
            **{"class": "assignee nowrap"},
        ))

        for version in versions:
            if (item.versions and version in item.versions):
                divisor = len(item.versions)
                version_ids.append(str(version.id))

                attrs = {
                    "class": f"hours version {background}",
                }

                spent_attrs = dict(attrs)

                if (item.estimate != 0 and item.spent > item.estimate):
                    spent_attrs.update({
                        "class": f"hours version danger {background}",
                    })

                scrollable_tr.append(
                    TD(
                        round(item.estimate / divisor, 1),
                        **attrs,
                    )
                )
                scrollable_tr.append(
                    TD(
                        round(item.spent / divisor, 1),
                        **spent_attrs,
                    )
                )
            else:
                scrollable_tr.append(TD("", **{"class": "hours"}))
                scrollable_tr.append(TD("", **{"class": "hours"}))

        # add version ID to rows
        version_ids_data_attr = {"data-version-ids": ",".join(version_ids)}
        tr.attrs.update(version_ids_data_attr)
        scrollable_tr.attrs.update(version_ids_data_attr)

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
        **{"class": "combined"},
    )
