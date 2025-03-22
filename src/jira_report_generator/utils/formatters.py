from contextlib import suppress
from datetime import datetime
from urllib.parse import urljoin


def format_name(name: str) -> str:
    """Format name

    Turns "User Local Host" into "User L. H.".

    """
    name_list = name.split()

    return " ".join([
        name_list[0] if name_list else "",
        *[f"{s[0]}." for s in name_list[1:] if s],
    ])


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
