"""
Chat API Routes for AI Assistant

Provides endpoints for conversing with the AI assistant to create and manage estimates.
"""
import json
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.databricks_auth import get_current_user
from app.external_api import get_user_token, get_model_serving_token
from app.services.ai_agent import create_agent, EstimateAgent
from app.config import log_info, log_warning, log_error


router = APIRouter(prefix="/chat", tags=["AI Assistant"])


# Request/Response models
class ChatMessage(BaseModel):
    """A single chat message."""
    role: str  # 'user' or 'assistant'
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None


class ChatRequest(BaseModel):
    """Request to send a message to the AI assistant."""
    message: str
    conversation_id: Optional[str] = None
    estimate_context: Optional[Dict[str, Any]] = None
    workloads_context: Optional[List[Dict[str, Any]]] = None
    mode: str = "estimate"  # 'estimate' for full features, 'home' for Q&A only
    stream: bool = True


class ChatResponse(BaseModel):
    """Response from the AI assistant."""
    content: str
    conversation_id: str
    tool_results: Optional[List[Dict[str, Any]]] = None
    estimate: Optional[Dict[str, Any]] = None
    workloads: Optional[List[Dict[str, Any]]] = None
    proposed_workload: Optional[Dict[str, Any]] = None  # Workload awaiting confirmation


class ConfirmWorkloadRequest(BaseModel):
    """Request to confirm or reject a proposed workload."""
    proposal_id: str
    confirmed: bool = True


# In-memory conversation storage (for MVP - should use Redis/DB in production)
_conversation_agents: Dict[str, EstimateAgent] = {}


def _get_or_create_agent(conversation_id: str, token: str, mode: str = "estimate") -> EstimateAgent:
    """Get existing agent or create new one for a conversation."""
    if conversation_id not in _conversation_agents:
        _conversation_agents[conversation_id] = create_agent(token, mode=mode)
    else:
        # Update token and mode for existing agent
        _conversation_agents[conversation_id].client.set_token(token)
        _conversation_agents[conversation_id].set_mode(mode)
    return _conversation_agents[conversation_id]


def _cleanup_old_conversations():
    """Clean up old conversation agents to prevent memory leaks."""
    # Simple cleanup: keep only last 100 conversations
    if len(_conversation_agents) > 100:
        # Remove oldest half
        keys_to_remove = list(_conversation_agents.keys())[:50]
        for key in keys_to_remove:
            del _conversation_agents[key]


@router.post("", response_model=ChatResponse)
@router.post("/", response_model=ChatResponse)
async def chat(
    request: Request,
    chat_request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Send a message to the AI assistant and get a response.
    
    For non-streaming responses. Use /chat/stream for streaming.
    """
    # Get app token for Claude API (SP token has model-serving scope)
    token = get_model_serving_token(request)
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required for AI assistant"
        )

    # Get or create conversation agent
    import uuid
    conversation_id = chat_request.conversation_id or str(uuid.uuid4())
    
    _cleanup_old_conversations()
    agent = _get_or_create_agent(conversation_id, token, mode=chat_request.mode)
    
    # Set estimate context if provided (only for estimate mode)
    if chat_request.mode == "estimate" and (chat_request.estimate_context or chat_request.workloads_context):
        agent.set_context(
            chat_request.estimate_context or {},
            chat_request.workloads_context or []
        )
    
    try:
        # Get response from agent
        result = await agent.chat(chat_request.message)
        
        return ChatResponse(
            content=result["content"],
            conversation_id=conversation_id,
            tool_results=result.get("tool_results"),
            estimate=result.get("estimate"),
            workloads=result.get("workloads"),
            proposed_workload=result.get("proposed_workload")
        )
    
    except Exception as e:
        log_error(f"Chat error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"AI assistant error: {str(e)}"
        )


@router.post("/stream")
async def chat_stream(
    request: Request,
    chat_request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Send a message to the AI assistant and stream the response.
    
    Returns Server-Sent Events (SSE) with chunks of the response.
    Event types:
    - content: Text content chunk
    - tool_start: Tool execution starting
    - tool_result: Tool execution result
    - done: Stream complete with final state
    - error: Error occurred
    """
    # Get app token for Claude API (SP token has model-serving scope)
    token = get_model_serving_token(request)
    if not token:
        async def error_generator():
            yield f"data: {json.dumps({'type': 'error', 'content': 'Authentication required'})}\n\n"
        return StreamingResponse(
            error_generator(),
            media_type="text/event-stream"
        )
    
    # Get or create conversation agent
    import uuid
    conversation_id = chat_request.conversation_id or str(uuid.uuid4())
    
    _cleanup_old_conversations()
    agent = _get_or_create_agent(conversation_id, token, mode=chat_request.mode)
    
    # Set estimate context if provided (only for estimate mode)
    if chat_request.mode == "estimate" and (chat_request.estimate_context or chat_request.workloads_context):
        agent.set_context(
            chat_request.estimate_context or {},
            chat_request.workloads_context or []
        )
    
    async def generate():
        """Generate SSE events from the agent's streaming response."""
        try:
            # Send conversation ID first
            yield f"data: {json.dumps({'type': 'start', 'conversation_id': conversation_id})}\n\n"
            
            async for chunk in agent.chat_stream(chat_request.message):
                # Convert chunk to SSE format
                yield f"data: {json.dumps(chunk)}\n\n"
            
        except Exception as e:
            log_error(f"Stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
        
        finally:
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.delete("/{conversation_id}")
async def clear_conversation(
    conversation_id: str,
    request: Request
):
    """Clear a conversation's history and state."""
    if conversation_id in _conversation_agents:
        _conversation_agents[conversation_id].reset()
        del _conversation_agents[conversation_id]
    
    return {"success": True, "message": "Conversation cleared"}


@router.post("/{conversation_id}/apply")
async def apply_estimate(
    conversation_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Apply the AI-generated estimate to create actual database records.
    
    This converts the draft estimate and workloads into real saved records.
    """
    from app.models.estimate import Estimate
    from app.models.line_item import LineItem
    from app.auth.databricks_auth import get_current_user
    
    if conversation_id not in _conversation_agents:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    agent = _conversation_agents[conversation_id]
    
    if not agent.current_estimate:
        raise HTTPException(status_code=400, detail="No estimate to apply")
    
    try:
        # Get current user
        user = get_current_user(request, db)
        
        # Get estimate name (support both 'name' and 'estimate_name')
        est_name = agent.current_estimate.get("name") or agent.current_estimate.get("estimate_name", "AI Generated Estimate")
        
        # Create the estimate
        estimate = Estimate(
            estimate_name=est_name,  # Use correct field name
            cloud=agent.current_estimate.get("cloud", "aws"),
            region=agent.current_estimate.get("region", "us-east-1"),
            tier="PREMIUM",
            description=agent.current_estimate.get("description", "Created by AI Assistant"),
            owner_user_id=user.user_id
        )
        db.add(estimate)
        db.flush()  # Get the estimate_id
        
        # Create line items from confirmed proposed workloads
        created_workloads = []
        # Note: proposed_workloads that are confirmed should be used
        workloads_to_create = agent.proposed_workloads if agent.proposed_workloads else []
        for workload in workloads_to_create:
            line_item = LineItem(
                estimate_id=estimate.estimate_id,
                workload_name=workload["workload_name"],
                workload_type=workload["workload_type"],
                serverless_enabled=workload.get("serverless_enabled", False),
                photon_enabled=workload.get("photon_enabled", False),
                driver_node_type=workload.get("driver_node_type"),
                worker_node_type=workload.get("worker_node_type"),
                num_workers=workload.get("num_workers"),
                hours_per_month=workload.get("hours_per_month", 730),
                runs_per_day=workload.get("runs_per_day"),
                avg_runtime_minutes=workload.get("avg_runtime_minutes"),
                days_per_month=workload.get("days_per_month", 22),
                driver_pricing_tier=workload.get("driver_pricing_tier", "on_demand"),
                worker_pricing_tier=workload.get("worker_pricing_tier", "spot"),
                dlt_edition=workload.get("dlt_edition"),
                dbsql_warehouse_type=workload.get("dbsql_warehouse_type"),
                dbsql_warehouse_size=workload.get("dbsql_warehouse_size"),
                dbsql_num_clusters=workload.get("dbsql_num_clusters"),
                lakebase_cu=workload.get("lakebase_cu"),
                lakebase_ha_nodes=workload.get("lakebase_ha_nodes"),
                notes=f"Created by AI Assistant"
            )
            db.add(line_item)
            created_workloads.append(workload["workload_name"])
        
        db.commit()
        
        # Clear the conversation after successful apply
        agent.reset()
        
        return {
            "success": True,
            "estimate_id": str(estimate.estimate_id),
            "estimate_name": estimate.estimate_name,
            "workloads_created": len(created_workloads),
            "message": f"Created estimate '{estimate.estimate_name}' with {len(created_workloads)} workloads"
        }
    
    except Exception as e:
        db.rollback()
        log_error(f"Apply estimate error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create estimate: {str(e)}"
        )


@router.get("/{conversation_id}/state")
async def get_conversation_state(
    conversation_id: str,
    request: Request
):
    """Get the current state of a conversation (estimate and workloads)."""
    if conversation_id not in _conversation_agents:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    agent = _conversation_agents[conversation_id]
    
    return {
        "conversation_id": conversation_id,
        "estimate": agent.current_estimate,
        "workloads": agent.current_workloads,
        "proposed_workloads": agent.proposed_workloads,
        "message_count": len(agent.conversation_history)
    }


@router.post("/{conversation_id}/confirm-workload")
async def confirm_workload(
    conversation_id: str,
    confirm_request: ConfirmWorkloadRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Confirm or reject a proposed workload.
    
    If confirmed, creates the workload via the regular line_items API.
    """
    from app.models.line_item import LineItem
    
    if conversation_id not in _conversation_agents:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    agent = _conversation_agents[conversation_id]
    
    if confirm_request.confirmed:
        # Get the confirmed workload configuration
        workload = agent.confirm_workload(confirm_request.proposal_id)
        
        if not workload:
            raise HTTPException(status_code=404, detail="Proposal not found")
        
        # Return the workload config for the frontend to create via regular API
        # This allows the UI to update properly via Zustand
        # Pass through ALL fields from the confirmed workload to preserve AI-proposed values
        # Only exclude internal tracking fields
        _INTERNAL_FIELDS = {
            "proposal_id", "status", "reason", "cloud",
            "total_users", "concurrent_queries", "use_case_type",
            "query_selectivity", "query_complexity", "typical_data_volume",
            "model_serving_type", "model_serving_scale_to_zero",
            "vector_search_endpoint_type",
            "lakebase_expected_reads_per_sec", "lakebase_expected_bulk_writes_per_sec",
            "lakebase_expected_incremental_writes_per_sec", "lakebase_avg_row_size_kb",
            "lakebase_ha_enabled", "lakebase_num_read_replicas",
            "jobs_worker_min", "jobs_worker_max",
        }
        workload_config = {
            k: v for k, v in workload.items()
            if k not in _INTERNAL_FIELDS and v is not None
        }
        # Ensure notes field has a value
        if not workload_config.get("notes"):
            workload_config["notes"] = f"Created by AI Assistant: {workload.get('reason', '')}"

        return {
            "success": True,
            "action": "confirmed",
            "workload_config": workload_config,
            "message": f"Workload '{workload['workload_name']}' confirmed. Use the returned config to create via /api/v1/estimates/{{estimate_id}}/line-items"
        }
    else:
        # Reject the proposal
        if agent.reject_workload(confirm_request.proposal_id):
            return {
                "success": True,
                "action": "rejected",
                "message": "Workload proposal rejected"
            }
        else:
            raise HTTPException(status_code=404, detail="Proposal not found")
