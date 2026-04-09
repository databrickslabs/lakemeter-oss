---
sidebar_position: 5
---

# Architecture

Lakemeter is built as a full-stack application on the Databricks platform, using FastAPI for the backend, React for the frontend, and Lakebase (managed PostgreSQL) for persistent storage.

![Architecture documentation page](/img/guides/admin-architecture-guide.png)
*The Architecture guide — system diagram, backend structure, and module organization.*

## System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     Databricks Apps                          │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              FastAPI Backend (Python 3.11)              │  │
│  │                                                        │  │
│  │  ┌──────────┐  ┌──────────┐  ┌─────────────────────┐  │  │
│  │  │ REST API │  │ Static   │  │ AI Agent Service    │  │  │
│  │  │ Routes   │  │ Files    │  │ (FMAPI + Tools)     │  │  │
│  │  └─────┬────┘  │ (React)  │  └──────────┬──────────┘  │  │
│  │        │       └──────────┘             │              │  │
│  │  ┌─────▼────────────────────────────────▼──────────┐  │  │
│  │  │           Service Layer                         │  │  │
│  │  │  ├── Calculation Engine (export/calculations)   │  │  │
│  │  │  ├── Pricing Bundle Manager                     │  │  │
│  │  │  ├── Export Engine (Excel/XLSX, 10 modules)     │  │  │
│  │  │  └── AI Client (Foundation Model API)           │  │  │
│  │  └──────────┬──────────────────────────────────────┘  │  │
│  │             │                                          │  │
│  │  ┌──────────▼──────────────────────────────────────┐  │  │
│  │  │    Auth Layer (OAuth Token Manager)              │  │  │
│  │  │    SP credentials → OAuth token → Lakebase      │  │  │
│  │  └──────────┬──────────────────────────────────────┘  │  │
│  │             │                                          │  │
│  │  ┌──────────▼──────────────────────────────────────┐  │  │
│  │  │           Data Layer (SQLAlchemy ORM)           │  │  │
│  │  │  ├── Estimates          ├── Templates           │  │  │
│  │  │  ├── Line Items         ├── Sharing             │  │  │
│  │  │  ├── Users              ├── Conversations       │  │  │
│  │  │  ├── Decision Records   ├── Workload Types      │  │  │
│  │  │  ├── VM Pricing         ├── SKU Region Map      │  │  │
│  │  │  └── Instance DBU Rates                         │  │  │
│  │  └──────────┬──────────────────────────────────────┘  │  │
│  └─────────────┼──────────────────────────────────────────┘  │
│                │                                              │
│  ┌─────────────▼──────────────────────────────────────────┐  │
│  │           Lakebase (Managed PostgreSQL)                 │  │
│  │  Database: lakemeter_pricing                           │  │
│  │  Schema: lakemeter (app tables + sync pricing tables)  │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │           Databricks APIs                              │  │
│  │  ├── Foundation Model API (AI assistant)                │  │
│  │  ├── Database Credential API (OAuth tokens)             │  │
│  │  └── Secret Scope (SP credentials)                      │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React 19 + TypeScript | Interactive SPA with real-time cost calculation |
| **UI Framework** | Tailwind CSS + Heroicons | Responsive styling and iconography |
| **State** | Zustand | Client-side state management |
| **API Layer** | FastAPI (Python 3.11) | REST API, serves React static assets |
| **ORM** | SQLAlchemy 2.x | Database access and model definitions |
| **Settings** | Pydantic Settings | Environment variable management |
| **Database** | Lakebase (PostgreSQL) | Transactional data (estimates, line items, users, pricing) |
| **AI** | Foundation Model API | AI assistant for pricing Q&A and estimate generation |
| **Export** | xlsxwriter | Excel report generation with live formulas |
| **Auth** | Databricks Apps SSO + SP OAuth M2M | User auth (SSO) and DB auth (SP tokens) |
| **Hosting** | Databricks Apps | Managed deployment with TLS and scaling |

## Backend Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI entry point, CORS, SPA routing, debug endpoints
│   ├── config.py            # Pydantic Settings (env vars, logging)
│   ├── database.py          # SQLAlchemy engine with OAuth token refresh
│   ├── external_api.py      # External pricing API client
│   ├── auth/                # Authentication layer
│   │   ├── databricks_auth.py  # SSO header extraction
│   │   └── token_manager.py    # SP OAuth token lifecycle
│   ├── models/              # SQLAlchemy ORM models (11 models)
│   │   ├── estimate.py         # Estimate model
│   │   ├── line_item.py        # LineItem model (all workload types)
│   │   ├── user.py             # User model
│   │   ├── template.py         # Template model
│   │   ├── workload_type.py    # RefWorkloadType model
│   │   ├── sharing.py          # Sharing model
│   │   ├── conversation.py     # ConversationMessage model
│   │   ├── decision_record.py  # DecisionRecord model
│   │   ├── vm_pricing.py       # VMPricing model
│   │   ├── sku_region_map.py   # SKURegionMap model
│   │   └── instance_dbu_rates.py  # InstanceDBURates model
│   ├── schemas/             # Pydantic request/response schemas
│   │   ├── estimate.py
│   │   ├── line_item.py
│   │   └── ...
│   ├── routes/              # API route handlers (9 routers)
│   │   ├── estimates.py        # /api/v1/estimates
│   │   ├── line_items.py       # /api/v1/line-items
│   │   ├── workload_types.py   # /api/v1/workload-types
│   │   ├── users.py            # /api/v1/users
│   │   ├── calculate.py        # /api/v1/calculate/*
│   │   ├── reference.py        # /api/v1/reference/*
│   │   ├── vm_pricing.py       # /api/v1/vm-pricing/*
│   │   ├── chat.py             # /api/v1/chat/*
│   │   └── export/             # /api/v1/export/* (modular)
│   │       ├── routes.py          # Export endpoints
│   │       ├── calculations.py    # Cost calculation logic
│   │       ├── pricing.py         # Pricing data lookup
│   │       ├── excel_builder.py   # Excel workbook assembly
│   │       ├── excel_row_writer.py # Per-row Excel output
│   │       ├── excel_columns.py   # Column definitions
│   │       ├── excel_formats.py   # Cell formatting
│   │       ├── excel_sections.py  # Totals, summary, legend
│   │       ├── excel_item_helpers.py # Workload-type helpers
│   │       └── helpers.py         # Shared utilities
│   └── services/            # Business logic
│       ├── ai_agent.py         # AI assistant with tool use
│       └── ai_client.py        # FMAPI client wrapper
├── static/                  # Built React frontend assets + docs
│   ├── index.html
│   ├── assets/              # JS + CSS bundles
│   ├── docs/                # Built Docusaurus docs (post-deploy)
│   └── pricing/             # Pricing data JSON files (9 files)
├── app.yaml                 # Databricks App configuration
└── requirements.txt         # Python dependencies
```

## Frontend Structure

```
frontend/
├── src/
│   ├── App.tsx              # Root component with routing
│   ├── main.tsx             # Entry point
│   ├── api/
│   │   └── client.ts        # API client with typed methods
│   ├── components/
│   │   ├── Layout.tsx        # App shell with navigation
│   │   ├── ChatPanel.tsx     # AI assistant side panel
│   │   ├── WorkloadForm.tsx  # Workload configuration form
│   │   └── SearchableSelect.tsx  # Filterable dropdown component
│   ├── pages/
│   │   ├── Calculator.tsx    # Main workload calculator page
│   │   ├── Estimates.tsx     # Estimate list/management page
│   │   ├── EstimateDetail.tsx  # Single estimate with workloads
│   │   └── TestCalculations.tsx  # Calculation debugging page
│   ├── store/
│   │   └── useStore.ts       # Zustand state management
│   ├── hooks/
│   │   └── useTheme.ts       # Dark mode theme hook
│   ├── utils/
│   │   ├── costCalculation.ts    # Client-side cost formulas
│   │   └── pricingBundle.ts      # Pricing data from bundle
│   └── types/
│       └── index.ts          # TypeScript type definitions
└── package.json
```

## Data Flow

### Cost Calculation

1. User configures a workload in the Calculator UI
2. Frontend computes cost in real-time using `costCalculation.ts` and the local pricing bundle
3. When the user saves, the line item is persisted to Lakebase via the REST API
4. On export, the backend recalculates costs using `export/calculations.py` and writes Excel formulas

### Export Pipeline

```
User clicks Export → GET /api/v1/export/estimate/{id}/excel
  → Load estimate + line items from DB
  → For each line item:
      → Calculate hours, DBU/hr, monthly DBUs
      → Look up SKU and pricing
      → Write Excel row with live formulas
  → Write totals, summary, legend sections
  → Return .xlsx binary
```

### AI Assistant

```
User sends message → POST /api/v1/chat (or /api/v1/chat/stream for SSE)
  → AI Agent (FMAPI with tool use)
  → Tools: create_estimate, add_workload, search_pricing, ...
  → Streaming SSE response (content, tool results, proposed workloads)
  → Optional: Apply generated estimate → POST /api/v1/chat/{id}/apply
  → Optional: Confirm proposed workload → POST /api/v1/chat/{id}/confirm-workload
```

## Authentication Flow

```
Browser → Databricks Apps Proxy (adds auth headers)
  → FastAPI reads X-Forwarded-Email, X-Forwarded-User
  → Auto-creates user record on first access
  → All API calls scoped to authenticated user
```

For database access, the app uses SP OAuth M2M:

```
App startup → Token Manager reads SP credentials from secret scope
  → Exchanges credentials for OAuth token via generate_database_credential()
  → Token used as PostgreSQL password (cached, refreshed every 30 min)
  → SQLAlchemy pool recycles connections every 15 min
```

No additional OAuth or token management is required by the admin — the token manager handles everything automatically.

## Pricing Data

Pricing data is loaded as a **pricing bundle** — a JSON structure containing DBU rates, VM pricing, FMAPI token rates, and model serving rates for all clouds, regions, and tiers. The data flows through:

1. **Static JSON files** in `backend/static/pricing/` (9 files, updated from Databricks pricing APIs)
2. **Loaded into Lakebase** by the installer (`scripts/install_lakemeter.py` Step 5)
3. **Served to the frontend** as a pricing bundle on page load
4. **Used by the export engine** for Excel formula generation

Both frontend and backend use the same pricing source, ensuring consistency between browser-displayed costs and exported reports.

## Test Architecture

### AI Assistant Tests (FastAPI TestClient)

```
pytest → FastAPI TestClient (in-process)
  → POST /api/v1/chat (natural language prompt)
  → AI Agent (Claude via FMAPI) → propose_workload tool
  → Assert proposed_workload fields
  → Confirm/reject via /api/v1/chat/{id}/confirm-workload
```

Tests run against the real backend with real AI calls. Module-scoped fixtures share expensive AI responses across test methods.

### Calculation Tests (Direct Function Calls)

```
pytest → import frontend_calc_dlt() / backend calc functions
  → Construct test workload with known inputs
  → Assert calculated outputs match expected values
  → Generate real .xlsx → verify formulas with openpyxl
```

No AI calls needed — tests validate calculation logic directly. Runs in under 2 seconds.

See the [Testing Guide](/testing/overview) for full details on running and extending the test suite.
