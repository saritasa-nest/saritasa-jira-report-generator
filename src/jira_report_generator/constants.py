from enum import Enum

JIRA_FETCH_FIELDS = [
    "status",
    "summary",
    "assignee",
    "components",
    "timeoriginalestimate",
    "timespent",
    "fixVersions",
    "issuetype",
    "parent",
]

MAX_THREADS_COUNT = 4


class Status(Enum):
    VERIFIED = (
        "Verified",
    )
    IN_REVIEW = (
        "Client Review",
        "In Review",
    )
    IN_QA = (
        "In QA",
        "Ready for QA",
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


class Type(Enum):
    EPIC = "Epic"
    STORY = "Story"
