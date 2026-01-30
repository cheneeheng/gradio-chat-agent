"""Example of Programmatic Project Policy Validation.

This example demonstrates how to:
1. Load a policy from a YAML string or file.
2. Validate it against the project's official JSON schema.
3. Handle validation errors in your own code.
"""

import json
import yaml
from pathlib import Path
from jsonschema import validate, ValidationError

def run_example():
    # 1. Path to schema
    # (In a real install, this would be relative to the package or an environment var)
    schema_path = Path("docs/schemas/policy.schema.json")
    
    if not schema_path.exists():
        print(f"Skipping: Schema not found at {schema_path}")
        return

    with open(schema_path, "r") as f:
        schema = json.load(f)

    # 2. Test a VALID policy
    valid_policy_yaml = """
limits:
  rate:
    per_minute: 10
  budget:
    daily: 100.0
role_mappings:
  - role: admin
    condition: "user.email.endswith('@corp.com')"
"""
    
    print("--- Scenario 1: Validating Correct Policy ---")
    try:
        policy_dict = yaml.safe_load(valid_policy_yaml)
        validate(instance=policy_dict, schema=schema)
        print("SUCCESS: Policy is valid.")
    except ValidationError as e:
        print(f"FAILURE: Policy should be valid but got error: {e.message}")

    # 3. Test an INVALID policy
    invalid_policy_yaml = """
limits:
  rate:
    per_minute: "high"  # Error: Should be integer
"""
    
    print("\n--- Scenario 2: Catching Validation Errors ---")
    try:
        policy_dict = yaml.safe_load(invalid_policy_yaml)
        validate(instance=policy_dict, schema=schema)
        print("FAILURE: Policy should be invalid but passed validation.")
    except ValidationError as e:
        print(f"SUCCESS: Correctly caught invalid policy attribute.")
        print(f"Error Message: {e.message}")
        print(f"Path: {'.'.join(str(p) for p in e.path)}")

if __name__ == "__main__":
    run_example()
