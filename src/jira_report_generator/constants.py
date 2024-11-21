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
    CLIENT_REVIEW = (
        "Client Review",
    )
    IN_QA = (
        "In QA",
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
    )
    BACKLOG = (
        "Backlog",
    )


class Type(Enum):
    EPIC = "Epic"
    STORY = "Story"
