---
sidebar_position: 99
---

# Changelog

Lakemeter follows [Semantic Versioning](https://semver.org/):

- **Major** (X.0.0) — Breaking changes, database migrations
- **Minor** (0.X.0) — New features, new workload types
- **Patch** (0.0.X) — Bug fixes, pricing data updates

---

## v0.1.0

*2026-07-24*

Initial public open-source release.

- Workload coverage for Jobs, All-Purpose, DBSQL, DLT/Lakeflow, Model Serving, FMAPI (Databricks + Proprietary), Vector Search, Lakebase, Databricks Apps, AI Parse, and Shutterstock ImageAI
- AI assistant with streaming chat, workload suggestions, and one-click accept
- Excel export with full cost breakdowns, SKU details, and discount calculations
- One-command installer (`scripts/install.sh`) using Databricks Asset Bundles
- Lakebase-backed estimate storage
- Multi-cloud support: AWS, Azure, GCP
- SSO authentication via Databricks Apps
- Interactive API docs at `/api/docs` and `/api/redoc`
