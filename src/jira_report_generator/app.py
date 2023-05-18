import argparse
import logging
import os
import sys
from logging import Formatter, StreamHandler
from typing import Dict, List

from decouple import config
from jinja2 import Environment, FileSystemLoader
from jira import JIRA
from pandas import DataFrame

from .constants import Status
from .tables.assignees import generate_assignees_table
from .tables.backlog import generate_backlog_table
from .tables.epics import generate_epics_table
from .tables.issues import generate_issues_table
from .tables.statuses import generate_statuses_table
from .tables.versions import generate_versions_table
from .utils.tags import Table

SERVER_URL = str(config("SERVER_URL"))
EMAIL = str(config("EMAIL"))
API_TOKEN = str(config("API_TOKEN"))
OUTPUT_DIR = ".output"

parser = argparse.ArgumentParser()
parser.add_argument("key", type=str, help="JIRA project key")
parser.add_argument(
    "-o",
    "--output",
    type=str,
    help="output filename",
)
parser.add_argument(
    "-v",
    "--verbose",
    help="show log",
    action='store_true',
)

env = Environment(
    loader=FileSystemLoader(
        os.path.join(os.path.dirname(__file__),"static"),
    ),
)

logger = logging.getLogger(__name__)
handler = StreamHandler(stream=sys.stdout)
formatter = Formatter(fmt='[%(asctime)s: %(levelname)s] %(message)s')

handler.setFormatter(formatter)
logger.addHandler(handler)


def get_data(project_key: str) -> Dict[str, list]:
    logger.info(f"Connect to Jira ({project_key})")

    jira = JIRA(server=SERVER_URL, basic_auth=(EMAIL, API_TOKEN))
    result = {
        "issues": [],
        "versions": [],
    }
    offset = 0
    stop = False
    page_size = 100

    # get paginated issues
    while not stop:
        issues = jira.search_issues(
            f"project={project_key}",
            startAt=offset,
            maxResults=page_size,
        )
        result["issues"] += issues
        offset += page_size

        logger.info(f"Collected {len(issues)} issue(s)")

        if len(issues) < page_size:
            stop = True

    logger.info("Get versions")

    # get release versions
    result["versions"] = jira.project_versions(project_key)
    result["versions"].sort(key=lambda x: getattr(x, "releaseDate", ""))

    return result


def get_dataframe(data: list) -> DataFrame:
    result = []

    logger.info("Prepare Pandas dataframe")

    for item in data:
        estimate = (
            item.fields.timeoriginalestimate / 60 / 60
            if item.fields.timeoriginalestimate
            else 0
        )
        spent = (
            item.fields.timespent / 60 / 60
            if item.fields.timespent
            else 0
        )
        release_date = [
            getattr(v, "releaseDate", None)
            for v
            in item.fields.fixVersions
        ]

        result.append({
            "id": item.id,
            "key": item.key,
            "status": item.fields.status,
            "summary": item.fields.summary,
            "assignee": item.fields.assignee,
            "components": item.fields.components,
            "estimate": estimate,
            "spent": spent,
            "ratio": (
                round(spent / estimate, 2)
                if spent and estimate
                else 0
            ),
            "versions": item.fields.fixVersions,
            "link": item.permalink(),
            "type": item.fields.issuetype,
            "parent": getattr(item.fields, "parent", None),
            "release_date": release_date[0] if release_date else None,
        })

    df = DataFrame(result)

    # only issues with versions
    return df


def get_versioned_issues(df: DataFrame) -> DataFrame:
    return df[df["versions"].apply(lambda x: len(x) > 0)].sort_values(
        by=["release_date", "id"],
    )


def get_backlog(df: DataFrame) -> DataFrame:
    return df[df["versions"].apply(lambda x: len(x) == 0)]


def render_template(tables: List[Table], title: str) -> str:
    """Render template."""
    template = env.get_template("template.html")
    sections = map(str, tables)

    return template.render(
        title=title,
        sections=sections,
    )


def write_tables(tables: List[Table], filename: str, key: str):
    """Write tables."""

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    if not filename:
        filename = f"{OUTPUT_DIR}/{key}.html"

    logger.info(f"Write to {filename}")

    with open(filename, "w", encoding="utf-8") as f:
        f.write(render_template(tables, key))


def get_tables(jira_project_key: str) -> List[Table]:
    """Get tables."""
    data = get_data(jira_project_key)
    tables = []
    df = get_dataframe(data["issues"])
    versioned_df = get_versioned_issues(df)

    # collect used components
    components = sorted(list(filter(
        lambda x: hasattr(x, "name"),
        versioned_df.components.explode().unique().tolist()
    )), key=lambda x: x.id)

    # collect used statuses
    statuses = versioned_df.status.explode().unique().tolist()

    # current statuses
    not_finished_statuses = list(filter(lambda x: x.name in (
        Status.IN_PROGRESS.value,
        Status.READY_FOR_DEVELOPMENT.value,
    ), statuses))

    if not versioned_df.empty:
        logger.info("Generate Versions table")

        # versions table
        tables.append(Table(
            generate_versions_table(
                versioned_df,
                data["versions"],
            ),
            **{"class": "versions"},
        ))

    # statuses table
    logger.info("Generate Statuses table")
    tables.append(Table(
        generate_statuses_table(
            versioned_df[versioned_df["components"].apply(
                lambda x: len(x) > 0 and set(x).issubset(components),
            )],
            not_finished_statuses,
        ),
        **{"class": "issues"},
    ))

    # assignees table
    assignee_table_issues = versioned_df[versioned_df["status"].apply(
        lambda x: x in not_finished_statuses
    )]

    if not assignee_table_issues.empty:
        logger.info("Generate Assignee table")

        tables.append(Table(
            generate_assignees_table(
                assignee_table_issues,
                versioned_df.assignee.explode().unique().tolist(),
            ),
            **{"class": "assignees"},
        ))

    # epics table
    logger.info("Generate Epics table")
    tables.append(Table(
        generate_epics_table(df),
        **{"class": "epics"},
    ))

    # components table
    logger.info("Generate Components table")

    for component in components:
        tables.append(Table(
            generate_issues_table(
                versioned_df[versioned_df["components"].apply(
                    lambda x: component in x
                )],
                data["versions"],
            ),
            **{"class": "component"},
        ))

    # backlog table
    backlog_issues = get_backlog(df)

    if not backlog_issues.empty:
        logger.info("Generate Backlog table")
        tables.append(Table(
            generate_backlog_table(
                backlog_issues.sort_values("id"),
            ),
            **{"class": "backlog"},
        ))

    return tables


def main():
    cli_args = parser.parse_args()

    if cli_args.verbose:
        logger.setLevel(logging.INFO)

    write_tables(
        get_tables(cli_args.key),
        cli_args.output,
        cli_args.key,
    )


if __name__ == "__main__":
    main()
