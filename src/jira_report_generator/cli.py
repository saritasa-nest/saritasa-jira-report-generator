import argparse
import logging
import os
import sys

from decouple import config
from jinja2 import Environment, FileSystemLoader
from jira import JIRA

from .app import get_tables
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
    action='store_true',
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

    write_tables(
        get_tables(
            jira_client,
            cli_args.key,
            SERVER_URL,
        ),
        cli_args.output,
        cli_args.key,
    )


if __name__ == "__main__":
    main()
