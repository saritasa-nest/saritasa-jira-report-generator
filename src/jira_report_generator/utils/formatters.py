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
