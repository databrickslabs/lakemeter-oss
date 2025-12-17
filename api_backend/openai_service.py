#!/usr/bin/env python3
"""
OpenAI API Service
Handles calls to OpenAI API for workload analysis
"""

import os
import sys
import json
# import logging
from openai import OpenAI
import mlflow

# Configure logging
# log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
# os.makedirs(log_dir, exist_ok=True)
# log_file = os.path.join(log_dir, 'openai_service.log')

# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler(log_file),
#         logging.StreamHandler()  # Also print to console
#     ]
# )


def call_openai_api(prompt_text: str, prompt_path: str, api_key: str, base_url: str = None, use_responses_api: bool = False, model: str = "databricks-gpt-5-1") -> dict:
    """
    Call OpenAI API with the given prompt

    Args:
        prompt_text: User's prompt text
        prompt_path: MLflow prompt registry path (e.g., "prompts:/users.fajar_muharandy.lakemeter/1")
        api_key: OpenAI API key
        base_url: Optional custom base URL for OpenAI API (e.g., Azure OpenAI, local models)
        use_responses_api: If True, use client.responses.create instead of client.chat.completions.create
        model: Model name to use (defaults to "databricks-gpt-5-1")

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

        # Load prompt from MLflow registry
        system_prompt = ""
        if prompt_path:
            try:
                prompt_template = mlflow.genai.load_prompt(prompt_path)
                system_prompt = prompt_template.format()
            except Exception as e:
                # If loading from MLflow fails, we'll continue without a system prompt
                print(f"Warning: Failed to load prompt from {prompt_path}: {str(e)}", file=sys.stderr)

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

        # Call the API based on the selected method
        response_text = ""
        debug_info = {}

        if use_responses_api:
            # Use client.responses.create (for Databricks custom endpoints)
            input_messages = []
            if system_prompt:
                input_messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            input_messages.append({
                "role": "user",
                "content": prompt_text
            })

            response = client.responses.create(
                model=model,
                input=input_messages
            )

            # Extract response text from response.output[].content[].text
            if response.output and len(response.output) > 0:
                output_message = response.output[0]
                if hasattr(output_message, 'content') and output_message.content:
                    for content_item in output_message.content:
                        if hasattr(content_item, 'text'):
                            response_text = content_item.text.strip()
                            break

            # Store debug info for responses API
            debug_info = {
                "raw_response": response_text,
                "api_type": "responses"
            }
        else:
            # Use standard client.chat.completions.create
            response = client.chat.completions.create(
                model=model,
                max_tokens=1024,
                messages=messages,
                temperature=0
            )

            # Extract response text
            if response.choices and len(response.choices) > 0:
                response_text = response.choices[0].message.content.strip()

            # Store original response and finish reason for debugging
            debug_info = {
                "raw_response": response_text,
                "finish_reason": response.choices[0].finish_reason if response.choices else "",
                "api_type": "chat_completions"
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
    Expects JSON input via stdin with: prompt_text, prompt_path, api_key, base_url (optional), use_responses_api (optional), model (optional)
    Outputs JSON response to stdout
    """
    try:
        # Read input from stdin
        input_data = json.load(sys.stdin)

        prompt_text = input_data.get("prompt_text", "")
        prompt_path = input_data.get("prompt_path", "")
        api_key = input_data.get("api_key", "")
        base_url = input_data.get("base_url", "")
        use_responses_api = input_data.get("use_responses_api", False)
        model = input_data.get("model", "databricks-gpt-5-1")

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
            # Call the API with prompt_path and optional base_url
            result = call_openai_api(prompt_text, prompt_path, api_key, base_url if base_url else None, use_responses_api, model)
        
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
