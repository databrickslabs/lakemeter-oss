# Python Backend for Anthropic API

This directory contains a Python backend service that handles Anthropic API calls for the promptsizer application.

## Overview

The Python backend was created to handle Anthropic API calls server-side instead of making them directly from the browser. This provides better security and control over API key management.

## Setup

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)

### Installation

1. Run the setup script to create a virtual environment and install dependencies:

```bash
cd api_backend
bash setup.sh
```

Or manually:

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

## Files

### `anthropic_service.py`

Main Python script that handles Anthropic API calls.

**Features:**
- Accepts JSON input via stdin
- Calls Anthropic Claude API
- Returns structured JSON response
- Includes error handling and debug information

**Usage:**
```bash
echo '{"prompt_text": "your prompt", "system_prompt": "system prompt", "api_key": "your-api-key"}' | python3 anthropic_service.py
```

**Response Format:**
```json
{
  "success": true,
  "data": {
    "tableStructure": [...]
  },
  "debug": {
    "raw_response": "...",
    "stop_reason": "end_turn"
  }
}
```

### `requirements.txt`

Python dependencies:
- `anthropic==0.39.0` - Official Anthropic Python SDK

### `setup.sh`

Automated setup script that:
1. Creates a Python virtual environment
2. Updates pip
3. Installs all required dependencies

## Integration with Next.js

The Python backend is called from a Next.js API route at `/app/api/anthropic/route.ts`.

**Flow:**
1. Frontend makes POST request to `/api/anthropic`
2. Next.js API route receives request
3. API route executes Python script with user input
4. Python script calls Anthropic API
5. Results are returned to frontend

## Environment Variables

The API key is passed from the Next.js environment variables through the API route to the Python script. Ensure `NEXT_PUBLIC_ANTHROPIC_API_KEY` is set in your `.env.local` file.

## Development

### Testing the Python Script

You can test the Python script directly:

```bash
# Activate virtual environment
source api_backend/venv/bin/activate

# Test with sample input
echo '{
  "prompt_text": "I need to process data from Salesforce into my lakehouse",
  "system_prompt": "You are a helpful assistant",
  "api_key": "your-api-key-here"
}' | python3 api_backend/anthropic_service.py
```

### Updating Dependencies

To add new Python packages:

1. Activate the virtual environment
2. Install the package: `pip install package-name`
3. Update requirements.txt: `pip freeze > requirements.txt`

## Troubleshooting

### Virtual Environment Not Found

If you get an error about the virtual environment not being found:

```bash
cd api_backend
rm -rf venv
bash setup.sh
```

### Permission Denied

If you get a permission error with the setup script:

```bash
chmod +x api_backend/setup.sh
```

### Import Errors

Make sure the virtual environment is activated and dependencies are installed:

```bash
source api_backend/venv/bin/activate
pip install -r api_backend/requirements.txt
```

## Security Notes

- The API key is never exposed to the browser
- All API calls are server-side
- Input is validated before processing
- Errors are logged but sensitive information is not exposed to clients
