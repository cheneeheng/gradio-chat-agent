## Getting Started

This guide walks through running the demo and controlling components via chat.

### Prerequisites

- Python 3.10+
- An OpenAI-compatible API key
- SQLite (default)

### Installation

```bash
pip install -r requirements.txt
```

### Running the App

```bash
python src/gradio_chat_agent/app.py
```

The Gradio UI will start locally and prompt for authentication.

### Default Setup

- A default project is created
- An admin user is available
- A demo component (`demo.counter`) is registered

### Example: Controlling a Component via Chat

In the chat UI, try:

```
Set the counter to 5
```

What happens internally:

1. The agent interprets the request
2. It proposes the action `demo.counter.set`
3. The execution engine:
   - Validates permissions
   - Checks budgets and limits
   - Applies the action
4. The component state updates
5. A state diff is shown in the UI
6. The execution is logged and replayable

### Example: Multi-Step Plan

```
Increase the counter by 2, then reset it
```

The agent proposes a plan:

- Step 1: `demo.counter.increment`
- Step 2: `demo.counter.reset`

You can:

- Review the plan
- See warnings (budget, permissions)
- Approve or reject execution

### Viewer vs Operator vs Admin

- **Viewer**: Can chat and inspect state
- **Operator**: Can execute low/medium-risk actions
- **Admin**: Full control, approvals, role management

### Replay

At any time, you can replay the execution log to reconstruct state from scratch.

---

### Summary

You are not chatting _with_ components.

You are chatting with a **governed control plane** that safely manipulates components on your behalf.
