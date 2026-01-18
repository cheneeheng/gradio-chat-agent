"""Example of Rich UI Binding with UIBinder.

This example demonstrates how to:
1. Initialize a UIBinder.
2. Bind Gradio components to state paths.
3. Automatically update components when state changes.
"""

import gradio as gr
from gradio_chat_agent.ui.binder import UIBinder


def run_example():
    # 1. Initialize Binder
    binder = UIBinder()

    # 2. Define Components
    with gr.Blocks() as demo:
        gr.Markdown("# UIBinder Demo")
        
        with gr.Row():
            with gr.Column():
                gr.Markdown("### Source State")
                state_input = gr.JSON(
                    label="Application State",
                    value={
                        "demo": {
                            "counter": {"value": 42},
                            "status": {"online": True}
                        },
                        "user": {"name": "Alice"}
                    }
                )
                update_btn = gr.Button("Apply State to Bound Components")

            with gr.Column():
                gr.Markdown("### Bound Components")
                
                # Bind a Slider to demo.counter.value
                counter_slider = gr.Slider(label="Counter (Bound)", minimum=0, maximum=100)
                binder.bind("demo.counter.value", counter_slider)
                
                # Bind a Checkbox to demo.status.online
                status_check = gr.Checkbox(label="Is Online (Bound)")
                binder.bind("demo.status.online", status_check)
                
                # Bind a Textbox to user.name with custom update_fn
                user_text = gr.Textbox(label="Welcome Message (Bound)")
                binder.bind("user.name", user_text, update_fn=lambda x: f"Hello, {x}!")

        # 3. Setup Update logic
        # In the real app, this is handled by UIController
        def sync_ui(state):
            updates = binder.get_updates(state)
            return updates

        update_btn.click(
            sync_ui,
            inputs=[state_input],
            outputs=binder.get_bound_components()
        )

    print("UIBinder example constructed.")
    print("To view, uncomment demo.launch() in the source code.")
    # demo.launch()


if __name__ == "__main__":
    run_example()
