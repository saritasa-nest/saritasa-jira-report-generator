# Jira Report Generator

Just JIRA project report generator.

## Configure

Need to create `.env` file with variables:

```
SERVER_URL=""
EMAIL=""
API_TOKEN=""
JIRA_TO_QA_COUNTER_FIELD_ID=""
```

API token: https://id.atlassian.com/manage-profile/security/api-tokens

## Setup virtual environment

```bash
python3.10 -m venv .virtualenv
source .virtualenv/bin/activate
```

## Install app

```bash
pip install jira-report-generator
```

##  Use

### CLI

#### Report

```bash
jira-report-generator JIRA_PROJECT_KEY
```

In this case, by default, the file will be located in the 
`.output` directory (make sure this directory exists) 
and named `JIRA_PRTOJECT_KEY.html`.

Use `-o` or `--output` if you want provide custom path for output:

```bash
jira-report-generator JIRA_PROJECT_KEY -o FILENAME
```

Add `-v` or `--verbose` flag if you want to see some logs:

```bash
[2023-04-24 14:38:04,370: INFO] Connect to Jira (JIRA_PROJECT_KEY)
[2023-04-24 14:38:05,009: INFO] Collect issues
[2023-04-24 14:38:18,274: INFO] Collected 55 issue(s)
[2023-04-24 14:38:18,274: INFO] Get versions
[2023-04-24 14:38:18,603: INFO] Prepare Pandas dataframe
[2023-04-24 14:38:18,620: INFO] Generate Versions table
[2023-04-24 14:38:18,714: INFO] Generate Statuses table
[2023-04-24 14:38:18,731: INFO] Generate Assignee table
[2023-04-24 14:38:18,750: INFO] Generate Epics table
[2023-04-24 14:38:18,755: INFO] Generate Components table
[2023-04-24 14:38:18,929: INFO] Generate Backlog table
[2023-04-24 14:38:18,941: INFO] Write to FILENAME
```

Find `FILENAME` file and get fun.

#### Task statuse transitions

```bash
jira-report-generator JIRA_TASK_ID
```

output is:

```log
2025-03-25T07:16:39.981-0500 Backlog -> Ready for Development (Denis)
2025-04-23T02:32:04.603-0500 Ready for Development -> In Progress (Khan)
2025-04-23T02:32:08.009-0500 In Progress -> Code Review (Khan)
2025-04-23T02:32:09.677-0500 Code Review -> In QA (Khan)
2025-05-06T03:35:52.911-0500 In QA -> Ready for Development (Qu)
2025-05-09T05:18:01.321-0500 Ready for Development -> In Progress (Khan)
2025-05-16T05:33:18.047-0500 In Progress -> Code Review (Khan)
2025-05-16T05:33:20.245-0500 Code Review -> In QA (Khan)
2025-05-20T23:56:59.423-0500 In QA -> Client Review (Qu)
2025-07-02T04:08:47.373-0500 Client Review -> Verified (Denis)
---
Code Review -> In QA (2)
In Progress -> Code Review (2)
Ready for Development -> In Progress (2)
Client Review -> Verified (1)
In QA -> Client Review (1)
In QA -> Ready for Development (1)
Backlog -> Ready for Development (1)
```

### Code

```python
from jira_report_generator import get_tables

tables = get_tables(JIRA_PROJECT_KEY)  # list of <Table: > objects
rendered_tables_html = map(str, tables)  # str reprs -- <table>
```

```python
from jira_report_generator.app import get_issue_status_changelog

status_changelog = get_issue_status_changelog(JIRA_CLIENT, JIRA_TASK_ID)

# [
#     {
#         "from": "Backlog",
#         "to": "Ready for Development",
#         "author": "Denis",
#         "created": "2025-07-02 08:47",
#     }
# ]
```

```python
from jira_report_generator.app import get_issue_assignee_changelog

status_changelog = get_issue_assignee_changelog(JIRA_CLIENT, JIRA_TASK_ID)

# [
#     {
#         "from": "Rodrigo",
#         "to": "Lucia",
#         "author": "Rodrigo",
#         "created": "2025-07-02 08:47",
#     }
# ]
```

```python
from jira_report_generator.app import get_issue_worklogs

worklogs = get_issue_worklogs(JIRA_CLIENT, JIRA_TASK_ID)

# [
#     {
#         "author": "Denis",
#         "spent": "1h 30m",
#         "created": "2025-07-02 08:47",
#     }
# ]
```
