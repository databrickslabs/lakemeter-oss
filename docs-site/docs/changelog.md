---
sidebar_position: 99
---

# Changelog

Lakemeter follows [Semantic Versioning](https://semver.org/):

- **Major** (X.0.0) — Schema migrations and breaking database changes
- **Minor** (0.X.0) — Data-only database updates
- **Patch** (0.0.X) — Application-only fixes with no database changes

---

## v0.1.1

*2026-08-01*

Patch release introducing safer upgrades and correcting AI Parse estimate persistence. No database schema or data migration is required.

- Added a version-aware upgrade utility with `status`, `plan`, `doctor`, `apply`, and `rollback` commands
- Added immutable runtime staging, authenticated health checks, concurrency locks, resumable execution, and automatic recovery
- Added Lakebase backup branches for future minor data updates and major schema migrations; patch upgrades never modify Lakebase
- Updated new installations to provision Lakebase Autoscaling projects, branches, and endpoints directly
- Fixed AI Parse fields so calculation method, complexity, DBU quantity, page count, mode, and page volume persist and clone correctly
- Added the [Upgrade Guide](./admin-guide/upgrading.md) and updated installer and deployment documentation

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
