import json
from pathlib import Path

from gradio_chat_agent.models.action import ActionDeclaration
from gradio_chat_agent.models.component import ComponentDeclaration
from gradio_chat_agent.models.execution_result import ExecutionResult
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.state_snapshot import StateSnapshot


OUTPUT_DIR = Path("docs/schemas")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


MODELS = {
    "component.schema.json": ComponentDeclaration,
    "action.schema.json": ActionDeclaration,
    "intent.schema.json": ChatIntent,
    "state_snapshot.schema.json": StateSnapshot,
    "execution_result.schema.json": ExecutionResult,
}


def main() -> None:
    for filename, model in MODELS.items():
        schema = model.model_json_schema()
        (OUTPUT_DIR / filename).write_text(
            json.dumps(schema, indent=2),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
