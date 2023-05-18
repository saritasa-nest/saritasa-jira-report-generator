from enum import Enum


class Status(Enum):
    VERIFIED = "Verified"
    CLIENT_REVIEW = "Client Review"
    IN_QA = "In QA"
    COMPLETED = "Completed."
    CODE_REVIEW = "Code Review"
    TM_PM_VERIFY = "TM/PM Verify"
    READY_FOR_DEVELOPMENT = "Ready for Development"
    IN_PROGRESS = "In Progress"
