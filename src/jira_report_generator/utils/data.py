import collections.abc
import datetime
from typing import Any

from jinja2 import Template
from jira import Issue
from pandas import DataFrame
from dateutil.parser import isoparse

from ..constants import (
    DEVELOPMENT_ESTIMATE_FIELD_ID,
    LAST_STATUS_CHANGE_TIME_FIELD_ID,
    GroupBy,
    Status,
    TO_QA_COUNTER_FIELD_ID,
    Type,
)
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
            if getattr(item.fields, "timeoriginalestimate", None)
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
        versions = item.fields.fixVersions or []
        parent = getattr(item.fields, "parent", None)

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
            "components": getattr(item.fields, "components", None) or [],
            "labels": getattr(item.fields, "labels", None) or [],
            "estimate": estimate,
            "spent": spent,
            "ratio": (
                round(spent / estimate, 2)
                if spent and estimate
                else 0
            ),
            "versions": versions,
            "link": item_permalink,
            "type": item.fields.issuetype,
            "parent": parent,
            "release_date": release_date[0] if release_date else None,
            "sprint_date": getattr(sprint, "endDate", "") if sprint else None,
            "boards_ids": [board.id for board in boards] if boards else [],
            "sprint_id": sprint.id if sprint else None,
            "to_qa_count": int(
                float(getattr(item.fields, TO_QA_COUNTER_FIELD_ID, None) or 0),
            ) if TO_QA_COUNTER_FIELD_ID else 0,
            "last_status_change_time": get_issue_last_status_change_time(item),
            "development_estimate": float(
                getattr(item.fields, DEVELOPMENT_ESTIMATE_FIELD_ID, None) or 0
            ) if DEVELOPMENT_ESTIMATE_FIELD_ID else None,
            "version_ids": [str(version.id) for version in versions],
            "parent_id": str(parent.id) if parent else None,
        })

    dataframe = DataFrame(result)

    if dataframe.empty:
        return dataframe

    dataframe["status_name"] = dataframe["status"].apply(
        lambda x: x.name,
    )
    dataframe["type_name"] = dataframe["type"].apply(
        lambda x: x.name,
    )
    dataframe["components_len"] = dataframe["components"].apply(
        lambda x: len(x) if x else 0,
    )
    dataframe["labels_len"] = dataframe["labels"].apply(
        lambda x: len(x) if x else 0,
    )
    dataframe["has_versions"] = dataframe["versions"].apply(
        lambda x: len(x) > 0 if x else False,
    )
    dataframe["has_sprint"] = dataframe["sprint_id"].notna()

    return dataframe


def status_name_series(df: DataFrame):
    if "status_name" in df.columns:
        return df["status_name"]
    return df["status"].apply(lambda x: x.name)


def type_name_series(df: DataFrame):
    if "type_name" in df.columns:
        return df["type_name"]
    return df["type"].apply(lambda x: x.name)


def components_len_series(df: DataFrame):
    if "components_len" in df.columns:
        return df["components_len"]
    return df["components"].apply(lambda x: len(x) if x else 0)


def labels_len_series(df: DataFrame):
    if "labels_len" in df.columns:
        return df["labels_len"]
    return df["labels"].apply(lambda x: len(x) if x else 0)


def has_versions_series(df: DataFrame):
    if "has_versions" in df.columns:
        return df["has_versions"]
    return df["versions"].apply(lambda x: len(x) > 0 if x else False)


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


def filter_data_by_statuses(
    df: DataFrame,
    statuses: list,
    group_by: GroupBy = GroupBy.COMPONENT,
) -> DataFrame:
    """Prepare data filtered by statuses."""

    if df.empty:
        return df

    if group_by == GroupBy.LABEL:
        labels_len = labels_len_series(df)
        filtered_df = df[labels_len.gt(0)]
    else:
        components_len = components_len_series(df)
        # only with components
        filtered_df = df[
            components_len.gt(0)
            & df["components"].apply(
                lambda x: all(
                    hasattr(component, "name") for component in x
                ) if x else False,
            )
        ]

    # return empty dataframe
    if not statuses:
        return filtered_df.iloc[0:0]

    status_names = [
        status if isinstance(status, str) else getattr(status, "name", None)
        for status in statuses
    ]
    status_names = [status for status in status_names if status]

    if status_names:
        return filtered_df[
            status_name_series(filtered_df).isin(status_names)
        ]

    # filter by statuses (fallback for non-nameable status objects)
    return filtered_df[
        filtered_df["status"].isin(statuses)
    ]


def filter_cancelled_issues(
    issues_dataframe: DataFrame,
) -> DataFrame:
    """Returns only cancelled issues."""
    return issues_dataframe[
        status_name_series(issues_dataframe).isin(Status.CANCELLED.value)
    ]


def filter_unclassified_issues(df: DataFrame) -> DataFrame:
    """Returns unclassified issues."""
    return df[components_len_series(df).eq(0)]


def filter_internal_issues(df: DataFrame) -> DataFrame:
    """Returns issues with status Internal."""
    return df[status_name_series(df).isin(Status.INTERNAL.value)]


def prepare_backlog_table_data(df: DataFrame) -> DataFrame:
    """Prepare initial data for backlog table rendering."""
    return df[
        status_name_series(df).isin(Status.BACKLOG.value)
        & df["sprint_id"].isna()
        & ~has_versions_series(df)
        ]


def prepare_unversioned_table_data(df: DataFrame) -> DataFrame:
    """Prepare initial data for unversioned issues table rendering."""
    to_skip_versions = (
        *Status.BACKLOG.value,
    )
    df = df[~status_name_series(df).isin(to_skip_versions)]
    df = df[~type_name_series(df).isin(
        [Type.EPIC.value, Type.STORY.value]
    )]

    return df[~has_versions_series(df)]


def prepare_cancelled_table_data(df: DataFrame) -> DataFrame:
    """Prepare data for cancelled issues table rendering."""
    return df[status_name_series(df).isin(Status.CANCELLED.value)]


def get_epics(df: DataFrame) -> DataFrame:
    """Returns a dataframe of issues type Epic"""

    if df.empty:
        return df

    return df[type_name_series(df).eq(Type.EPIC.value)]


def get_stories(df: DataFrame) -> DataFrame:
    """Returns a dataframe of issues type Story"""

    if df.empty:
        return df

    return df[type_name_series(df).eq(Type.STORY.value)]


def build_index_map(
    df: DataFrame,
    column: str,
) -> dict[Any, list[int]]:
    """Build an index map for exploded list-like columns."""
    if df.empty or column not in df.columns:
        return {}

    exploded = df[column].explode().dropna()

    if exploded.empty:
        return {}

    index_map: dict[Any, list[int]] = {}
    for index, value in exploded.items():
        index_map.setdefault(value, []).append(index)

    return index_map


def build_value_index_map(
    df: DataFrame,
    column: str,
) -> dict[Any, list[int]]:
    """Build an index map for scalar columns."""
    if df.empty or column not in df.columns:
        return {}

    series = df[column].dropna()

    if series.empty:
        return {}

    index_map: dict[Any, list[int]] = {}
    for index, value in series.items():
        index_map.setdefault(value, []).append(index)

    return index_map


def build_component_combo_index_map(
    df: DataFrame,
) -> tuple[dict[tuple[str, ...], list[int]], dict[tuple[str, ...], str]]:
    """Build an index map by ordered component combinations."""
    if df.empty or "components" not in df.columns:
        return {}, {}

    index_map: dict[tuple[str, ...], list[int]] = {}
    title_map: dict[tuple[str, ...], str] = {}

    for index, components in df["components"].items():
        if not components or not isinstance(components, collections.abc.Sequence):
            continue

        concrete_components = [
            component for component in components if hasattr(component, "name")
        ]
        if not concrete_components or len(concrete_components) != len(components):
            continue

        component_ids = []
        component_names = []
        for component in concrete_components:
            component_id = getattr(component, "id", None)
            component_name = getattr(component, "name", None)
            if component_id is None or component_name is None:
                component_ids = []
                break
            component_ids.append(str(component_id))
            component_names.append(component_name)

        if not component_ids:
            continue
        component_ids_tuple = tuple(component_ids)

        index_map.setdefault(component_ids_tuple, []).append(index)

        if component_ids_tuple not in title_map:
            title_map[component_ids_tuple] = " + ".join(component_names)

    return index_map, title_map


def build_component_combo_id(component_ids: tuple[str, ...]) -> str:
    """Build a stable component combination id for HTML usage."""
    return (
        component_ids[0]
        if len(component_ids) == 1
        else "-".join(component_ids)
    )


def build_label_combo_index_map(
    df: DataFrame,
) -> tuple[dict[tuple[str, ...], list[int]], dict[tuple[str, ...], str]]:
    """Build an index map by ordered label combinations."""
    if df.empty or "labels" not in df.columns:
        return {}, {}

    index_map: dict[tuple[str, ...], list[int]] = {}
    title_map: dict[tuple[str, ...], str] = {}

    for index, labels in df["labels"].items():
        if not labels or not isinstance(labels, (list, tuple)):
            continue

        sorted_labels = sorted(labels)
        labels_tuple = tuple(sorted_labels)

        index_map.setdefault(labels_tuple, []).append(index)

        if labels_tuple not in title_map:
            title_map[labels_tuple] = " + ".join(sorted_labels)

    return index_map, title_map


def build_label_combo_id(label_names: tuple[str, ...]) -> str:
    """Build a stable label combination id for HTML usage."""
    return (
        f"label-{label_names[0]}"
        if len(label_names) == 1
        else "label-" + "-".join(label_names)
    )


def filter_unlabeled_issues(df: DataFrame) -> DataFrame:
    """Returns issues without labels."""
    return df[labels_len_series(df).eq(0)]


def is_task_version(
    version,
    task_versions,
) -> bool:
    """Check if a task belongs to the specified version."""
    return version in task_versions


def get_issue_last_status_change_time(issue) -> datetime.datetime | None:
    """Return an issue's last status change time."""
    if not LAST_STATUS_CHANGE_TIME_FIELD_ID:
        return None
    last_status_change_raw = getattr(
        issue.fields,
        LAST_STATUS_CHANGE_TIME_FIELD_ID,
        None,
    )
    if not last_status_change_raw:
        return None

    last_status_change_time = None
    try:
        if isinstance(last_status_change_raw, str):
            last_status_change_time = isoparse(
                last_status_change_raw,
            )
        elif isinstance(
            last_status_change_raw,
            datetime.datetime,
        ):
            last_status_change_time = last_status_change_raw
        if (
            last_status_change_time
            and last_status_change_time.tzinfo is None
        ):
            return (
                last_status_change_time.replace(
                    tzinfo=datetime.timezone.utc,
                )
            )
        return last_status_change_time
    except Exception:
        return None
