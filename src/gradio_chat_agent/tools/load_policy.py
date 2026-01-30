"""Utility script to load policy YAML into the database."""

import argparse
import os

import yaml

from gradio_chat_agent.observability.logging import get_logger, setup_logging
from gradio_chat_agent.persistence.sql_repository import SQLStateRepository


logger = get_logger(__name__)


def load_policy(file_path: str, project_id: str, db_url: str):
    """Loads a governance policy from a YAML file into the database.

    This function reads the specified YAML file, parses its content as a
    governance policy, and persists it for the given project using the
    SQLStateRepository.

    Args:
        file_path: The path to the YAML file containing the policy definition.
        project_id: The unique identifier for the project to apply the policy to.
        db_url: The SQLAlchemy database connection string.
    """
    with open(file_path, "r") as f:
        policy = yaml.safe_load(f)

    repo = SQLStateRepository(db_url)
    repo.set_project_limits(project_id, policy)
    logger.info(f"Loaded policy for project {project_id} from {file_path}")


if __name__ == "__main__":
    setup_logging()
    parser = argparse.ArgumentParser(
        description="Load a policy YAML file into the database."
    )
    parser.add_argument("file_path", help="Path to policy YAML")
    parser.add_argument(
        "--project-id",
        default="default_project",
        help="Target project ID (default: default_project)",
    )
    parser.add_argument(
        "--db-url",
        default=os.environ.get(
            "DATABASE_URL", "sqlite:///gradio_chat_agent.sqlite3"
        ),
        help="Database connection URL",
    )
    args = parser.parse_args()

    load_policy(args.file_path, args.project_id, args.db_url)
