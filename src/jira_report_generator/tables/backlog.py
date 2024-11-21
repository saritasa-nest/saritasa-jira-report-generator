from pandas import DataFrame

from ..utils.formatters import format_name
from ..utils.tags import TD, TH, TR, A, NumTD, Table


def generate_backlog_table(df: DataFrame, **table_options: str):
    rows = []

    # table header
    header = TR()
    header.append(TH("Summary", **{"class": "summary"}))
    header.append(TH("Type", **{"class": "type"}))
    header.append(TH("Jira ID", **{"class": "key"}))
    header.append(TH("Status", **{"class": "status"}))
    header.append(TH("Assignee", **{"class": "assignee"}))
    header.append(TH("Components"))
    header.append(TH("Spent", **{"class": "hours"}))

    rows.append(header)

    # table body
    for _, item in df.iterrows():
        tr = TR()
        status_attrs = {"class": "status nowrap"}

        # summary
        tr.append(TD(item.summary, **{"class": "summary"}))

        # issue type
        tr.append(TD(item.type, **{"class": "type"}))

        # link to the issue
        tr.append(
            TD(
                A(item.key, **{"href": item.link}),
                **{"class": "nowrap"},
            ),
        )

        # status
        tr.append(TD(item.status.name, **status_attrs))

        # assignee
        tr.append(TD(
            format_name(getattr(item.assignee, "displayName", "")),
            **{"class": "nowrap"},
        ))

        # components
        tr.append(TD(", ".join([c.name for c in item.components])))

        # spent
        tr.append(NumTD(round(item.spent, 1)))

        rows.append(tr)

    # footer
    row = TR(**{"class": "summary"})

    row.append(TD("", colspan=6))
    row.append(NumTD(round(df.spent.sum(), 1)))

    rows.append(row)

    return Table(rows, **table_options)
