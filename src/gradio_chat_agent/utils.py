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

import copy
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


def apply_state_diff(
    state: dict[str, Any], diffs: list[StateDiffEntry]
) -> dict[str, Any]:
    """Applies a list of state diff entries to a state dictionary.

    Args:
        state: The base state dictionary.
        diffs: The list of diff entries to apply.

    Returns:
        A new state dictionary with the diffs applied.
    """
    new_state = copy.deepcopy(state)

    for diff in diffs:
        path = diff.path
        
        # 1. Handle top-level component addition/removal
        if diff.op == StateDiffOp.ADD and path not in new_state and "." not in path:
             new_state[path] = diff.value
             continue
        
        # 2. Try to find which component this path belongs to.
        # We greedily match the longest prefix that exists in the state.
        target_comp_id = None
        remaining_parts = []
        
        parts = path.split(".")
        for i in range(len(parts), 0, -1):
            prefix = ".".join(parts[:i])
            if prefix in new_state:
                target_comp_id = prefix
                remaining_parts = parts[i:]
                break
        
        if target_comp_id:
            current = new_state[target_comp_id]
            # Navigate internal state
            for part in remaining_parts[:-1]:
                if part not in current or not isinstance(current[part], dict):
                    current[part] = {}
                current = current[part]
            
            if not remaining_parts:
                # Path IS the component ID
                if diff.op == StateDiffOp.REPLACE or diff.op == StateDiffOp.ADD:
                    new_state[target_comp_id] = diff.value
                elif diff.op == StateDiffOp.REMOVE:
                    new_state.pop(target_comp_id, None)
            else:
                target_key = remaining_parts[-1]
                if diff.op == StateDiffOp.ADD or diff.op == StateDiffOp.REPLACE:
                    current[target_key] = diff.value
                elif diff.op == StateDiffOp.REMOVE:
                    current.pop(target_key, None)
        else:
            # Fallback: Naive split (for new components or paths not matching existing components)
            if diff.op == StateDiffOp.ADD or diff.op == StateDiffOp.REPLACE:
                parts = path.split(".")
                current = new_state
                for part in parts[:-1]:
                    if part not in current or not isinstance(current[part], dict):
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = diff.value
            elif diff.op == StateDiffOp.REMOVE:
                # Naive removal
                parts = path.split(".")
                current = new_state
                for part in parts[:-1]:
                    if part not in current or not isinstance(current[part], dict):
                        break
                    current = current[part]
                else:
                    current.pop(parts[-1], None)

    return new_state


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
