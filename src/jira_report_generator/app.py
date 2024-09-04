import argparse
import logging
import os
import sys
from logging import Formatter, StreamHandler
from datetime import datetime

from decouple import config
from jinja2 import Environment, FileSystemLoader
from jira import JIRA
from pandas import DataFrame

from .tables.assignees import generate_assignees_table
from .tables.backlog import generate_backlog_table
from .tables.epics import generate_epics_table
from .tables.issues import generate_issues_table
from .tables.statuses import generate_statuses_table
from .tables.versions import generate_versions_table
from .tables.project import generate_project_table
from .tables.board import generate_board_table
from .tables.sprints import generate_sprints_table
from .tables.stories import generate_stories_table
from .tables.unversioned import generate_unversioned_table
from .constants import JIRA_FETCH_FIELDS
from .utils.data import (
    filter_data_by_statuses,
    get_sprinted_issues,
    prepare_issues_table_data,
    prepare_backlog_table_data,
    prepare_not_finished_statuses_data,
    prepare_components_data,
    get_dataframe,
    get_versioned_issues,
    prepare_unversioned_table_data,
    render_template,
)
from .utils.tags import H2, Div, Section, Table
from .utils.tabs import wrap_with_tabs

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


def get_paginated_issues(
        jira_client: JIRA,
        jql_str: str,
        fields: list = JIRA_FETCH_FIELDS,
) -> list:
    result = []
    offset = 0
    stop = False
    page_size = 100

    while not stop:
        issues = jira_client.search_issues(
            jql_str,
            startAt=offset,
            maxResults=page_size,
            fields=fields,
        )
        result += issues
        offset += page_size

        logger.info(f"Collected {len(issues)} issue(s)")

        if len(issues) < page_size:
            stop = True

    return result


def get_extra_data(project_key) -> dict[str, list or dict]:
    logger.info(f"Connect to Jira ({project_key})")

    jira = JIRA(server=SERVER_URL, basic_auth=(EMAIL, API_TOKEN))
    result = {
        "boards": [],
        "issues": {},
    }
    boards = jira.boards(projectKeyOrID=project_key)

    logger.info(f"Collected {len(boards)} board(s)")

    for board in boards:
        logger.info(f"Collect sprints for Board {board.id}")

        try:
            sprints = jira.sprints(board_id=board.id)
        except Exception as e:
            logger.debug(e)
            sprints = []

        board_data = {
            "board": board,
            "sprints": [],
        }

        logger.info(f"Collected {len(sprints)} sprints(s)")

        for sprint in sprints:
            logger.info(f"Collect issues for Sprint {sprint.id}")

            issues = get_paginated_issues(
                jira_client=jira,
                jql_str=(
                    f"project={project_key} "
                    f"AND sprint={sprint.id} "
                    f"ORDER BY created DESC"
                ),
                fields=[],
            )

            for issue in issues:
                result["issues"][issue.id] = {
                    "board": board,
                    "sprint": sprint,
                }

            board_data["sprints"].append(sprint)

        board_data["sprints"].sort(
            key=lambda x: getattr(
                x,
                "startDate",
                # required for correct ordering of future sprints
                # without start date
                str(datetime.now().isoformat()),
            ),
        )
        result["boards"].append(board_data)

    return result


def get_data(project_key: str) -> dict[str, list]:
    logger.info(f"Connect to Jira ({project_key})")

    jira = JIRA(server=SERVER_URL, basic_auth=(EMAIL, API_TOKEN))
    result = {
        "issues": [],
        "versions": [],
    }

    result["issues"] = get_paginated_issues(
        jira_client=jira,
        jql_str=f"project={project_key} ORDER BY created DESC",
    )

    logger.info("Get versions")

    # get release versions
    result["versions"] = jira.project_versions(project_key)
    result["versions"].sort(key=lambda x: getattr(x, "startDate", ""))

    return result


def construct_tables(
    issues_dataframe: DataFrame,
    versions: list,
    boards: list,
) -> list[Table]:
    """Construct tables from data."""
    VERSIONS_TAB_ID = 1
    EMPTY_TAB_CONTENT = "No data."

    versioned_df = get_versioned_issues(issues_dataframe)
    unversioned_df = prepare_unversioned_table_data(issues_dataframe)
    sprinted_df = get_sprinted_issues(issues_dataframe)
    backlog_df = prepare_backlog_table_data(issues_dataframe)
    tables = []
    components = prepare_components_data(versioned_df)
    not_finished_statuses = prepare_not_finished_statuses_data(
        versioned_df,
    )

    # project table
    logger.info("Generate Project table")
    tables.append(Section(
        H2("Project"),
        generate_project_table(
            versioned_df,
            unversioned_df,
            backlog_df,
            **{"class": "project"},
        ),
    ))

    # statuses and assignees table
    statuses_and_assignees_table_df = filter_data_by_statuses(
        versioned_df,
        not_finished_statuses,
    )
    if not statuses_and_assignees_table_df.empty:
        # statuses table
        tables.append(Section(
            H2("Statuses"),
            generate_statuses_table(
                statuses_and_assignees_table_df,
                not_finished_statuses,
                **{"class": "issues"},
            ),
        ))

        # assignees table
        tables.append(Section(
            H2("Assignees"),
            generate_assignees_table(
                statuses_and_assignees_table_df,
                issues_dataframe.assignee.explode().unique().tolist(),
                **{"class": "assignees"},
            ),
        ))

    # prepare tabs header
    tabs_header: list[str, int] = [
        ("Versions", VERSIONS_TAB_ID),
    ]
    if boards and boards[0]["sprints"]:
        for board in boards:
            tabs_header.append((
                board["board"].name,
                board["board"].id,
            ))

    # prepare tabs content
    tabs_content: list[Div, int] = []

    # versions tab
    if not versioned_df.empty:
        version_sections = []

        logger.info("Generate Versions table")
        version_sections.append(Section(
            H2("Versions"),
            generate_versions_table(
                versioned_df,
                versions,
                **{"class": "versions"},
            ),
        ))

        # version components table
        logger.info("Generate Components table")
        for component in components:
            version_sections.append(Section(
                H2(component),
                generate_issues_table(
                    prepare_issues_table_data(versioned_df, component),
                    versions,
                    component_id=component.id,
                    **{"class": "component"},
                ),
            ))
        tabs_content.append((
            "".join(map(str, version_sections)),
            VERSIONS_TAB_ID,
        ))
    else:
        tabs_content.append((
            EMPTY_TAB_CONTENT,
            VERSIONS_TAB_ID,
        ))

    # boards tab
    for board in boards:
        if board["sprints"]:
            board_sections = []
            logger.info("Generate Sprints table")
            board_sections.append(Section(
                H2("Sprints"),
                generate_sprints_table(
                    sprinted_df,
                    board["sprints"],
                    **{"class": "sprints"},
                ),
            ))
            logger.info("Generate Components table")
            for component in components:
                board_sections.append(Section(
                    H2(component),
                    generate_board_table(
                        prepare_issues_table_data(sprinted_df, component),
                        board["sprints"],
                        component_id=component.id,
                        **{"class": "component"},
                    ),
                ))
            tabs_content.append((
                "".join(map(str, board_sections)),
                board["board"].id,
            ))
        else:
            tabs_content.append((
                EMPTY_TAB_CONTENT,
                board["board"].id,
            ))

    tables.append(
        wrap_with_tabs(
            tabs_header,
            tabs_content,
        ),
    )

    # epics table
    logger.info("Generate Epics table")
    tables.append(Section(
        H2("Epics"),
        generate_epics_table(
            issues_dataframe,
            **{"class": "epics"},
        ),
    ))

    # stories table
    logger.info("Generate Stories table")
    tables.append(Section(
        H2("Stories"),
        generate_stories_table(
            issues_dataframe,
            **{"class": "stories"},
        ),
    ))

    # unversioned issues table
    if not unversioned_df.empty:
        logger.info("Generate Unversioned Issues table")
        tables.append(Section(
            H2("Unversioned"),
            generate_unversioned_table(
                unversioned_df,
                **{"class": "backlog"},
            ),
        ))

    # backlog table
    if not backlog_df.empty:
        logger.info("Generate Backlog table")
        tables.append(Section(
            H2("Backlog"),
            generate_backlog_table(
                backlog_df,
                **{"class": "backlog"},
            ),
        ))

    return tables


def get_tables(jira_project_key: str) -> list[Table]:
    """Get tables."""
    data = get_data(jira_project_key)
    extra_data = get_extra_data(jira_project_key)

    logger.info("Prepare Pandas dataframe")
    dataframe = get_dataframe(
        data["issues"],
        extra_data["issues"],
    )

    return construct_tables(
        dataframe,
        data["versions"],
        extra_data["boards"],
    )


def write_tables(tables: list[Table], filename: str, key: str):
    """Write tables."""

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    if not filename:
        filename = f"{OUTPUT_DIR}/{key}.html"

    logger.info(f"Write to {filename}")

    with open(filename, "w", encoding="utf-8") as f:
        f.write(render_template(
            tables,
            key,
            env.get_template("template.html"),
        ))


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
