from pandas import DataFrame

from ..utils.formatters import (
    format_name,
    format_to_qa_count_badge,
)
from ..utils.tags import TD, TH, TR, A, NumTD, Table


def generate_backlog_table(df: DataFrame, **table_options: str):
    rows = []

    # table header
    header = TR()
    header.append(TH("Summary"))
    header.append(TH("Type"))
    header.append(TH("Jira ID"))
    header.append(TH("Status"))
    header.append(TH("Assignee"))
    header.append(TH("Components"))
    header.append(TH("Spent"))

    rows.append(header)

    # table body
    for _, item in df.iterrows():
        tr = TR()

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
                **{"class": "key"},
            ),
        )

        # status
        tr.append(TD(
            f"{item.status.name}{format_to_qa_count_badge(item)}",
            **{"class": "status"},
        ))

        # assignee
        tr.append(TD(
            format_name(getattr(item.assignee, "displayName", "")),
            **{"class": "assignee"},
        ))

        # components
        tr.append(TD(
            ", ".join([c.name for c in item.components]),
            **{"class": "components"},
        ))

        # spent
        tr.append(NumTD(round(item.spent, 1)))

        rows.append(tr)

    # footer
    row = TR(**{"class": "summary"})

    row.append(TD("", colspan=6))
    row.append(NumTD(round(df.spent.sum(), 1)))

    rows.append(row)

    return Table(rows, **table_options)
