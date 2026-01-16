"""Example of using the custom AgentTheme standalone.

This example demonstrates how to:
1. Instantiate the AgentTheme.
2. Apply it to a basic Gradio interface.
"""

import gradio as gr
from gradio_chat_agent.ui.theme import AgentTheme


def run_example():
    # 1. Create the theme
    theme = AgentTheme()

    # 2. Use it in a Blocks interface
    with gr.Blocks(theme=theme, title="Theme Demo") as demo:
        gr.Markdown("# AgentTheme Demo")
        gr.Markdown("This interface uses the custom brand colors and fonts.")

        with gr.Row():
            with gr.Column():
                gr.Textbox(label="Input Field", placeholder="Enter some text...")
                gr.Button("Primary Action", variant="primary")
                gr.Button("Secondary Action", variant="secondary")

            with gr.Column():
                gr.JSON(
                    label="Sample State",
                    value={"status": "online", "tasks": 5, "alerts": 0},
                )

    print("Theme example constructed successfully.")
    print("To view, uncomment demo.launch() in the source code.")
    # demo.launch()


if __name__ == "__main__":
    run_example()
