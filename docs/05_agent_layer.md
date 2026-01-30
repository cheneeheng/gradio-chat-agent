# Agent Layer Architecture

## Overview

The **Agent Layer** is the bridge between the user's natural language and the strict, structured world of the Execution Engine. It uses an LLM (Large Language Model) to interpret intent, but it is **constrained** to never execute actions directly. It can only *propose* them.

---

## The Interpreter Loop

The agent operates in a stateless "turn-based" loop:

1.  **Receive Message**: User input arrives.
2.  **Context Construction**: Gather all necessary context (see below).
3.  **LLM Inference**: Send prompt to LLM.
4.  **Intent Parsing**: Convert LLM output (Tool Calls or JSON) into a `ChatIntent`.
5.  **Handoff**: Pass the `ChatIntent` to the Execution Engine.

---

## Context Management

The "Intelligence" of the system relies on the context provided to the LLM. The Prompt Context window is constructed dynamically:

### 1. System Prompt (The Persona)
Defines the rules:
*   "You are a control plane..."
*   "You do not invent actions..."
*   "You must check preconditions..."
*   "You must ask for clarification if ambiguous..."

### 2. Registry Injection (The Capabilities)
The agent is "taught" the available tools in every prompt (or via system message):
*   **Component Registry**: "Here is the current state schema of the UI."
*   **Action Registry**: "Here are the actions you can call, their schemas, and their costs."

### 3. State Injection (The Reality)
*   **Current Snapshot**: The full JSON representation of the current component state.
*   **Diffs**: Optionally, the diffs from the last few turns to show progress.

### 4. Memory Injection (The History)
*   **Conversation History**: Last $N$ turns of chat.
*   **Execution Log**: Last $M$ results (Success/Failure) so the agent knows if its previous attempt worked.
*   **Explicit Facts**: Key-value pairs retrieved from the `SessionMemory` repo.

---

## Intent Generation

The agent does not execute code. It emits a **Structured Intent**:

```json
{
  "type": "action_call",
  "action_id": "demo.counter.set",
  "inputs": { "value": 42 },
  "confirmed": false
}
```

Or a **Clarification Request**:

```json
{
  "type": "clarification_request",
  "question": "Which counter do you mean?"
}
```

### Tool Use (Function Calling)
We utilize the native "Tool Use" or "Function Calling" capabilities of modern LLMs (OpenAI/Anthropic/Gemini).
*   The `ActionRegistry` is converted into a list of Tool Definitions.
*   The LLM selects a tool.
*   The Agent Adapter wraps that tool selection into a `ChatIntent`.

---

## Developer Contract: AgentAdapter

To support multiple LLM providers, all integrations must implement the following base interface:

```python
from abc import ABC, abstractmethod
from typing import Optional, List, Union
from .models.intent import ChatIntent
from .models.plan import ExecutionPlan

class AgentAdapter(ABC):
    @abstractmethod
    def message_to_intent_or_plan(
        self,
        message: str,
        history: List[dict],
        state: dict,
        registry: dict,
        media: Optional[dict] = None
    ) -> Union[ChatIntent, ExecutionPlan]:
        """
        Converts a user message and context into a structured intent.
        
        Args:
            message: Raw text from user.
            history: List of past conversation turns.
            state: Current project state snapshot.
            registry: Dict of available actions and components.
            media: Optional image/document data.
        """
        pass
```

---

## Safety & Hallucination Control

*   **Strict Parsers**: If the LLM produces invalid JSON or hallucinates an `action_id` not in the registry, the Adapter catches this *before* it reaches the engine and returns a specialized error prompt to the LLM ("Action XYZ does not exist. Please chose from...").
*   **No Direct IO**: The LLM cannot browse the web or access the DB. It only sees what is in the Context Window.
