#!/bin/bash

# Example usage of the gradio-agent CLI tool

# 1. Create a new project
uv run gradio-agent project create --name "CLI Demo Project" --project-id "cli-demo"

# 2. List all projects
uv run gradio-agent project list

# 3. Create a new user (prompts for password)
echo "Creating user 'bob' with password 'secret'..."
echo "secret" | uv run gradio-agent user create --username "bob"

# 4. Reset user password
echo "Resetting password for 'bob' to 'new-secret'..."
echo "new-secret" | uv run gradio-agent user password-reset --username "bob"

# 5. List webhooks (assuming some exist)
uv run gradio-agent webhook list

# 6. Validate a project policy
uv run gradio-agent project validate docs/policies/example-project.yaml
