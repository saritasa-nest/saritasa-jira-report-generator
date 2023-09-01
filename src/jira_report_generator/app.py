import argparse
import logging
import os
import sys
from logging import Formatter, StreamHandler

from decouple import config
from jinja2 import Environment, FileSystemLoader
from jira import JIRA
from jira_report_generator.tables.stories import generate_stories_table

from jira_report_generator.tables.unversioned import generate_unversioned_table
from .tables.assignees import generate_assignees_table
from .tables.backlog import generate_backlog_table
from .tables.epics import generate_epics_table
from .tables.issues import generate_issues_table
from .tables.statuses import generate_statuses_table
from .tables.versions import generate_versions_table
from pandas import DataFrame

from .constants import JIRA_FETCH_FIELDS
from .utils.data import (
    filter_data_by_statuses,
    prepare_issues_table_data,
    prepare_backlog_table_data,
    prepare_not_finished_statuses_data,
    prepare_components_data,
    get_dataframe,
    get_versioned_issues,
    prepare_unversioned_table_data,
    render_template,
)
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
        os.path.join(os.path.dirname(__file__), "static"),
    ),
)

logger = logging.getLogger(__name__)
handler = StreamHandler(stream=sys.stdout)
formatter = Formatter(fmt='[%(asctime)s: %(levelname)s] %(message)s')

handler.setFormatter(formatter)
logger.addHandler(handler)


def get_data(project_key: str) -> dict[str, list]:
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
            fields=JIRA_FETCH_FIELDS,
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


def construct_tables(
    issues_dataframe: DataFrame,
    versions: list,
) -> list[Table]:
    """Construct tables from data."""
    versioned_df = get_versioned_issues(issues_dataframe)
    tables = []
    components = prepare_components_data(versioned_df)
    not_finished_statuses = prepare_not_finished_statuses_data(
        versioned_df,
    )

    # statuses and assignees table
    statuses_and_assignees_table_df = filter_data_by_statuses(
        versioned_df,
        not_finished_statuses,
    )
    if not statuses_and_assignees_table_df.empty:
        # statuses table
        tables.append(
            generate_statuses_table(
                statuses_and_assignees_table_df,
                not_finished_statuses,
                **{"class": "issues"},
            )
        )

        # assignees table
        tables.append(
            generate_assignees_table(
                statuses_and_assignees_table_df,
                issues_dataframe.assignee.explode().unique().tolist(),
                **{"class": "assignees"},
            ),
        )

    # # statuses table
    # logger.info("Generate Statuses table")
    # statuses_df = prepare_statuses_table_data(versioned_df)
    # tables.append(
    #     generate_statuses_table(
    #         statuses_df,
    #         not_finished_statuses,
    #         **{"class": "issues"},
    #     ),
    # )

    # # assignees table
    # assignee_table_df = prepare_assignees_table_data(versioned_df)

    # if not assignee_table_df.empty:
    #     logger.info("Generate Assignee table")

    #     tables.append(
    #         generate_assignees_table(
    #             assignee_table_df,
    #             issues_dataframe.assignee.explode().unique().tolist(),
    #             **{"class": "assignees"},
    #         ),
    #     )

    # versions table
    if not versioned_df.empty:
        logger.info("Generate Versions table")
        tables.append(
            generate_versions_table(
                versioned_df,
                versions,
                **{"class": "versions"},
            ),
        )

    # components table
    logger.info("Generate Components table")

    for component in components:
        tables.append(
            generate_issues_table(
                prepare_issues_table_data(versioned_df, component),
                versions,
                component_id=component.id,
                **{"class": "component"},
            ),
        )

    # epics table
    logger.info("Generate Epics table")
    tables.append(
        generate_epics_table(issues_dataframe, **{"class": "epics"}),
    )

    # stories table
    logger.info("Generate Stories table")
    tables.append(
        generate_stories_table(issues_dataframe, **{"class": "stories"}),
    )

    # unversioned issues table
    unversioned_df = prepare_unversioned_table_data(issues_dataframe)

    if not unversioned_df.empty:
        logger.info("Generate Unversioned Issues table")
        tables.append(
            generate_unversioned_table(
                unversioned_df,
                **{"class": "backlog"},
            ),
        )

    # backlog table
    backlog_df = prepare_backlog_table_data(issues_dataframe)

    if not backlog_df.empty:
        logger.info("Generate Backlog table")
        tables.append(
            generate_backlog_table(backlog_df, **{"class": "backlog"}),
        )

    return tables


def get_tables(jira_project_key: str) -> list[Table]:
    """Get tables."""
    data = get_data(jira_project_key)
    logger.info("Prepare Pandas dataframe")
    df = get_dataframe(data["issues"])
    return construct_tables(df, data["versions"])


def write_tables(tables: list[Table], filename: str, key: str):
    """Write tables."""

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    if not filename:
        filename = f"{OUTPUT_DIR}/{key}.html"

    logger.info(f"Write to {filename}")

    with open(filename, "w", encoding="utf-8") as f:
        f.write(
            render_template(tables, key, env.get_template("template.html")),
        )


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
