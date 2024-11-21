import argparse
import collections
import functools
import itertools
import logging
import os
import sys
import typing
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from logging import Formatter, StreamHandler

import jira.resources
from jinja2 import Environment, FileSystemLoader
from jira import JIRA
from pandas import DataFrame

from .constants import JIRA_FETCH_FIELDS, MAX_THREADS_COUNT
from .tables.assignees import generate_assignees_table
from .tables.backlog import generate_backlog_table
from .tables.board import generate_board_table
from .tables.epics import generate_epics_table
from .tables.issues import generate_issues_table
from .tables.project import generate_project_table
from .tables.sprints import generate_sprints_table
from .tables.statuses import generate_statuses_table
from .tables.stories import generate_stories_table
from .tables.unversioned import generate_unversioned_table
from .tables.versions import generate_versions_table
from .utils.data import (
    filter_data_by_statuses,
    get_dataframe,
    get_epics,
    get_sprinted_issues,
    get_stories,
    get_versioned_issues,
    prepare_backlog_table_data,
    prepare_components_data,
    prepare_issues_table_data,
    prepare_not_finished_statuses_data,
    prepare_unversioned_table_data,
)
from .utils.tabs import wrap_with_tabs
from .utils.tags import H2, Div, Section

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
formatter = Formatter(fmt="[%(asctime)s: %(levelname)s] %(message)s")

handler.setFormatter(formatter)
logger.addHandler(handler)


def get_paginated_issues_for_sprint(
    project_key: str,
    jira_client: JIRA,
    sprint: jira.resources.Sprint,
    fields: list = JIRA_FETCH_FIELDS,
) -> list[dict[str, typing.Any]]:
    """Get list of issues for project sprint."""
    jql_str = (
        f"project={project_key} "
        f"AND sprint={sprint.id} "
        f"ORDER BY created DESC"
    )
    issues = jira_client.search_issues(
        jql_str,
        startAt=0,
        maxResults=False,
        fields=fields,
    )
    return [
        {"issue_id": issue.id, "sprint": sprint}
        for issue in issues
    ]


def get_board_issues_data(
    jira_client: JIRA,
    project_key: str,
    board: jira.resources.Board,
) -> dict[str, list | dict]:
    """Get issues for board with info about sprints."""
    logger.info(f"Collect sprints for Board {board.id}")

    try:
        sprints = jira_client.sprints(board_id=board.id, maxResults=False)
    except Exception as e:
        logger.debug(e)
        sprints = []

    sprints.sort(
        key=lambda x: getattr(
            x,
            "startDate",
            # required for correct ordering of future sprints
            # without start date
            str(datetime.now().isoformat()),
        ),
    )

    logger.info(f"Collected {len(sprints)} sprints(s)")

    with ThreadPoolExecutor(max_workers=MAX_THREADS_COUNT) as executor:
        issues_for_sprint_func = functools.partial(
            get_paginated_issues_for_sprint,
            project_key,
            jira_client,
        )
        issues_result_lists = executor.map(issues_for_sprint_func, sprints)
        issues_data = itertools.chain(*issues_result_lists)

    return {
        "board": {
            "board": board,
            "sprints": sprints,
        },
        "issues": {
            issue_data["issue_id"]: {
                "board": board,
                "sprint": issue_data["sprint"],
            }
            for issue_data in issues_data
        },
    }


def get_extra_data(
    jira_client: JIRA,
    project_key: str,
) -> dict[str, list | dict]:
    """Get boards and issues data."""
    logger.info(f"Connect to Jira ({project_key})")

    boards = jira_client.boards(projectKeyOrID=project_key)

    logger.info(f"Collected {len(boards)} board(s)")

    with ThreadPoolExecutor(max_workers=MAX_THREADS_COUNT) as executor:
        board_issues_data_func = functools.partial(
            get_board_issues_data,
            jira_client,
            project_key,
        )
        results = list(executor.map(board_issues_data_func, boards))
    return {
        "boards": [result["board"] for result in results],
        "issues": dict(
            collections.ChainMap(*[result["issues"] for result in results]),
        ),
    }


def get_data(jira_client: JIRA, project_key: str) -> dict[str, list]:
    """Get all project issues and versions."""
    logger.info(f"Connect to Jira ({project_key})")

    issues = jira_client.search_issues(
        f"project={project_key} ORDER BY created DESC",
        startAt=0,
        maxResults=False,
        fields=JIRA_FETCH_FIELDS,
    )

    logger.info("Get versions")

    # get not archived release versions
    versions = [
        version for version in jira_client.project_versions(project_key)
        if not version.archived
    ]
    versions.sort(key=lambda x: getattr(x, "startDate", ""))

    return {
        "versions": versions,
        "issues": issues,
    }


def construct_tables(
    issues_dataframe: DataFrame,
    versions: list,
    boards: list,
) -> list[Section | Div]:
    """Construct tables from data."""
    VERSIONS_TAB_ID = 1
    EMPTY_TAB_CONTENT = "No data."

    versioned_df = get_versioned_issues(issues_dataframe)
    unversioned_df = prepare_unversioned_table_data(issues_dataframe)
    sprinted_df = get_sprinted_issues(issues_dataframe)
    backlog_df = prepare_backlog_table_data(issues_dataframe)
    tables = []
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
    tabs_header: list[tuple[str, int]] = [
        ("Versions", VERSIONS_TAB_ID),
    ]
    for board in boards:
        if board["sprints"]:
            tabs_header.append((
                board["board"].name,
                board["board"].id,
            ))

    # prepare tabs content
    tabs_content: list[tuple[str, int]] = []

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
        for component in prepare_components_data(versioned_df):
            version_sections.append(Section(
                H2(component),
                generate_issues_table(
                    prepare_issues_table_data(versioned_df, component),
                    versions,
                    component_id=component.id,
                    **{"class": "component"},
                ),
            ))

        # unversioned issues table
        if not unversioned_df.empty:
            logger.info("Generate Unversioned Issues table")
            version_sections.append(Section(
                H2("Unversioned"),
                generate_unversioned_table(
                    unversioned_df,
                    **{"class": "backlog"},
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
            for component in prepare_components_data(sprinted_df):
                component_issues_df = prepare_issues_table_data(
                    sprinted_df,
                    component,
                )

                if component_issues_df.empty:
                    continue

                board_sections.append(Section(
                    H2(component),
                    generate_board_table(
                        component_issues_df,
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
    epics_dataframe = get_epics(issues_dataframe)
    if not epics_dataframe.empty:
        logger.info("Generate Epics table")
        tables.append(Section(
            H2("Epics"),
            generate_epics_table(
                issues_dataframe,
                epics_dataframe,
                **{"class": "epics"},
            ),
        ))

    # stories table
    stories_dataframe = get_stories(issues_dataframe)
    if not stories_dataframe.empty:
        logger.info("Generate Stories table")
        tables.append(Section(
            H2("Stories"),
            generate_stories_table(
                issues_dataframe,
                stories_dataframe,
                **{"class": "stories"},
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


def get_tables(
    jira_client: JIRA,
    jira_project_key: str,
    jira_server_url: str,
) -> list[Section | Div]:
    """Get tables."""
    data = get_data(jira_client, jira_project_key)
    extra_data = get_extra_data(jira_client, jira_project_key)

    logger.info("Prepare Pandas dataframe")
    dataframe = get_dataframe(
        data["issues"],
        extra_data["issues"],
        jira_server_url,
    )

    return construct_tables(
        dataframe,
        data["versions"],
        extra_data["boards"],
    )
