from ..models.action import ActionDeclaration
from ..models.component import ComponentDeclaration


def build_agent_context_markdown(
    *,
    components: dict[str, ComponentDeclaration],
    actions: dict[str, ActionDeclaration],
    max_items: int = 200,
) -> str:
    """
    Implementation: converts registry descriptions into a compact, readable context block
    you can inject into the floating chatbot “system/help” area or show in a side panel.
    """
    lines: list[str] = []
    lines.append("## UI components (contract)")
    for i, c in enumerate(components.values()):
        if i >= max_items:
            lines.append("- (truncated)")
            break
        lines.append(f"- **{c.component_id}**: {c.title} — {c.description}")

    lines.append("")
    lines.append("## UI actions (capabilities)")
    for i, a in enumerate(actions.values()):
        if i >= max_items:
            lines.append("- (truncated)")
            break
        conf = (
            "confirm" if a.permission.confirmation_required else "no-confirm"
        )
        lines.append(
            f"- **{a.action_id}**: {a.title} — {a.description} "
            f"(risk={a.permission.risk}, {conf})"
        )

    return "\n".join(lines)
