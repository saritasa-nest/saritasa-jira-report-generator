from pandas import DataFrame

from ..constants import Status
from ..utils.data import status_name_series
from ..utils.formatters import format_status_badges
from ..utils.tags import TD, TH, TR, A, NumTD, Table


def generate_epics_table(
    df: DataFrame,
    epics: DataFrame,
    parent_index_map: dict[str, list[int]] | None = None,
    **table_options: str,
):
    rows = []
    header = TR()

    if epics.empty:
        return Table(rows, **table_options)

    completed_statuses = (
        *Status.IN_REVIEW.value,
        *Status.COMPLETED.value,
        *Status.VERIFIED.value,
        *Status.TM_PM_VERIFY.value,
    )
    qa_statuses = (
        *Status.IN_QA.value,
    )

    header.append(TH("Epic"))
    header.append(TH("Jira ID"))
    header.append(TH("Status"))
    header.append(TH("Tasks"))
    header.append(TH("Testing"))
    header.append(TH("Completed", **{"class": "numeric"}))
    header.append(TH("Estimated", **{"class": "numeric"}))
    header.append(TH("Spent"))
    header.append(TH("Left"))

    rows.append(header)

    for _, epic in epics.iterrows():
        row = TR(**{"data-epic-id": epic.id})
        if parent_index_map is not None:
            indices = parent_index_map.get(str(epic.id), [])
            epic_tasks = (
                df.loc[indices]
                if indices
                else df.iloc[0:0]
            )
        else:
            epic_tasks = df[df["parent"].apply(
                lambda x: x is not None and x.id == epic.id,
            )]

        status_series = status_name_series(epic_tasks)
        tasks_count = len(epic_tasks)
        completed_count = int(status_series.isin(completed_statuses).sum())
        qa_count = int(status_series.isin(qa_statuses).sum())
        estimate = round(epic_tasks.estimate.sum(), 1)
        spent = round(epic_tasks.spent.sum(), 1)
        left = round(estimate - spent, 1)

        row.append(TD(epic.summary, **{"class": "summary"}))
        row.append(TD(A(epic.key, href=epic.link), **{"class": "key"}))
        row.append(TD(
            f"{epic.status}{format_status_badges(epic)}",
            **{"class": "status"},
        ))
        row.append(NumTD(tasks_count))
        row.append(NumTD(qa_count))
        row.append(NumTD(completed_count))
        row.append(NumTD(estimate))
        row.append(NumTD(spent))
        row.append(NumTD(left if left > 0 else 0))

        rows.append(row)

    return Table(rows, **table_options)
