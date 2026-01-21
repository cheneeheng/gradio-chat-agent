## Threat Model

This system is designed to safely allow a chat interface to control real application state.

### Primary Threats Addressed

| Threat                               | Mitigation                                |
| ------------------------------------ | ----------------------------------------- |
| LLM hallucinating actions            | Agent can only propose registered actions |
| UI bugs executing unintended changes | UI cannot execute actions                 |
| Prompt injection                     | Engine ignores prompts; enforces policies |
| Unauthorized execution               | Role-based enforcement in engine          |
| Runaway automation                   | Budgets, rate limits, approvals           |
| Silent state corruption              | All changes logged and replayable         |
| Irreversible mistakes                | Replay, audit, and approval workflows     |
| Automation bypassing safety          | Same engine used for all execution paths  |

### Explicit Non-Goals

The system does **not** attempt to:

- Trust the LLM with authority
- Encode business logic in prompts
- Hide state changes
- Optimize for minimal code size

### Trust Boundaries

- **Untrusted**: Chat UI, LLM output, API clients
- **Trusted**: Execution engine, persistence layer
- **Authoritative**: Engine policies and action registry

### Result

Even if:

- The LLM behaves incorrectly
- The UI has a bug
- An API client misbehaves

The system remains safe, deterministic, and auditable.
