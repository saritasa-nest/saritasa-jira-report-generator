from pandas import DataFrame

from ..constants import Status
from ..utils.tags import TD, TH, TR, A, Table, NumTD


def generate_epics_table(
        df: DataFrame,
        epics: DataFrame,
        **table_options: str,
):
    rows = []
    header = TR()

    if epics.empty:
        return Table(rows, **table_options)

    epics_list = list(epics.iterrows())
    completed_statuses = (
        *Status.CLIENT_REVIEW.value,
        *Status.COMPLETED.value,
        *Status.VERIFIED.value,
        *Status.TM_PM_VERIFY.value,
    )
    qa_statuses = (
        *Status.IN_QA.value,
    )

    header.append(TH("Epic"))
    header.append(TH("Jira ID"))
    header.append(TH("Status", **{"class": "status"}))
    header.append(TH("Tasks"))
    header.append(TH("Testing"))
    header.append(TH("Completed"))
    header.append(TH("Estimated", **{"class": "hours"}))
    header.append(TH("Spent", **{"class": "hours"}))
    header.append(TH("Left", **{"class": "hours"}))

    rows.append(header)

    for _, epic in epics_list:
        row = TR(**{"data-epic-id": epic.id})
        epic_tasks = df[df["parent"].apply(
            lambda x: x is not None and x.id == epic.id
        )]
        epic_completed_tasks = epic_tasks[epic_tasks["status"].apply(
            lambda x: x.name in completed_statuses,
        )]
        epic_qa_tasks = epic_tasks[epic_tasks["status"].apply(
            lambda x: x.name in qa_statuses,
        )]
        estimate = round(epic_tasks.estimate.sum(), 1)
        spent = round(epic_tasks.spent.sum(), 1)
        left = round(estimate - spent, 1)

        row.append(TD(epic.summary))
        row.append(TD(A(epic.key, href=epic.link)))
        row.append(TD(epic.status, **{"class": "status nowrap"}))
        row.append(NumTD(epic_tasks.id.count()))
        row.append(NumTD(
            epic_qa_tasks.id.count()
            if not epic_qa_tasks.empty
            else 0
        ))
        row.append(NumTD(
            epic_completed_tasks.id.count()
            if not epic_completed_tasks.empty
            else 0
        ))
        row.append(NumTD(estimate))
        row.append(NumTD(spent))
        row.append(NumTD(left if left > 0 else 0))

        rows.append(row)

    if not epics_list:
        rows = []

    return Table(rows, **table_options)
