import datetime
from typing import Any

from jinja2 import Template
from jira import Issue
from jira.resources import Board
from pandas import DataFrame

from ..constants import Status, Type
from .formatters import get_issue_permalink
from .tags import Table


def get_dataframe(
        data: list[Issue],
        extra_data: dict[int, dict],
        jira_server_url: str,
) -> DataFrame:
    """Construct dataframe from fetched data."""
    result = []

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
        extra = extra_data.get(item.id, {})
        boards = extra.get("boards", None)
        sprint = extra.get("sprint", None)

        item_permalink = get_issue_permalink(
            jira_server_url,
            item.key,
        )

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
            "link": item_permalink,
            "type": item.fields.issuetype,
            "parent": getattr(item.fields, "parent", None),
            "release_date": release_date[0] if release_date else None,
            "sprint_date": getattr(sprint, "endDate", "") if sprint else None,
            "boards_ids": [board.id for board in boards] if boards else [],
            "sprint_id": sprint.id if sprint else None,
        })

    return DataFrame(result)


def get_versioned_issues(
        df: DataFrame,
        versions: list,
) -> DataFrame:
    """Get versioned issues."""
    version_ids = [v.id for v in versions]

    return df[df["versions"].apply(
        lambda x: any([not getattr(v, "archived", False) for v in x])
            and any([v.id in version_ids for v in x]),
    )]


def get_sprinted_issues(df: DataFrame) -> DataFrame:
    """Get sprinted issues."""
    return df[df["sprint_id"].notna()]


def render_template(
    tables: list[Table],
    title: str,
    template: Template,
) -> str:
    """Render template."""
    sections = map(str, tables)

    return template.render(
        title=title,
        sections=sections,
    )


def prepare_components_data(issues_dataframe: DataFrame):
    """Prepare components data for usage."""
    components = issues_dataframe.components.explode().dropna()

    return sorted(list(filter(
        lambda x: hasattr(x, "name"),
        components.unique().tolist(),
    )), key=lambda x: x.id)


def prepare_not_finished_statuses_data(df: DataFrame):
    """Prepare statuses data for usage."""
    # collect used statuses
    statuses = df.status.explode().unique().tolist()

    # not finished statuses
    return list(filter(lambda x: x.name in (
        *Status.IN_PROGRESS.value,
        *Status.READY_FOR_DEVELOPMENT.value,
    ), statuses))


def filter_data_by_statuses(df: DataFrame, statuses: list) -> DataFrame:
    """Prepare data filtered by statuses."""

    if df.empty:
        return df

    components = prepare_components_data(df)

    # only with components
    issues_with_components_df = df[df["components"].apply(
        lambda x: len(x) > 0 and set(x).issubset(components),
    )]

    # return empty dataframe
    if not statuses:
        return DataFrame()

    # filter by statuses
    return issues_with_components_df[
        issues_with_components_df["status"].apply(
            lambda x: x in statuses
        )
    ]


def prepare_issues_table_data(
    issues_dataframe: DataFrame,
    component: Any,
) -> DataFrame:
    """Prepare initial data for issues table rendering."""
    return issues_dataframe[issues_dataframe["components"].apply(
        lambda x: component in x,
    )]


def filter_unclassified_issues(df: DataFrame) -> DataFrame:
    """Returns unclassified issues."""
    to_skip_versions = (
        *Status.BACKLOG.value,
        *Status.CANCELLED.value,
        *Status.VERIFIED.value,
        *Status.COMPLETED.value,
        *Status.INTERNAL.value,
    )

    df = df[df["components"].apply(
        lambda x: len(x) == 0,
    )]

    if (df.empty):
        return df

    df = df[df["type"].apply(
        lambda x: x.name not in [
            Type.EPIC.value,
            Type.STORY.value,
        ]
    )]

    if (df.empty):
        return df

    return df[df["status"].apply(
        lambda x: x.name not in to_skip_versions,
    )]


def filter_internal_issues(df: DataFrame) -> DataFrame:
    """Returns issues with status Internal."""
    return df[df["status"].apply(
        lambda x: x.name in Status.INTERNAL.value,
    )]


def prepare_backlog_table_data(df: DataFrame) -> DataFrame:
    """Prepare initial data for backlog table rendering."""
    return df[df["status"].apply(
        lambda x: x.name in Status.BACKLOG.value,
    )]


def prepare_unversioned_table_data(df: DataFrame) -> DataFrame:
    """Prepare initial data for unversioned issues table rendering."""
    to_skip_versions = (
        *Status.BACKLOG.value,
    )
    df = df[df["status"].apply(lambda x: x.name not in to_skip_versions)]
    df = df[df["type"].apply(
        lambda x: x.name not in [
            Type.EPIC.value,
            Type.STORY.value,
        ]
    )]

    return df[df["versions"].apply(lambda x: len(x) == 0)]


def prepare_cancelled_table_data(df: DataFrame) -> DataFrame:
    """Prepare data for cancelled issues table rendering."""
    return df[df["status"].apply(
        lambda x: x.name in Status.CANCELLED.value,
    )]


def get_epics(df: DataFrame) -> DataFrame:
    """Returns a dataframe of issues type Epic"""

    if df.empty:
        return df

    return df[df["type"].apply(
        lambda x: x.name == Type.EPIC.value,
    )]


def get_stories(df: DataFrame) -> DataFrame:
    """Returns a dataframe of issues type Story"""

    if df.empty:
        return df

    return df[df["type"].apply(
        lambda x: x.name == Type.STORY.value,
    )]


def filter_by_board(df: DataFrame, board: Board) -> DataFrame:
    """Filter issues by board"""
    board_id = getattr(board, "id", None)

    if df.empty or not board_id:
        return df

    return df[df["boards_ids"].apply(
        lambda x: board_id in x,
    )]


def is_task_latest_version(
    version,
    task_versions,
):
    """Check if the version is considered latest version of a task."""
    return version == sorted(
        task_versions,
        key=lambda v: (
            datetime.date.fromisoformat(v.releaseDate) if hasattr(v, "releaseDate") else datetime.date.min,
            datetime.date.fromisoformat(v.startDate) if hasattr(v, "startDate") else datetime.date.min,
            v.id,
        ),
    )[-1]
