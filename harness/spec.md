# Lakemeter Harness Spec — AI Assistant Bug Fixes + Installer + Docs

## Existing Project Context
- **Discovery report**: harness/discovery/discovery-report.md
- **Current quality baseline**: 7/10 (core features work, 3 critical AI bugs)
- **Quality target**: 9.5/10

## Sprint Plan

### Sprint 1: Fix All AI Assistant Problems (Critical Bugs)
**Type**: Fix | **Priority**: Critical

#### BUG A: Missing workload types in API response
- Add DATABRICKS_APPS, AI_PARSE, SHUTTERSTOCK_IMAGEAI to `DEFAULT_WORKLOAD_TYPES` in `backend/app/routes/workload_types.py`
- Also add these types to `propose_workload` tool enum in `backend/app/services/ai_agent.py`
- Also add them to SYSTEM_PROMPT workload type list in `ai_agent.py`

#### BUG B: AI URL protocol error
- Fix `DATABRICKS_HOST` handling in `backend/app/services/ai_client.py` to ensure `https://` prefix
- Databricks Apps runtime may set DATABRICKS_HOST without protocol

#### BUG C: Accept button populates defaults instead of AI-proposed values
- Fix `confirm-workload` endpoint in `backend/app/routes/chat.py` to pass through ALL workload fields from proposal
- Replace hardcoded field mapping with dynamic passthrough of confirmed workload dict

#### Testing Requirements
- Verify all 12 workload types show correctly in dropdown
- Test AI chat API endpoints directly 
- Verify AI accept preserves non-default values

### Sprint 2: Installation Test (Fresh Clone Validation)
**Type**: Extend
- Clone from https://github.com/steven-tan_data/lakemeter-opensource
- Run installer, validate all workload types, calculate costs, export

### Sprint 3: Full Documentation Update + Deploy
**Type**: Extend
- Update Docusaurus docs for new workload types
- Deploy to GitHub Pages
