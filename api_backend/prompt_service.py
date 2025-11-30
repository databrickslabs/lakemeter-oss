#!/usr/bin/env python3
"""
Prompt Registry Service
Handles querying MLflow prompt registry
"""

import sys
import json
import mlflow

# revert to use prompt patch from input text for now, since the current implementation of search_prompts still only returns the Prompt not the PromptVersion object
# https://mlflow.org/docs/latest/api_reference/python_api/mlflow.genai.html#mlflow.genai.search_prompts
# https://docs.databricks.com/aws/en/mlflow3/genai/prompt-version-mgmt/prompt-registry/examples

def search_prompts(catalog: str = "users", schema: str = "fajar_muharandy") -> dict:
    """
    Search prompts in MLflow registry based on catalog and schema

    Args:
        catalog: The catalog name (default: 'users')
        schema: The schema name (default: 'fajar_muharandy')

    Returns:
        dict: Response containing the list of prompts or error information
    """
    try:
        # Build filter string using the correct format with single quotes
        filter_string = f"catalog='{catalog}' AND schema='{schema}'"

        # Search prompts with the filter
        results = mlflow.genai.search_prompts(filter_string)

        # Convert results to list of dictionaries
        prompts = []
        all_prompts_debug = []  # For debugging

        for prompt in results:
            # Get the full prompt name which includes catalog.schema.name
            full_name = prompt.name

            # Get the latest version or all versions
            # Since search_prompts returns Prompt objects (not PromptVersion),
            # we need to access the latest_version or versions attribute
            latest_version = getattr(prompt, 'latest_version', None)

            # Debug: collect all prompts to see what's available
            all_prompts_debug.append({
                "name": full_name,
                "latest_version": latest_version
            })

            # Check if the prompt matches the catalog and schema
            # Expected format: catalog.schema.promptname or just promptname
            if "." in full_name:
                parts = full_name.split(".")
                if len(parts) >= 3:
                    prompt_catalog = parts[0]
                    prompt_schema = parts[1]
                    prompt_name = ".".join(parts[2:])  # Handle names with dots

                    prompt_info = {
                        "name": prompt_name,
                        "full_name": full_name,
                        "version": latest_version,
                        "catalog": prompt_catalog,
                        "schema": prompt_schema,
                        "path": f"prompts:/{full_name}/{latest_version}",
                        "creation_timestamp": getattr(prompt, 'creation_timestamp', None),
                        "last_updated_timestamp": getattr(prompt, 'last_updated_timestamp', None),
                    }
                    prompts.append(prompt_info)
            else:
                # Handle prompts without catalog.schema prefix
                # These might be in the format used by your existing code
                prompt_info = {
                    "name": full_name,
                    "full_name": full_name,
                    "version": latest_version,
                    "catalog": catalog,
                    "schema": schema,
                    "path": f"prompts:/{catalog}.{schema}.{full_name}/{latest_version}",
                    "creation_timestamp": getattr(prompt, 'creation_timestamp', None),
                    "last_updated_timestamp": getattr(prompt, 'last_updated_timestamp', None),
                }
                prompts.append(prompt_info)

        return {
            "success": True,
            "data": prompts,
            "count": len(prompts),
            "debug_all_prompts": all_prompts_debug  # Include all prompts for debugging
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Search error: {str(e)}",
            "data": []
        }


def get_prompt_details(prompt_path: str) -> dict:
    """
    Get detailed information about a specific prompt

    Args:
        prompt_path: MLflow prompt registry path (e.g., "prompts:/users.fajar_muharandy.lakemeter/1")

    Returns:
        dict: Response containing prompt details or error information
    """
    try:
        prompt_template = mlflow.genai.load_prompt(prompt_path)

        prompt_details = {
            "path": prompt_path,
            "content": prompt_template.format(),
            "template": getattr(prompt_template, 'template', None),
        }

        return {
            "success": True,
            "data": prompt_details
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Load error: {str(e)}",
            "data": None
        }


def main():
    """
    Main function to handle CLI execution
    Expects JSON input via stdin with: action, catalog (optional), schema (optional), prompt_path (optional)
    Outputs JSON response to stdout
    """
    try:
        # Read input from stdin
        input_data = json.load(sys.stdin)

        action = input_data.get("action", "search")
        catalog = input_data.get("catalog", "users")
        schema = input_data.get("schema", "fajar_muharandy")
        prompt_path = input_data.get("prompt_path", "")

        if action == "search":
            result = search_prompts(catalog, schema)
        elif action == "get_details":
            if not prompt_path:
                result = {
                    "success": False,
                    "error": "prompt_path is required for get_details action"
                }
            else:
                result = get_prompt_details(prompt_path)
        else:
            result = {
                "success": False,
                "error": f"Unknown action: {action}. Valid actions: 'search', 'get_details'"
            }

        # Output result as JSON
        print(json.dumps(result, indent=2))

    except json.JSONDecodeError as e:
        error_result = {
            "success": False,
            "error": f"Invalid JSON input: {str(e)}"
        }
        print(json.dumps(error_result, indent=2))
        sys.exit(1)
    except Exception as e:
        error_result = {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }
        print(json.dumps(error_result, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
