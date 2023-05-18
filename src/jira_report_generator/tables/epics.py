from pandas import DataFrame

from ..constants import Status
from ..utils.tags import TD, TH, TR, A


def generate_epics_table(df: DataFrame):
    rows = []
    header = TR()
    epics = df[df["type"].apply(lambda x: x.name == "Epic")]
    completed_statuses = (
        Status.CLIENT_REVIEW.value,
        Status.COMPLETED.value,
        Status.VERIFIED.value,
        Status.TM_PM_VERIFY.value,
    )
    qa_statuses = (
        Status.IN_QA.value,
    )

    header.append(TH("Epic"))
    header.append(TH("Jira ID"))
    header.append(TH("Tasks"))
    header.append(TH("Testing"))
    header.append(TH("Completed"))
    header.append(TH("Estimated", **{"class": "hours"}))
    header.append(TH("Spent", **{"class": "hours"}))
    header.append(TH("Left", **{"class": "hours"}))

    rows.append(header)

    for _, epic in epics.iterrows():
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
        row.append(TD(epic_tasks.id.count()))
        row.append(TD(
            epic_qa_tasks.id.count()
            if not epic_qa_tasks.empty
            else 0
        ))
        row.append(TD(
            epic_completed_tasks.id.count()
            if not epic_completed_tasks.empty
            else 0
        ))
        row.append(TD(estimate))
        row.append(TD(spent))
        row.append(TD(left if left > 0 else 0))

        rows.append(row)

    return rows
