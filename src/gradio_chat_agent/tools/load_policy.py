"""Utility script to load policy YAML into the database."""

import argparse
import os

import yaml

from gradio_chat_agent.persistence.sql_repository import SQLStateRepository


def load_policy(file_path: str, project_id: str, db_url: str):
    with open(file_path, "r") as f:
        policy = yaml.safe_load(f)

    repo = SQLStateRepository(db_url)
    repo.set_project_limits(project_id, policy)
    print(f"Loaded policy for project {project_id} from {file_path}")


if __name__ == "__main__":
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
        default=os.environ.get("DATABASE_URL", "sqlite:///gradio_chat_agent.sqlite3"),
        help="Database connection URL",
    )
    args = parser.parse_args()

    load_policy(args.file_path, args.project_id, args.db_url)
