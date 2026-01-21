"""Example of an External Headless API Client.

This script demonstrates how an external Python application would:
1. Authenticate with the Gradio Chat Agent using a Bearer Token.
2. Call the 'execute_action' endpoint via the Gradio API.
3. Parse the result.
"""

import requests
import json

# Configuration (Assumes the app is running on localhost:7860)
BASE_URL = "http://127.0.0.1:7860"
# In a real scenario, you'd get this from 'gradio-agent token create'
API_TOKEN = "sk-example-token-12345"
PROJECT_ID = "default_project"

def call_agent_api():
    print(f"--- Calling Agent API at {BASE_URL} ---")
    
    # Endpoint for 'execute_action'
    # Gradio API endpoints are typically exposed under /run/predict or /call/...
    # but we can also use the direct functional call if using the API wrapper.
    # Here we simulate a standard HTTP POST to the underlying FastAPI route.
    
    payload = {
        "data": [
            PROJECT_ID,
            "demo.counter.increment",
            {"amount": 10},
            "assisted",
            False # confirmed
        ]
    }
    
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        # Note: The specific path depends on the Gradio mounting. 
        # For the mounted app in app.py, the API is exposed.
        # We use the 'api_name' from layout.py: 'execute_action'
        response = requests.post(
            f"{BASE_URL}/run/execute_action", 
            json=payload, 
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            # Gradio returns data in a list under the 'data' key
            api_res = result.get("data", [{}])[0]
            print(f"Success! Result: {api_res.get('message')}")
            print(f"New Snapshot ID: {api_res.get('data', {}).get('state_snapshot_id')}")
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the server. Ensure the app is running.")

if __name__ == "__main__":
    print("This example requires the server to be running:")
    print("uv run python src/gradio_chat_agent/app.py")
    print("\nAnd a valid API token. For demonstration, we just show the logic.")
    # call_agent_api()
