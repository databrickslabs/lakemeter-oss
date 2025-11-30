#!/usr/bin/env python3
"""
OpenAI API Service
Handles calls to OpenAI API for workload analysis
"""

import os
import sys
import json
from openai import OpenAI
import mlflow


def call_openai_api(prompt_text: str, system_prompt: str, api_key: str, base_url: str = None) -> dict:
    """
    Call OpenAI API with the given prompt

    Args:
        prompt_text: User's prompt text
        system_prompt: System prompt for context
        api_key: OpenAI API key
        base_url: Optional custom base URL for OpenAI API (e.g., Azure OpenAI, local models)

    Returns:
        dict: Response containing the parsed JSON or error information
    """
    try:
        # Enable MLflow autologging for OpenAI
        mlflow.openai.autolog()

        # Initialize OpenAI client with the API key and optional base URL
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        client = OpenAI(**client_kwargs)
        
        # Prepare messages
        messages = []
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        messages.append({
            "role": "user",
            "content": prompt_text
        })
        
        # Call the API
        response = client.chat.completions.create(
            model="databricks-gpt-5-1",
            max_tokens=1024,
            messages=messages,
            temperature=0
        )
        
        # Extract response text
        response_text = ""
        if response.choices and len(response.choices) > 0:
            response_text = response.choices[0].message.content.strip()
        
        # Store original response and finish reason for debugging
        debug_info = {
            "raw_response": response_text,
            "finish_reason": response.choices[0].finish_reason if response.choices else ""
        }
        
        # Remove markdown code blocks if present
        cleaned_response = response_text.replace("```json\n", "").replace("```json", "")
        cleaned_response = cleaned_response.replace("```\n", "").replace("```", "").strip()
        
        # Parse JSON response
        try:
            json_response = json.loads(cleaned_response)
            return {
                "success": True,
                "data": json_response,
                "debug": debug_info
            }
        except json.JSONDecodeError as parse_error:
            return {
                "success": False,
                "error": f"JSON parse error: {str(parse_error)}",
                "raw_response": response_text,
                "debug": debug_info
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"API call error: {str(e)}",
            "raw_response": "",
            "debug": {}
        }


def main():
    """
    Main function to handle CLI execution
    Expects JSON input via stdin with: prompt_text, system_prompt, api_key, base_url (optional)
    Outputs JSON response to stdout
    """
    try:
        # Read input from stdin
        input_data = json.load(sys.stdin)
        
        prompt_text = input_data.get("prompt_text", "")
        system_prompt = input_data.get("system_prompt", "")
        api_key = input_data.get("api_key", "")
        base_url = input_data.get("base_url", "")
        
        if not prompt_text:
            result = {
                "success": False,
                "error": "prompt_text is required"
            }
        elif not api_key:
            result = {
                "success": False,
                "error": "api_key is required"
            }
        else:
            # Call the API with optional base_url
            result = call_openai_api(prompt_text, system_prompt, api_key, base_url if base_url else None)
        
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
