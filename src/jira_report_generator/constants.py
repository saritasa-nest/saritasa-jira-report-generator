from enum import Enum

from decouple import config

TO_QA_COUNTER_FIELD_ID = config("JIRA_TO_QA_COUNTER_FIELD_ID", default="")
LAST_STATUS_CHANGE_TIME_FIELD_ID = config(
    "JIRA_LAST_STATUS_CHANGE_TIME_FIELD_ID",
    default="",
)
DEVELOPMENT_ESTIMATE_FIELD_ID = config(
    "JIRA_DEVELOPMENT_ESTIMATE_FIELD_ID",
    default="",
)

JIRA_FETCH_FIELDS = [
    "status",
    "summary",
    "assignee",
    "components",
    "labels",
    "timeoriginalestimate",
    "timespent",
    "fixVersions",
    "issuetype",
    "parent",
    TO_QA_COUNTER_FIELD_ID,
    LAST_STATUS_CHANGE_TIME_FIELD_ID,
    DEVELOPMENT_ESTIMATE_FIELD_ID,
]


def get_jira_fetch_fields(group_by: "GroupBy | None" = None) -> list[str]:
    """Return JIRA fetch fields based on group_by mode.

    When grouping by labels, exclude 'components'.
    When grouping by components, exclude 'labels'.
    """
    if group_by is None:
        return list(JIRA_FETCH_FIELDS)

    exclude = set()
    if group_by == GroupBy.LABEL:
        exclude.add("components")
    elif group_by == GroupBy.COMPONENT:
        exclude.add("labels")

    return [f for f in JIRA_FETCH_FIELDS if f not in exclude]

MAX_THREADS_COUNT = 4
HOURS_N_DECIMAL_PLACES = 1


class Status(Enum):
    VERIFIED = (
        "Verified",
    )
    IN_REVIEW = (
        "Client Review",
        "In Review",
    )
    IN_QA = (
        "Ready for QA",
        "In QA",
        "QA Passed",
    )
    COMPLETED = (
        "Completed.",
        "Completed",
    )
    CODE_REVIEW = (
        "Code Review",
    )
    TM_PM_VERIFY = (
        "TM/PM Verify",
    )
    READY_FOR_DEVELOPMENT = (
        "Ready for Development",
    )
    IN_PROGRESS = (
        "In Progress",
        "In Development",
    )
    BACKLOG = (
        "Backlog",
    )
    CANCELLED = (
        "Cancelled",
    )
    INTERNAL = (
        "Internal",
    )


class GroupBy(Enum):
    COMPONENT = "component"
    LABEL = "label"


class Type(Enum):
    EPIC = "Epic"
    STORY = "Story"
