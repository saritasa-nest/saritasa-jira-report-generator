from pandas import DataFrame

from ..constants import Status
from ..utils.formatters import format_name
from ..utils.tags import TD, TH, TR, A, Table


def generate_issues_table(
    df: DataFrame,
    versions: list,
    **table_options: str,
):
    rows = []

    # table header
    header = TR()
    header.append(TH("Summary", **{"class": "summary", "rowspan": 2}))
    header.append(TH("Type", **{"class": "type", "rowspan": 2}))
    header.append(TH("Jira ID", **{"class": "key", "rowspan": 2}))
    header.append(TH("Status", **{"class": "status", "rowspan": 2}))
    header.append(TH("Assignee", **{"class": "assignee", "rowspan": 2}))

    for version in versions:
        releaseDate = getattr(version, "releaseDate", "")

        header.append(TH(
            f"{version.name}<br/><small>{releaseDate}</small>",
            **{"class": "version", "colspan": 2},
        ))

    rows.append(header)

    # table subheader
    subheader = TR()

    for version in versions:
        version_tasks = df[df["versions"].apply(lambda x: version in x)]
        estimate = round(version_tasks.estimate.sum(), 1)
        spent = round(version_tasks.spent.sum(), 1)

        subheader.append(TH(estimate, **{
            "class": "hours subheader",
        }))
        subheader.append(TH(spent, **{
            "class": (
                "hours subheader danger"
                if estimate != 0 and spent > estimate
                else "hours subheader"
            )
        }))

    rows.append(subheader)

    # table body
    for _, item in df.iterrows():
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

                attrs = {
                    "class": f"version {background}",
                }

                spent_attrs = dict(attrs)

                if (item.estimate != 0 and item.spent > item.estimate):
                    spent_attrs.update({
                        "class": f"version danger {background}",
                    })

                tr.append(
                    TD(
                        round(item.estimate / divisor, 1),
                        **attrs,
                    )
                )
                tr.append(
                    TD(
                        round(item.spent / divisor, 1),
                        **spent_attrs,
                    )
                )
            else:
                tr.append(TD(""))
                tr.append(TD(""))

        rows.append(tr)

    return Table(rows, **table_options)
