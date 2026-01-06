import json
from pathlib import Path

import jsonschema


SCHEMA_DIR = Path("docs/schemas")


def _load_schema(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_all_schemas_are_valid_jsonschema():
    for path in SCHEMA_DIR.glob("*.schema.json"):
        schema = _load_schema(path)
        # Will raise if invalid
        jsonschema.Draft202012Validator.check_schema(schema)
