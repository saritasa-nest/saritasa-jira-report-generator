# Jira Report Generator

Just JIRA project report generator.

## Configure

Need to create `.env` file with variables:

```
SERVER_URL=""
EMAIL=""
API_TOKEN=""
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

### Code

```python
from jira_report_generator import get_tables

tables = get_tables(JIRA_PROJECT_KEY)  # list of <Table: > objects
rendered_tables_html = map(str, tables)  # str reprs -- <table>
```
