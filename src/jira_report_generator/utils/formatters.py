from contextlib import suppress
from datetime import datetime, timezone
import math
from urllib.parse import urljoin

from dateutil.parser import isoparse
from ..constants import Status


def format_name(name: str) -> str:
    """Format name

    Turns "User Local Host" into "User L. H.".

    """
    name_list = name.split()

    return " ".join([
        name_list[0] if name_list else "",
        *[f"{s[0]}." for s in name_list[1:] if s],
    ])


def format_to_qa_count_badge(
    issue,
) -> str:
    """Render QA count badge."""
    to_qa_count = getattr(issue, "to_qa_count", 0) or 0
    if issue.status.name in Status.IN_QA.value and to_qa_count >= 2:
        return _format_status_badge(
            str(to_qa_count),
            extra_styles={
                "background": "darkorange",
                "top": "1px",
            },
        )

    return ""


def format_last_status_change_badge(
    issue,
) -> str:
    """Render last status change duration badge."""
    if issue.status.name not in (
        *Status.CODE_REVIEW.value,
        *Status.IN_QA.value,
    ):
        return ""
    last_status_change_time = getattr(
        issue,
        "last_status_change_time",
        None,
    )
    if not last_status_change_time:
        return ""
    if isinstance(last_status_change_time, float) and math.isnan(
        last_status_change_time,
    ):
        return ""
    try:
        import pandas as pd
        if pd.isna(last_status_change_time):
            return ""
    except Exception:
        pass
    if isinstance(last_status_change_time, str):
        try:
            last_status_change_time = isoparse(last_status_change_time)
        except Exception:
            return ""
    if isinstance(last_status_change_time, datetime):
        if last_status_change_time.tzinfo is None:
            last_status_change_time = last_status_change_time.replace(
                tzinfo=timezone.utc,
            )
        now = datetime.now(timezone.utc)
        elapsed_seconds = int(
            (now - last_status_change_time).total_seconds(),
        )
        elapsed_seconds = max(0, elapsed_seconds)
        if elapsed_seconds <= 24 * 3600:
            return ""
        last_status_change_duration = format_duration_days_hours(
            elapsed_seconds,
        )
        return _format_status_badge(
            last_status_change_duration,
            extra_styles={
                "background": "red",
                "bottom": "1px",
            },
        )

    return ""


def format_status_badges(issue) -> str:
    """Render QA count and status time passed badges."""
    status_badges = []
    qa_badge = format_to_qa_count_badge(issue)
    time_passed_badge = format_last_status_change_badge(issue)
    if qa_badge:
        status_badges.append(qa_badge)
    if time_passed_badge:
        status_badges.append(time_passed_badge)

    return "".join(status_badges)


def _format_status_badge(
    value: str,
    extra_styles: dict | None = None,
) -> str:
    """Formate status badge."""
    styles = {
        "line-height": "7px",
        "display": "inline-block",
        "padding": "1px 2px",
        "color": "white",
        "position": "absolute",
        "right": "1px",
        "font-size": "8px !important",
        "border-radius": "2px",
    }
    if extra_styles:
        styles.update(extra_styles)
    badge_style = " ".join(
        f"{attribute}: {value};" for attribute, value in styles.items()
    )
    return f"<span style=\"{badge_style}\">{value}</span>"


def get_issue_permalink(
        jira_server_url: str,
        issue_key: str,
) -> str:
    """Returns URL for browse issue details."""
    return urljoin(jira_server_url, f"browse/{issue_key}")


def get_version_permalink(
        jira_server_url: str,
        project_key: str,
        version_id: int,
) -> str:
    """Returns URL for browse version details."""
    return urljoin(
        jira_server_url,
        f"projects/{project_key}/versions/"
        f"{version_id}/tab/release-report-all-issues",
    )


def get_short_date(variable, input_format="%Y-%m-%d") -> str:
    """Returns date in short format like 12/31/2025."""
    result = ""

    with suppress(Exception):
        date_obj = datetime.strptime(variable, input_format)
        result = date_obj.strftime("%-m/%-d/%Y")

    return result


def get_full_date(variable, input_format="%Y-%m-%d") -> str:
    """Returns date in full format like December 31, 2025."""
    result = ""

    with suppress(Exception):
        date_obj = datetime.strptime(variable, input_format)
        result = date_obj.strftime("%B %-d, %Y")

    return result


def format_duration_days_hours(seconds: int) -> str:
    """Format the given amount of seconds to duration like 1d2h."""
    if seconds <= 0:
        return "0h"

    day_part = seconds // 86400
    hour_part = (seconds % 86400) // 3600

    parts = []
    if day_part > 0:
        parts.append(f"{day_part}d")
    if hour_part > 0:
        parts.append(f"{hour_part}h")

    return " ".join(parts)
