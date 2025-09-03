import argparse
import datetime
import logging
import os
import sys
from collections import Counter

from decouple import config
from jinja2 import Environment, FileSystemLoader
from jira import JIRA

from .app import (
    get_issue_assignee_changelog,
    get_issue_status_changelog,
    get_issue_worklogs,
    get_tables,
)
from .constants import Status
from .utils.data import render_template
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
    action="store_true",
)
parser.add_argument(
    "--from-date",
    type=datetime.date.fromisoformat,
    default=None,
    help="from date",
)
parser.add_argument(
    "--to-date",
    type=datetime.date.fromisoformat,
    default=None,
    help="to date",
)

env = Environment(
    loader=FileSystemLoader(
        os.path.join(os.path.dirname(__file__), "static"),
    ),
)

logger = logging.getLogger(__name__)
handler = logging.StreamHandler(stream=sys.stdout)
formatter = logging.Formatter(fmt='[%(asctime)s: %(levelname)s] %(message)s')

handler.setFormatter(formatter)
logger.addHandler(handler)


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


def print_issue_status_stat(jira_client: JIRA, issue_id: str):
    """Print list of status transitions with counter."""
    transitions = get_issue_status_changelog(jira_client, issue_id)
    data = Counter([f"{t["from"]} -> {t["to"]}" for t in transitions])

    for transition in sorted(data.items(), key=lambda x: x[1], reverse=True):
        print(transition[0], f"({transition[1]})")


def print_issue_status_transitions(jira_client: JIRA, issue_id: str):
    """Print list of status transitions."""
    transitions = get_issue_status_changelog(jira_client, issue_id)

    for transition in transitions[::-1]:
        print(
            f"{transition["created"]} "
            f"{transition["from"]} -> {transition["to"]} "
            f"({transition["author"]})"
        )


def print_issue_worklogs(jira_client: JIRA, issue_id: str):
    """Print list of issue worklogs."""
    worklogs = get_issue_worklogs(jira_client, issue_id)

    for worklog in worklogs:
        print(
            f"{worklog["created"]} "
            f"{worklog["author"]} "
            f"{worklog["spent"]}"
        )


def print_issue_assignee_transitions(jira_client: JIRA, issue_id: str):
    """Print list of assignee transitions."""
    transitions = get_issue_assignee_changelog(jira_client, issue_id)

    for transition in transitions[::-1]:
        print(
            f"{transition["created"]} "
            f"{transition["from"]} -> {transition["to"]} "
            f"({transition["author"]})"
        )


def main():
    cli_args = parser.parse_args()
    jira_client = JIRA(
        server=SERVER_URL,
        basic_auth=(EMAIL, API_TOKEN),
        async_=True,
        async_workers=4,
    )

    if cli_args.verbose:
        logger.setLevel(logging.INFO)

    if "-" in cli_args.key:
        print_issue_status_transitions(jira_client, cli_args.key)
        print("---")
        print_issue_status_stat(jira_client, cli_args.key)
        print("---")
        print_issue_worklogs(jira_client, cli_args.key)
        print("---")
        print_issue_assignee_transitions(jira_client, cli_args.key)
        return

    write_tables(
        get_tables(
            jira_client,
            cli_args.key,
            SERVER_URL,
            from_date=cli_args.from_date,
            to_date=cli_args.to_date,
        ),
        cli_args.output,
        cli_args.key,
    )


if __name__ == "__main__":
    main()
