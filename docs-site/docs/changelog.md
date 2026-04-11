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

*2026-04-11*

Initial open-source release.

- 16 workload types: Jobs, All-Purpose, DBSQL, DLT, Model Serving, FMAPI (Databricks + Proprietary), Vector Search, Lakebase, Databricks Apps, AI Parse, Shutterstock ImageAI
- AI assistant with streaming chat, workload suggestions, and one-click accept
- Excel export with full cost breakdowns, SKU details, and discount calculations
- One-command installer (`scripts/install.sh`) using Databricks Asset Bundles
- Lakebase backend with 19 stored cost calculation functions
- Multi-cloud support: AWS, Azure, GCP
- SSO authentication via Databricks Apps
- Interactive API docs at `/api/docs` and `/api/redoc`
