#!/usr/bin/env python3
"""
Prompt Registry Service
Handles querying MLflow prompt registry
"""

import sys
import json
import mlflow


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
        # Build filter string
        filter_string = f"catalog = '{catalog}' AND schema = '{schema}'"

        # Search prompts
        results = mlflow.genai.search_prompts(filter_string)

        # Convert results to list of dictionaries
        prompts = []
        for prompt in results:
            prompt_info = {
                "name": prompt.name,
                "version": prompt.version,
                "catalog": getattr(prompt, 'catalog', None),
                "schema": getattr(prompt, 'schema', None),
                "path": f"prompts:/{catalog}.{schema}.{prompt.name}/{prompt.version}",
                "creation_timestamp": getattr(prompt, 'creation_timestamp', None),
                "last_updated_timestamp": getattr(prompt, 'last_updated_timestamp', None),
            }
            prompts.append(prompt_info)

        return {
            "success": True,
            "data": prompts,
            "count": len(prompts)
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
