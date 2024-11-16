from pandas import DataFrame

from ..constants import Status, Type
from ..utils.tags import TD, TH, TR, A, Table, NumTD


def generate_stories_table(
        df: DataFrame,
        stories: DataFrame,
        **table_options: str,
):
    rows = []
    header = TR()

    if stories.empty:
        return Table(rows, **table_options)

    stories_list = list(stories.iterrows())
    completed_statuses = (
        Status.CLIENT_REVIEW.value,
        Status.COMPLETED.value,
        Status.VERIFIED.value,
        Status.TM_PM_VERIFY.value,
    )
    qa_statuses = (
        Status.IN_QA.value,
    )

    header.append(TH("Story"))
    header.append(TH("Jira ID"))
    header.append(TH("Status", **{"class": "status"}))
    header.append(TH("Tasks"))
    header.append(TH("Testing"))
    header.append(TH("Completed"))
    header.append(TH("Estimated", **{"class": "hours"}))
    header.append(TH("Spent", **{"class": "hours"}))
    header.append(TH("Left", **{"class": "hours"}))

    rows.append(header)

    for _, story in stories_list:
        row = TR(**{"data-story-id": story.id})
        story_tasks = df[df["parent"].apply(
            lambda x: x is not None and x.id == story.id
        )]
        story_completed_tasks = story_tasks[story_tasks["status"].apply(
            lambda x: x.name in completed_statuses,
        )]
        story_qa_tasks = story_tasks[story_tasks["status"].apply(
            lambda x: x.name in qa_statuses,
        )]
        estimate = round(story_tasks.estimate.sum(), 1)
        spent = round(story_tasks.spent.sum(), 1)
        left = round(estimate - spent, 1)

        row.append(TD(story.summary))
        row.append(TD(A(story.key, href=story.link)))
        row.append(TD(story.status, **{"class": "status nowrap"}))
        row.append(NumTD(story_tasks.id.count()))
        row.append(NumTD(
            story_qa_tasks.id.count()
            if not story_qa_tasks.empty
            else 0
        ))
        row.append(NumTD(
            story_completed_tasks.id.count()
            if not story_completed_tasks.empty
            else 0
        ))
        row.append(NumTD(estimate))
        row.append(NumTD(spent))
        row.append(NumTD(left if left > 0 else 0))

        rows.append(row)

    if not stories_list:
        rows = []

    return Table(rows, **table_options)
