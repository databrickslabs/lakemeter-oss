# Discovery Report: Lakemeter App

## Project Overview
- **Name**: Lakemeter - Databricks Cost Estimation Tool
- **Tech stack**: Python (FastAPI) + React (Vite/TypeScript) + PostgreSQL (Lakebase)
- **Backend**: FastAPI with SQLAlchemy ORM, Databricks-hosted Claude AI integration
- **Frontend**: React 18 + Vite + TypeScript + Tailwind CSS + Zustand state management
- **Docs**: Docusaurus docs site with GitHub Pages deployment
- **Deploy target**: Databricks Apps (lakemeter-oss)

## Architecture Map

### Backend
- **Framework**: FastAPI (Python)
- **Entry point**: `backend/app/main.py`
- **Routes**: estimates, line-items, chat (AI), export, reference data, workload-types, users, vm-pricing
- **Database**: Lakebase (PostgreSQL-compatible) via SQLAlchemy
- **Auth**: Databricks OAuth with token management
- **AI Service**: Databricks-hosted Claude via OpenAI-compatible API

### Frontend
- **Framework**: React 18 + Vite + TypeScript
- **State**: Zustand store (`useStore.ts`)
- **Styling**: Tailwind CSS with dark mode support
- **Pages**: Calculator (main), EstimateDetail, Estimates list, TestCalculations
- **Key components**: ChatPanel (AI assistant), WorkloadForm, SearchableSelect, Layout

## Critical Bugs Found

### BUG A: Workload Type Dropdown Broken for New Types
- **Root cause**: `backend/app/routes/workload_types.py:13-221` — `DEFAULT_WORKLOAD_TYPES` only has 9 types (JOBS through LAKEBASE), missing DATABRICKS_APPS, AI_PARSE, SHUTTERSTOCK_IMAGEAI
- **Symptom**: API returns 9 types, frontend's `selectedWorkloadType` is undefined for new types, shows "Unknown workload type" error with Lakeflow Jobs selected in dropdown
- **Fix**: Add DATABRICKS_APPS, AI_PARSE, SHUTTERSTOCK_IMAGEAI to `DEFAULT_WORKLOAD_TYPES` in backend

### BUG B: AI Assistant URL Protocol Error
- **Root cause**: `backend/app/services/ai_client.py:28` — `DATABRICKS_HOST` env var on Databricks Apps may not include `https://` protocol prefix
- **Symptom**: AI chat shows "Error: Request URL is missing an http:// or https:// protocol"
- **Fix**: Ensure `DATABRICKS_HOST` always has `https://` prefix before constructing endpoint URL

### BUG C: AI Assistant Accept Button Populates Defaults
- **Root cause**: `backend/app/routes/chat.py:366-387` — `confirm-workload` endpoint's `workload_config` response only maps a subset of fields, missing many AI-proposed fields
- **Missing fields**: `databricks_apps_size`, `ai_parse_mode/complexity/pages`, `shutterstock_images`, `vector_search_mode/capacity/storage_gb`, `model_serving_gpu_type/concurrency/scale_out`, `fmapi_provider/model/endpoint_type/context_length/rate_type/quantity`, `serverless_mode`, `lakebase_storage_gb/pitr_gb/snapshot_gb/backup_retention_days`
- **Fix**: Pass through ALL workload fields from the confirmed proposal instead of hardcoding a subset

## Work Classification

### Fix Sprints
1. **[Fix]: Missing workload types in API** — Severity: CRITICAL
2. **[Fix]: AI URL protocol error** — Severity: CRITICAL  
3. **[Fix]: Accept button drops AI-proposed values** — Severity: CRITICAL

### Extend Sprints
4. **[Extend]: Installation test from fresh clone** — validate end-to-end
5. **[Extend]: Documentation update for all recent changes**
