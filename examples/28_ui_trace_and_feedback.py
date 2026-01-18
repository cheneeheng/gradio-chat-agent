"""Example showing how to use and verify UI Trace and Feedback features.

This 'example' is a guide on how to interact with the UI to see the 
newly implemented features:
1. Visual Action Feedback (Status Indicators)
2. Raw Trace Inspectors (Last Intent & Last Result)
"""

def guide():
    print("--- UI Trace and Feedback Guide ---")
    print("1. Start the application:")
    print("   uv run python src/gradio_chat_agent/app.py")
    print("\n2. Open the Gradio UI in your browser.")
    print("\n3. Perform an action via chat, e.g., 'Increment the counter by 5'.")
    print("\n4. Observe 'Visual Action Feedback':")
    print("   - Look at the sidebar in the 'Control Panel'.")
    print("   - You will see a status indicator (Ready, Success, Pending, or Failed).")
    print("   - After a successful action, it will show '✅ Success'.")
    print("\n5. Observe 'Raw Trace Inspectors':")
    print("   - Look at the 'State Inspector' on the right.")
    print("   - Click on the 'Trace' tab.")
    print("   - You will find two sub-tabs: 'Last Intent' and 'Last Result'.")
    print("   - 'Last Intent' shows the structured JSON the agent proposed.")
    print("   - 'Last Result' shows the full execution result including diffs and metadata.")

if __name__ == "__main__":
    guide()
