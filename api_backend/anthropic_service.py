#!/usr/bin/env python3
"""
Anthropic API Service
Handles calls to Anthropic Claude API for workload analysis
"""

import os
import sys
import json
from anthropic import Anthropic


def call_anthropic_api(prompt_text: str, system_prompt: str, api_key: str) -> dict:
    """
    Call Anthropic API with the given prompt
    
    Args:
        prompt_text: User's prompt text
        system_prompt: System prompt for context
        api_key: Anthropic API key
        
    Returns:
        dict: Response containing the parsed JSON or error information
    """
    try:
        # Initialize Anthropic client with only the API key
        client = Anthropic(api_key=api_key)
        
        # Call the API
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": prompt_text,
                }
            ],
        )
        
        # Extract response text
        response_text = ""
        if message.content and len(message.content) > 0:
            if message.content[0].type == "text":
                response_text = message.content[0].text.strip()
        
        # Store original response and stop reason for debugging
        debug_info = {
            "raw_response": response_text,
            "stop_reason": message.stop_reason or ""
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
    Expects JSON input via stdin with: prompt_text, system_prompt, api_key
    Outputs JSON response to stdout
    """
    try:
        # Read input from stdin
        input_data = json.load(sys.stdin)
        
        prompt_text = input_data.get("prompt_text", "")
        system_prompt = input_data.get("system_prompt", "")
        api_key = input_data.get("api_key", "")
        
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
            # Call the API
            result = call_anthropic_api(prompt_text, system_prompt, api_key)
        
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
