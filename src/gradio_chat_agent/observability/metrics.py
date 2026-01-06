from pydantic import BaseModel, ConfigDict, Field


class EngineMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    counters: dict[str, int] = Field(
        default_factory=dict, description="Named counters for engine outcomes."
    )

    def inc(self, key: str, n: int = 1) -> None:
        self.counters[key] = int(self.counters.get(key, 0)) + n

    def render_markdown(self) -> str:
        if not self.counters:
            return "No metrics yet."
        lines = ["### Metrics"]
        for k in sorted(self.counters.keys()):
            lines.append(f"- **{k}**: {self.counters[k]}")
        return "\n".join(lines)
