"""Utility functions for the Gradio Chat Agent.

This module provides shared helper functions used across the application,
such as diff computation and common transformations.
"""

import os
import base64
import hashlib
import json
import mimetypes
from typing import Any, Optional

from gradio_chat_agent.models.enums import StateDiffOp
from gradio_chat_agent.models.execution_result import StateDiffEntry


class SecretManager:
    """Utility for encrypting and decrypting sensitive data."""

    def __init__(self, key: Optional[str] = None):
        """Initializes with a base64 encoded Fernet key.

        Args:
            key: Optional key. If not provided, looks for SECRET_KEY env var.
        """
        from cryptography.fernet import Fernet

        secret = key or os.environ.get("SECRET_KEY")
        if not secret:
            # Fallback for dev only
            secret = base64.urlsafe_b64encode(
                b"static-dev-key-must-be-32-bytes!!"
            )

        # Ensure key is correctly padded/formatted for Fernet
        if isinstance(secret, str):
            secret = secret.encode("utf-8")

        try:
            self.fernet = Fernet(secret)
        except Exception:
            # If key is invalid format, derive one from the string
            derived_key = base64.urlsafe_b64encode(
                hashlib.sha256(secret).digest()
            )
            self.fernet = Fernet(derived_key)

    def encrypt(self, plain_text: str) -> str:
        """Encrypts a string."""
        return self.fernet.encrypt(plain_text.encode("utf-8")).decode("utf-8")

    def decrypt(self, cipher_text: str) -> str:
        """Decrypts a string."""
        return self.fernet.decrypt(cipher_text.encode("utf-8")).decode("utf-8")


def hash_password(password: str) -> str:
    """Simple SHA256 hashing for demonstration purposes.

    In production, use a dedicated library like bcrypt or argon2.
    """
    return hashlib.sha256(password.encode()).hexdigest()


def compute_checksum(components: dict[str, Any]) -> str:
    """Computes a deterministic SHA-256 hash of a components dictionary.

    Args:
        components: The components state dictionary.

    Returns:
        A hex string representing the checksum.
    """
    # Use sort_keys=True for determinism
    dump = json.dumps(components, sort_keys=True)
    return hashlib.sha256(dump.encode("utf-8")).hexdigest()


def compute_state_diff(
    old_state: dict[str, Any], new_state: dict[str, Any], path_prefix: str = ""
) -> list[StateDiffEntry]:
    """Computes a simplified diff between two state dictionaries.

    This function recursively compares two dictionaries and generates a list of
    add, remove, or replace operations required to transform old_state into
    new_state.

    Args:
        old_state: The original state dictionary.
        new_state: The new state dictionary.
        path_prefix: Internal recursion helper to build dotted paths.
            Defaults to an empty string.

    Returns:
        A list of StateDiffEntry objects describing the changes between the
        two states.
    """
    diffs = []

    all_keys = set(old_state.keys()) | set(new_state.keys())

    for key in all_keys:
        path = f"{path_prefix}.{key}" if path_prefix else key

        if key not in old_state:
            diffs.append(
                StateDiffEntry(
                    path=path, op=StateDiffOp.ADD, value=new_state[key]
                )
            )
        elif key not in new_state:
            diffs.append(
                StateDiffEntry(path=path, op=StateDiffOp.REMOVE, value=None)
            )
        elif old_state[key] != new_state[key]:
            if isinstance(old_state[key], dict) and isinstance(
                new_state[key], dict
            ):
                diffs.extend(
                    compute_state_diff(old_state[key], new_state[key], path)
                )
            else:
                diffs.append(
                    StateDiffEntry(
                        path=path, op=StateDiffOp.REPLACE, value=new_state[key]
                    )
                )

    return diffs


def encode_media(file_path: str) -> dict[str, str]:
    """Encodes a file as a base64 string for intent media.

    Args:
        file_path: Path to the local file.

    Returns:
        A dictionary with 'data' (base64 string) and 'mime_type'.
    """
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        mime_type = "application/octet-stream"

    with open(file_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")

    return {"data": data, "mime_type": mime_type}
