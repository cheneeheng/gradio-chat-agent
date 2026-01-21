# Multimodal Intent (Images)

## Overview

The `gradio-chat-agent` supports **Multimodal Context**, allowing users to upload images alongside their text messages. This is particularly useful for visual debugging or describing UI layout issues.

---

## Data Flow

1.  **UI Collection**: The Gradio `Chatbot` component accepts an image file.
2.  **Intent Wrapping**: The UI includes the image data (usually as a Base64 string or a local path reference) in the `trace` or a dedicated `media` field of the intent.
3.  **Agent Interpretation**: 
    *   The Agent Adapter detects the media.
    *   It uses a multimodal-capable model (e.g., `gpt-4o`, `gemini-1.5-pro`).
    *   The image is passed as a `Part` in the LLM's conversation history.
4.  **Action Proposal**: The LLM analyzes the image to decide the next action (e.g., "Set the color to match this image").

---

## Schema Extension

The `ChatIntent` schema allows for optional media:

```json
{
  "media": {
    "type": "image",
    "data": "<base64_encoded_string>",
    "mime_type": "image/png"
  }
}
```

---

## Limitations

*   **Engine Ignoring**: The Execution Engine **ignores** media. Media is used strictly by the Agent Layer to *formulate* the intent. The resulting `action_id` and `inputs` remain standard JSON.
*   **Storage**: Images are **not** persisted in the Audit Log by default to prevent DB bloat. Only the reference or a hash is stored in `execution_metadata`.
