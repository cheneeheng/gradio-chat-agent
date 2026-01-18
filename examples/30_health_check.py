"""Example of checking system health via the /health endpoint.

This example demonstrates how to:
1. Ping the /health endpoint of the running application.
2. Interpret the health status.
"""

import requests
import json

def check_health():
    # Assuming the app is running on localhost:7860
    url = "http://127.0.0.1:7860/health"
    
    print(f"Checking health at {url}...")
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        print(f"Payload: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("System is HEALTHY.")
        else:
            print("System is UNHEALTHY.")
            
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the server. Is it running?")

if __name__ == "__main__":
    # Note: This requires the server to be running (uv run python src/gradio_chat_agent/app.py)
    # check_health()
    print("Health check example script ready. Uncomment check_health() to run against a live server.")
