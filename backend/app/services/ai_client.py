"""
Databricks Claude AI Client

Integrates with Databricks-hosted Claude model for the AI assistant.
Endpoint: {DATABRICKS_HOST}/serving-endpoints/{CLAUDE_MODEL_ENDPOINT}/invocations

Uses OpenAI-compatible chat completions format as per Databricks documentation:
https://docs.databricks.com/aws/en/machine-learning/model-serving/query-chat-models

Rate Limits (Pay-per-token):
- Input tokens per minute (ITPM): Controls input throughput
- Output tokens per minute (OTPM): Controls output throughput
- Queries per hour: Maximum requests in 60-minute window
"""
import os
import json
import asyncio
import httpx
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import deque

from app.config import log_info, log_warning, log_error


# Claude endpoint configuration
# DATABRICKS_HOST is auto-set by Databricks Apps runtime; CLAUDE_MODEL_ENDPOINT is set via app.yaml valueFrom
_raw_host = os.getenv("DATABRICKS_HOST", "")
# Ensure DATABRICKS_HOST always has https:// protocol (Databricks Apps runtime may omit it)
DATABRICKS_HOST = (_raw_host if _raw_host.startswith("http") else f"https://{_raw_host}") if _raw_host else ""
MODEL_ENDPOINT = os.getenv("CLAUDE_MODEL_ENDPOINT", "databricks-claude-opus-4-6")
CLAUDE_ENDPOINT = f"{DATABRICKS_HOST}/serving-endpoints/{MODEL_ENDPOINT}/invocations" if DATABRICKS_HOST else ""

# Rate limiting configuration
MAX_QUERIES_PER_HOUR = 500
MAX_INPUT_TOKENS_PER_MINUTE = 200000
MAX_OUTPUT_TOKENS_PER_MINUTE = 20000


@dataclass
class RateLimitState:
    """Tracks rate limit usage."""
    query_timestamps: deque
    input_tokens_window: deque
    output_tokens_window: deque
    
    def __init__(self):
        self.query_timestamps = deque()
        self.input_tokens_window = deque()
        self.output_tokens_window = deque()


class ClaudeAIClient:
    """
    Client for Databricks-hosted Claude models.
    
    Uses OpenAI-compatible chat completions format.
    Supports multiple models: databricks-claude-opus-4-6, databricks-claude-sonnet-4-6
    """
    
    def __init__(self, token: Optional[str] = None, model: Optional[str] = None):
        self._token = token
        self._model = model or MODEL_ENDPOINT
        self._endpoint = f"{DATABRICKS_HOST}/serving-endpoints/{self._model}/invocations"
        self._rate_limit_state = RateLimitState()
        self._http_client: Optional[httpx.AsyncClient] = None
    
    def set_token(self, token: str):
        """Set the authentication token."""
        self._token = token
    
    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=120.0)
        return self._http_client
    
    async def close(self):
        """Close the HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
    
    def _clean_rate_limit_windows(self):
        """Remove expired entries from rate limit tracking."""
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        minute_ago = now - timedelta(minutes=1)
        
        while self._rate_limit_state.query_timestamps and \
              self._rate_limit_state.query_timestamps[0] < hour_ago:
            self._rate_limit_state.query_timestamps.popleft()
        
        while self._rate_limit_state.input_tokens_window and \
              self._rate_limit_state.input_tokens_window[0][0] < minute_ago:
            self._rate_limit_state.input_tokens_window.popleft()
        
        while self._rate_limit_state.output_tokens_window and \
              self._rate_limit_state.output_tokens_window[0][0] < minute_ago:
            self._rate_limit_state.output_tokens_window.popleft()
    
    def _check_rate_limits(self, estimated_input_tokens: int = 1000) -> bool:
        """Check if we're within rate limits."""
        self._clean_rate_limit_windows()
        
        if len(self._rate_limit_state.query_timestamps) >= MAX_QUERIES_PER_HOUR:
            log_warning(f"Rate limited: {len(self._rate_limit_state.query_timestamps)} queries in last hour")
            return False
        
        current_input_tokens = sum(t[1] for t in self._rate_limit_state.input_tokens_window)
        if current_input_tokens + estimated_input_tokens > MAX_INPUT_TOKENS_PER_MINUTE:
            log_warning(f"Rate limited: {current_input_tokens} input tokens in last minute")
            return False
        
        return True
    
    def _record_usage(self, input_tokens: int, output_tokens: int):
        """Record token usage for rate limiting."""
        now = datetime.now()
        self._rate_limit_state.query_timestamps.append(now)
        self._rate_limit_state.input_tokens_window.append((now, input_tokens))
        self._rate_limit_state.output_tokens_window.append((now, output_tokens))
    
    def _convert_tools_to_openai_format(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert our tool format to OpenAI functions format."""
        openai_tools = []
        for tool in tools:
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", tool.get("parameters", {}))
                }
            }
            openai_tools.append(openai_tool)
        return openai_tools
    
    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
        temperature: float = 0,
        system: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a chat request to Claude using OpenAI-compatible format.
        """
        if not self._token:
            raise ValueError("No authentication token provided")
        
        # Estimate input tokens
        estimated_input = sum(len(str(m.get('content', ''))) // 4 for m in messages)
        if system:
            estimated_input += len(system) // 4
        
        if not self._check_rate_limits(estimated_input):
            raise Exception("Rate limit exceeded. Please wait before making more requests.")
        
        # Build messages list with system message first (OpenAI format)
        formatted_messages = []
        if system:
            formatted_messages.append({"role": "system", "content": system})
        
        # Add conversation messages
        for msg in messages:
            # Handle tool results in OpenAI format
            if msg.get("role") == "user" and isinstance(msg.get("content"), list):
                # This is a tool result in Anthropic format, convert to OpenAI
                for item in msg["content"]:
                    if item.get("type") == "tool_result":
                        # Ensure tool result content is non-empty
                        tool_content = item.get("content", "")
                        if not tool_content:
                            tool_content = "{}"
                        formatted_messages.append({
                            "role": "tool",
                            "tool_call_id": item.get("tool_use_id", ""),
                            "content": tool_content
                        })
            elif msg.get("tool_calls"):
                # Assistant message with tool calls — omit content field.
                # Databricks FMAPI cannot convert content + tool_calls together
                # to Anthropic format; it drops tool_result pairing. Always send
                # tool_calls-only assistant messages (OpenAI spec allows this).
                assistant_msg = {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": tc.get("id", f"call_{i}"),
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": json.dumps(tc.get("arguments", {}))
                            }
                        }
                        for i, tc in enumerate(msg["tool_calls"])
                    ]
                }
                formatted_messages.append(assistant_msg)
            else:
                # For regular messages, ensure content is non-empty
                content = msg.get("content", "")
                if not content and msg.get("role") == "assistant":
                    content = "I'll help you with that."
                formatted_messages.append({
                    "role": msg["role"],
                    "content": content
                })
        
        # Build request payload (OpenAI chat completions format)
        payload = {
            "messages": formatted_messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        if tools:
            payload["tools"] = self._convert_tools_to_openai_format(tools)
            payload["tool_choice"] = "auto"
        
        client = await self._get_http_client()
        
        log_info(f"Sending request to Claude: {self._endpoint}")
        log_info(f"Payload keys: {list(payload.keys())}, messages count: {len(formatted_messages)}")
        
        # Log message structure for debugging tool_use/tool_result issues
        for i, msg in enumerate(formatted_messages):
            role = msg.get("role", "?")
            if role == "tool":
                log_info(f"  Formatted [{i}] tool: call_id={msg.get('tool_call_id', '?')[:30]}")
            elif msg.get("tool_calls"):
                tool_ids = [tc.get("id", "?")[:30] for tc in msg.get("tool_calls", [])]
                log_info(f"  Formatted [{i}] {role}: tool_calls={tool_ids}")
            else:
                content_preview = str(msg.get("content", ""))[:40]
                log_info(f"  Formatted [{i}] {role}: {content_preview}...")
        
        try:
            response = await client.post(
                self._endpoint,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/json"
                }
            )
            
            log_info(f"Response status: {response.status_code}")
            
            if response.status_code != 200:
                error_text = response.text
                log_error(f"Claude API error: {response.status_code} - {error_text}")
                raise Exception(f"Claude API error: {response.status_code} - {error_text[:500]}")
            
            result = response.json()
            log_info(f"Response keys: {list(result.keys())}")
            
            # Record usage
            usage = result.get("usage", {})
            self._record_usage(
                usage.get("prompt_tokens", estimated_input),
                usage.get("completion_tokens", 0)
            )
            
            return self._parse_openai_response(result)
            
        except httpx.HTTPStatusError as e:
            log_error(f"Claude API HTTP error: {e.response.status_code} - {e.response.text}")
            if e.response.status_code == 429:
                raise Exception("AI service is temporarily rate limited. Please try again in a moment.")
            raise Exception(f"AI service error: {e.response.status_code}")
        except Exception as e:
            log_error(f"Claude API request failed: {e}")
            raise
    
    async def chat_stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        system: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Send a streaming chat request to Claude using OpenAI-compatible format.
        """
        if not self._token:
            yield {"type": "error", "content": "No authentication token provided"}
            return
        
        estimated_input = sum(len(str(m.get('content', ''))) // 4 for m in messages)
        if system:
            estimated_input += len(system) // 4
        
        if not self._check_rate_limits(estimated_input):
            yield {"type": "error", "content": "Rate limit exceeded. Please wait before making more requests."}
            return
        
        # Build messages with system message first
        formatted_messages = []
        if system:
            formatted_messages.append({"role": "system", "content": system})
        
        for msg in messages:
            if msg.get("role") == "user" and isinstance(msg.get("content"), list):
                for item in msg["content"]:
                    if item.get("type") == "tool_result":
                        # Ensure tool result content is non-empty
                        tool_content = item.get("content", "")
                        if not tool_content:
                            tool_content = "{}"
                        formatted_messages.append({
                            "role": "tool",
                            "tool_call_id": item.get("tool_use_id", ""),
                            "content": tool_content
                        })
            elif msg.get("tool_calls"):
                # For assistant messages with tool calls, content can be omitted if empty
                assistant_msg = {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": tc.get("id", f"call_{i}"),
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": json.dumps(tc.get("arguments", {}))
                            }
                        }
                        for i, tc in enumerate(msg["tool_calls"])
                    ]
                }
                # Only include content if it's non-empty
                content = msg.get("content", "")
                if content:
                    assistant_msg["content"] = content
                formatted_messages.append(assistant_msg)
            else:
                # For regular messages, ensure content is non-empty
                content = msg.get("content", "")
                if not content and msg.get("role") == "assistant":
                    content = "I'll help you with that."
                formatted_messages.append({
                    "role": msg["role"],
                    "content": content
                })
        
        # Build request payload with streaming
        payload = {
            "messages": formatted_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True
        }
        
        if tools:
            payload["tools"] = self._convert_tools_to_openai_format(tools)
            payload["tool_choice"] = "auto"
        
        client = await self._get_http_client()
        
        log_info(f"Sending streaming request to Claude: {self._endpoint}")
        
        # Log message structure for debugging tool_use/tool_result issues (streaming)
        log_info(f"Streaming request - {len(formatted_messages)} formatted messages:")
        for i, msg in enumerate(formatted_messages):
            role = msg.get("role", "?")
            if role == "tool":
                log_info(f"  Fmt [{i}] tool: call_id={msg.get('tool_call_id', '?')[:30]}")
            elif msg.get("tool_calls"):
                tool_ids = [tc.get("id", "?")[:30] for tc in msg.get("tool_calls", [])]
                log_info(f"  Fmt [{i}] {role}: tool_calls={tool_ids}")
            else:
                content_preview = str(msg.get("content", ""))[:40]
                log_info(f"  Fmt [{i}] {role}: {content_preview}...")
        
        try:
            async with client.stream(
                "POST",
                self._endpoint,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/json"
                }
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    error_decoded = error_text.decode()
                    log_error(f"Claude streaming error: {response.status_code} - {error_decoded}")
                    
                    # Try to extract meaningful error message
                    try:
                        error_json = json.loads(error_decoded)
                        error_msg = error_json.get("error", {}).get("message", "") or error_json.get("message", "") or error_decoded[:200]
                    except:
                        error_msg = error_decoded[:200] if len(error_decoded) > 200 else error_decoded
                    
                    if response.status_code == 400:
                        yield {"type": "error", "content": f"Request error: {error_msg}. Try clearing the conversation."}
                    elif response.status_code == 429:
                        yield {"type": "error", "content": "Rate limited. Please wait a moment and try again."}
                    else:
                        yield {"type": "error", "content": f"AI service error ({response.status_code}): {error_msg}"}
                    return
                
                output_tokens = 0
                current_tool_calls = []
                
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    
                    try:
                        chunk = json.loads(data)
                        
                        # Parse OpenAI streaming format
                        choices = chunk.get("choices", [])
                        if not choices:
                            continue
                        
                        delta = choices[0].get("delta", {})
                        finish_reason = choices[0].get("finish_reason")
                        
                        # Text content
                        if delta.get("content"):
                            output_tokens += 1
                            yield {"type": "content_delta", "content": delta["content"]}
                        
                        # Tool calls
                        if delta.get("tool_calls"):
                            for tc in delta["tool_calls"]:
                                tc_index = tc.get("index", 0)
                                
                                # Extend list if needed
                                while len(current_tool_calls) <= tc_index:
                                    current_tool_calls.append({
                                        "id": "",
                                        "name": "",
                                        "arguments": ""
                                    })
                                
                                if tc.get("id"):
                                    current_tool_calls[tc_index]["id"] = tc["id"]
                                if tc.get("function", {}).get("name"):
                                    current_tool_calls[tc_index]["name"] = tc["function"]["name"]
                                    yield {"type": "tool_use_start", "id": tc["id"], "name": tc["function"]["name"]}
                                if tc.get("function", {}).get("arguments"):
                                    current_tool_calls[tc_index]["arguments"] += tc["function"]["arguments"]
                        
                        if finish_reason == "tool_calls" and current_tool_calls:
                            # Parse and yield complete tool calls
                            for tc in current_tool_calls:
                                try:
                                    args = json.loads(tc["arguments"]) if tc["arguments"] else {}
                                    yield {
                                        "type": "tool_call_complete",
                                        "id": tc["id"],
                                        "name": tc["name"],
                                        "arguments": args
                                    }
                                except json.JSONDecodeError:
                                    pass
                        
                        if finish_reason:
                            yield {"type": "message_delta", "stop_reason": finish_reason}
                        
                    except json.JSONDecodeError:
                        continue
                
                self._record_usage(estimated_input, output_tokens)
                yield {"type": "done"}
                
        except Exception as e:
            log_error(f"Claude streaming error: {e}")
            yield {"type": "error", "content": str(e)}
    
    def _parse_openai_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse OpenAI chat completions response format."""
        result = {
            "content": "",
            "tool_calls": [],
            "usage": response.get("usage", {}),
            "stop_reason": None
        }
        
        choices = response.get("choices", [])
        if choices:
            choice = choices[0]
            message = choice.get("message", {})
            
            result["content"] = message.get("content", "") or ""
            result["stop_reason"] = choice.get("finish_reason")
            
            # Parse tool calls
            if message.get("tool_calls"):
                for tc in message["tool_calls"]:
                    func = tc.get("function", {})
                    try:
                        args = json.loads(func.get("arguments", "{}"))
                    except json.JSONDecodeError:
                        args = {}
                    
                    result["tool_calls"].append({
                        "id": tc.get("id", ""),
                        "name": func.get("name", ""),
                        "arguments": args
                    })
        
        return result


def get_claude_client(token: str, model: str = "databricks-claude-opus-4-6") -> ClaudeAIClient:
    """Get a Claude client instance with the given token."""
    return ClaudeAIClient(token=token, model=model)
