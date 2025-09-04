import collections
import functools
import itertools
import logging
import os
import sys
import typing
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import partial
from logging import Formatter, StreamHandler

import jira.resources
from dateutil.parser import isoparse
from jinja2 import Environment, FileSystemLoader
from jira import JIRA
from pandas import DataFrame

from .constants import JIRA_FETCH_FIELDS, MAX_THREADS_COUNT
from .tables.assignees import generate_assignees_table
from .tables.backlog import generate_backlog_table
from .tables.board import generate_board_table
from .tables.epics import generate_epics_table
from .tables.internal import generate_internal_table
from .tables.issues import generate_issues_table
from .tables.project import generate_project_table
from .tables.sprints import generate_sprints_table
from .tables.statuses import generate_statuses_table
from .tables.stories import generate_stories_table
from .tables.unclassified import generate_unclassified_table
from .tables.versions import generate_versions_table
from .tables.cancelled import generate_cancelled_table
from .utils.data import (
    filter_by_board,
    filter_data_by_statuses,
    filter_internal_issues,
    filter_unclassified_issues,
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
    prepare_cancelled_table_data,
)
from .utils.formatters import get_version_permalink
from .utils.tabs import wrap_with_tabs
from .utils.tags import H2, Div, Section

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

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


def get_issues_by_sprint(
    project_key: str,
    jira_client: JIRA,
    from_date: str,
    to_date: str,
    sprint: jira.resources.Sprint,
    fields: list = JIRA_FETCH_FIELDS,
) -> list[dict[str, typing.Any]]:
    """Get list of issues for project sprint."""
    jql_str = f"project={project_key} AND sprint={sprint.id}"

    if from_date:
        jql_str = f"{jql_str} AND createdDate>={from_date}"

    if to_date:
        jql_str = f"{jql_str} AND createdDate<={to_date}"

    issues = jira_client.search_issues(
        jql_str=f"{jql_str} ORDER BY created DESC",
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
    from_date: str,
    to_date: str,
    board: jira.resources.Board,
) -> dict[str, list | dict]:
    """Get issues for board with info about sprints."""
    logger.info(f"Collect sprints for Board {board.id}")

    try:
        sprints = jira_client.sprints(board_id=board.id, maxResults=False)
    except Exception as e:
        logger.debug(e)
        sprints = []

    if from_date:
        get_date = datetime.fromisoformat
        sprints = [
            sprint
            for sprint
            in sprints
            if sprint.startDate
            and get_date(sprint.startDate).date() >= from_date
        ]

        if to_date:
            sprints = [
                sprint
                for sprint
                in sprints
                if sprint.endDate
                and get_date(sprint.endDate).date() <= to_date
            ]

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
            get_issues_by_sprint,
            project_key,
            jira_client,
            from_date,
            to_date,
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
    jira_server_url: str,
    from_date: str = None,
    to_date: str = None,
) -> dict[str, list | dict]:
    """Get boards and issues data."""
    logger.info(f"Connect to Jira ({project_key})")

    boards = jira_client.boards(projectKeyOrID=project_key)
    issues = {}

    logger.info(f"Collected {len(boards)} board(s)")

    with ThreadPoolExecutor(max_workers=MAX_THREADS_COUNT) as executor:
        board_issues_data_func = functools.partial(
            get_board_issues_data,
            jira_client,
            project_key,
            from_date,
            to_date,
        )
        results = list(executor.map(board_issues_data_func, boards))

    for result in results:
        for issue_id, data in result["issues"].items():
            if issue_id in issues:
                issues[issue_id]["boards"].append(data["board"])
                continue
            issues[issue_id] = {
                "boards": [data["board"]],
                "sprint": data["sprint"],
            }

    return {
        "boards": [result["board"] for result in results],
        "issues": issues,
    }


def get_data(
        jira_client: JIRA,
        project_key: str,
        jira_server_url: str,
        from_date: str = None,
        to_date: str = None,
) -> dict[str, list]:
    """Get all project issues and versions."""
    logger.info(f"Connect to Jira ({project_key})")

    jql_str = f"project={project_key}"

    if from_date:
        jql_str = f"{jql_str} and createdDate>={from_date}"

    if to_date:
        jql_str = f"{jql_str} and createdDate<={to_date}"

    issues = jira_client.search_issues(
        jql_str=f"{jql_str} ORDER BY created DESC",
        startAt=0,
        maxResults=False,
        fields=JIRA_FETCH_FIELDS,
    )

    logger.info("Get versions")

    # get not archived release versions
    versions = [
        version
        for version
        in jira_client.project_versions(project_key)
        if not version.archived
    ]

    if from_date:
        versions = [
            version
            for version
            in versions
            if getattr(version, "startDate", None)
            and datetime.fromisoformat(
                getattr(version, "startDate", None)
            ).date() >= from_date
        ]

        if to_date:
            versions = [
                version
                for version
                in versions
                if getattr(version, "releaseDate", None)
                and datetime.fromisoformat(
                    getattr(version, "releaseDate", None)
                ).date() <= to_date
            ]

    for version in versions:
        setattr(
            version,
            "permalink",
            get_version_permalink(
                jira_server_url,
                project_key,
                version.id,
            )
        )

    versions.sort(key=lambda x: getattr(x, "releaseDate", ""))

    return {
        "versions": versions,
        "issues": issues,
    }


def construct_tables(
    issues_dataframe: DataFrame,
    versions: list,
    boards: list,
    show_sprint_limit_column: bool = True,
    show_project_budget_column: bool = True,
) -> list[Section | Div]:
    """Construct tables from data."""
    VERSIONS_TAB_ID = 1
    EMPTY_TAB_CONTENT = "No data."

    tables = []

    if issues_dataframe.empty:
        return tables

    versioned_df = get_versioned_issues(issues_dataframe, versions)
    unversioned_df = prepare_unversioned_table_data(issues_dataframe)
    sprinted_df = get_sprinted_issues(issues_dataframe)
    unclassified_df = filter_unclassified_issues(issues_dataframe)
    internal_df = filter_internal_issues(issues_dataframe)
    backlog_df = prepare_backlog_table_data(issues_dataframe)
    cancelled_df = prepare_cancelled_table_data(issues_dataframe)
    not_finished_statuses = prepare_not_finished_statuses_data(
        versioned_df,
    )

    # project table
    if not versioned_df.empty:
        logger.info("Generate Project table")
        tables.append(Section(
            H2("Project"),
            generate_project_table(
                versioned_df,
                internal_df,
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

        # version component tables
        logger.info("Generate Component tables")
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
        board_issues_df = filter_by_board(sprinted_df, board["board"])
        if board["sprints"] and not board_issues_df.empty:
            board_sections = []
            logger.info("Generate Sprints table")
            board_sections.append(Section(
                H2("Sprints"),
                generate_sprints_table(
                    board_issues_df,
                    board["sprints"],
                    show_sprint_limit_column=show_sprint_limit_column,
                    show_project_budget_column=show_project_budget_column,
                    **{"class": "sprints"},
                ),
            ))

            # board component tables
            logger.info("Generate Component tables")
            for component in prepare_components_data(board_issues_df):
                component_issues_df = prepare_issues_table_data(
                    board_issues_df,
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
            H2("Epics", **{
                "id": "epics",
                "class": "table-title",
            }),
            generate_epics_table(
                issues_dataframe,
                epics_dataframe,
                **{"class": "epics hidden"},
            ),
        ))

    # stories table
    stories_dataframe = get_stories(issues_dataframe)
    if not stories_dataframe.empty:
        logger.info("Generate Stories table")
        tables.append(Section(
            H2("Stories", **{
                "id": "stories",
                "class": "table-title",
            }),
            generate_stories_table(
                issues_dataframe,
                stories_dataframe,
                **{"class": "stories hidden"},
            ),
        ))

    # internal tasks
    if not internal_df.empty:
        logger.info("Generate Internal table")
        tables.append(Section(
            H2("Internal", **{
                "id": "internal",
                "class": "table-title",
            }),
            generate_internal_table(
                internal_df,
                **{"class": "internal hidden"},
            )
        ))

    # issues without components
    if not unclassified_df.empty:
        logger.info("Generate Unclassified table")
        tables.append(Section(
            H2("Unclassified", **{
                "id": "unclassified",
                "class": "table-title",
            }),
            generate_unclassified_table(
                unclassified_df,
                **{"class": "unclassified hidden"},
            )
        ))

    # backlog table
    if not backlog_df.empty:
        logger.info("Generate Backlog table")
        tables.append(Section(
            H2("Backlog", **{
                "id": "backlog",
                "class": "table-title",
            }),
            generate_backlog_table(
                backlog_df,
                **{"class": "backlog hidden"},
            ),
        ))

    # backlog table
    if not cancelled_df.empty:
        logger.info("Generate Cancelled table")
        tables.append(Section(
            H2("Cancelled", **{
                "id": "cancelled",
                "class": "table-title",
            }),
            generate_cancelled_table(
                cancelled_df,
                **{"class": "cancelled hidden"},
            ),
        ))

    return tables


def get_tables(
    jira_client: JIRA,
    jira_project_key: str,
    jira_server_url: str,
    show_sprint_limit_column: bool = True,
    show_project_budget_column: bool = True,
    from_date: str = None,
    to_date: str = None,
) -> list[Section | Div]:
    """Get tables."""
    arguments = (
        jira_client,
        jira_project_key,
        jira_server_url,
        from_date,
        to_date,
    )
    data = get_data(*arguments)
    extra_data = get_extra_data(*arguments)

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
        show_sprint_limit_column=show_sprint_limit_column,
        show_project_budget_column=show_project_budget_column,
    )


def get_issue_worklogs(
        jira_client: JIRA,
        issue_id: str,
) -> list[dict[str, str]]:
    """Get issue worklogs."""
    worklogs = jira_client.worklogs(issue_id)

    return [{
        "created": isoparse(wl.created).strftime(DATE_FORMAT),
        "author": wl.author.displayName,
        "spent": wl.timeSpent,
    } for wl in worklogs]


def get_issue_field_changelog(
        jira_client: JIRA,
        issue_id: str,
        field_name: str,
) -> list[dict[str, str]]:
    """Get issue field changelog."""
    issue = jira_client.issue(issue_id, expand="changelog")
    transitions = []

    for history in issue.changelog.histories:
        for item in history.items:
            if item.field == field_name:
                transitions.append({
                    "from": item.fromString,
                    "to": item.toString,
                    "author": history.author,
                    "created": isoparse(
                        history.created
                    ).strftime(DATE_FORMAT),
                })

    return transitions


get_issue_status_changelog = partial(
    get_issue_field_changelog,
    field_name="status",
)


get_issue_assignee_changelog = partial(
    get_issue_field_changelog,
    field_name="assignee",
)
