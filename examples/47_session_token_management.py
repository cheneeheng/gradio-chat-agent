"""Example of Session Token Management in the UI.

This example demonstrates how the UI handles session tokens, 
including a mock login process that sets a token in the session state.
"""

import gradio as gr
import uuid

def run_example():
    with gr.Blocks() as demo:
        # 1. Session state for the token
        session_token = gr.State(None)
        
        gr.Markdown("# Session Token Management Demo")
        
        with gr.Tab("Login"):
            login_btn = gr.Button("Mock Login")
            token_display = gr.Textbox(label="Active Session Token", interactive=False)
            
            def on_login():
                token = f"sk-{uuid.uuid4().hex[:12]}"
                return token, token
            
            login_btn.click(on_login, inputs=[], outputs=[session_token, token_display])
            
        with gr.Tab("Secure Area"):
            gr.Markdown("This area simulates a component that needs a token.")
            check_token_btn = gr.Button("Check Token")
            status_output = gr.Textbox(label="Status")
            
            def check_access(token):
                if token:
                    return f"Access Granted! Token: {token}"
                return "Access Denied: No session token found."
            
            check_token_btn.click(check_access, inputs=[session_token], outputs=[status_output])

    print("Session token management example constructed.")
    print("To view, uncomment demo.launch() in the source code.")
    # demo.launch()

if __name__ == "__main__":
    run_example()
