from typing import Any

from jinja2 import Template
from jira import Issue
from pandas import DataFrame

from ..constants import Status, Type
from .tags import Table
from .formatters import get_issue_permalink


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
        board = extra.get("board", None)
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
            "board_id": board.id if board else None,
            "sprint_id": sprint.id if sprint else None,
        })

    return DataFrame(result)


def get_versioned_issues(df: DataFrame) -> DataFrame:
    return df[df["versions"].apply(
        lambda x: any([not getattr(v, "archived", False) for v in x])
    )].sort_values(
        by=["release_date", "id"],
    )


def get_sprinted_issues(df: DataFrame) -> DataFrame:
    return df[df["sprint_id"].notna()].sort_values(
        by=["sprint_date", "id"],
    )


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
        components.unique().tolist()
    )), key=lambda x: x.id)


def prepare_not_finished_statuses_data(issues_dataframe: DataFrame):
    """Prepare statuses data for usage."""
    # collect used statuses
    statuses = issues_dataframe.status.explode().unique().tolist()

    # not finished statuses
    return list(filter(lambda x: x.name in (
        Status.IN_PROGRESS.value,
        Status.READY_FOR_DEVELOPMENT.value,
    ), statuses))


def filter_data_by_statuses(
        issues_df: DataFrame,
        statuses: list,
) -> DataFrame:
    """Prepare data filtered by statuses."""
    components = prepare_components_data(issues_df)

    # only with components
    issues_with_components_df = issues_df[issues_df["components"].apply(
        lambda x: len(x) > 0 and set(x).issubset(components),
    )]

    # filter by statuses
    return issues_with_components_df[
        issues_with_components_df["status"].apply(lambda x: x in statuses)
    ]


def prepare_issues_table_data(
    issues_dataframe: DataFrame,
    component: Any,
) -> DataFrame:
    """Prepare initial data for issues table rendering."""
    return issues_dataframe[issues_dataframe["components"].apply(
        lambda x: component in x
    )]


def prepare_backlog_table_data(issues_dataframe: DataFrame) -> DataFrame:
    """Prepare initial data for backlog table rendering."""
    return issues_dataframe[
        issues_dataframe["status"].apply(
            lambda x: x.name == Status.BACKLOG.value
        )
    ].sort_values("id")


def prepare_unversioned_table_data(issues_dataframe: DataFrame) -> DataFrame:
    """Prepare initial data for unversioned issues table rendering."""
    to_skip_versions = (
        Status.BACKLOG.value,
    )
    issues_dataframe = issues_dataframe[
        issues_dataframe["status"].apply(
            lambda x: x.name not in to_skip_versions,
        )
    ]

    return issues_dataframe[
        issues_dataframe["versions"].apply(lambda x: len(x) == 0)
    ].sort_values("id")


def get_epics(issues_dataframe: DataFrame) -> DataFrame:
    """Returns a dataframe of issues type Epic"""
    return issues_dataframe[
        issues_dataframe["type"].apply(
            lambda x: x.name == Type.EPIC.value,
        )
    ]


def get_stories(issues_dataframe: DataFrame) -> DataFrame:
    """Returns a dataframe of issues type Story"""
    return issues_dataframe[
        issues_dataframe["type"].apply(
            lambda x: x.name == Type.STORY.value,
        )
    ]
