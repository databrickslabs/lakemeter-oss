---
sidebar_position: 99
---

# Changelog

Lakemeter follows [Semantic Versioning](https://semver.org/):

- **Major** (X.0.0) — Schema migrations and breaking database changes
- **Minor** (0.X.0) — Data-only database updates
- **Patch** (0.0.X) — Application-only fixes with no database changes

---

## v0.3.0

*Unreleased*

Data and application release expanding workload coverage, DSU accounting, estimate-level add-ons, and cross-surface calculation parity. The release includes reference-data updates but no Lakebase schema migration.

### New workload coverage

- Added AI Extract and AI Classify quantity-based estimates
- Added Unity AI Gateway inference-table and usage-tracking estimates
- Added Agent Evaluation labels, token, and synthetic-question estimates
- Added AI Runtime serverless GPU training for AWS and Azure
- Added Databricks Default Storage with stored-data and Tier 1 and Tier 2 operation DSUs
- Added standard and OpenTelemetry Zerobus ingestion using Jobs Serverless DBUs
- Refreshed Databricks and proprietary Foundation Model API catalogs

### Platform and export enhancements

- Added Enhanced Security and Compliance and Mission Critical Platform Add-ons, calculated from DBU and DSU Product Spend at List
- Added first-class DSU totals and regional `DATABRICKS_STORAGE` pricing
- Expanded Excel exports to 34 columns with DSU costs, a pre-add-on workload summary, a Platform Add-on section, and a final estimate summary
- Added AI Search reranker pricing and aligned AI Search and Lakebase storage with DSU-based calculations

### Calculation fixes

- Fixed All-Purpose Serverless rate parity
- Fixed saved always-on workloads so the UI, calculation APIs, and Excel consistently resolve missing usage to 730 hours
- Fixed Databricks Apps counts so multiple apps multiply DBUs and cost across the API, UI, and Excel
- Preserved explicit zero hours and run-based usage precedence

### Upgrade notes

- Applies data updates `020` through `027` for the new workload reference entries
- Does not add or alter Lakebase columns
- Use the [Upgrade Guide](./admin-guide/upgrading.md) to validate and apply the release from a clean checkout

---

## v0.1.2

*2026-08-08*

Code-only patch release focused on calculation accuracy, estimate persistence,
and safer release validation. No Lakebase schema change, data migration, or
pricing refresh is required.

### Bug fixes

- [Issue #10](https://github.com/databrickslabs/lakemeter-oss/issues/10):
  Fixed AI-generated estimate application so authenticated requests persist
  supported workload configuration and roll back cleanly on failure
- [Issue #11](https://github.com/databrickslabs/lakemeter-oss/issues/11):
  Fixed regional VM pricing parity across the UI and Excel exports for Jobs,
  All-Purpose, DLT/Lakeflow, and DBSQL workloads
- [Issue #9](https://github.com/databrickslabs/lakemeter-oss/issues/9):
  Fixed daily, monthly, and run-based usage normalization across calculation
  APIs
- [Issue #7](https://github.com/databrickslabs/lakemeter-oss/issues/7):
  Fixed Databricks Apps estimates to use the correct serverless compute SKU
  and reject unsupported workload types instead of silently falling back
- Fixed AI Parse and Shutterstock ImageAI quantity fields so saved estimates,
  cloned estimates, and Excel exports retain the entered values
- Fixed Lakebase responses to report the effective billable hours used by the
  calculation

### Security and release reliability

- Updated frontend and documentation dependencies to address known security
  alerts
- Added a tested release-candidate gate that validates installation, upgrade,
  end-to-end behavior, and rollback before release assets can be published

### Upgrade notes

- Supports code-only upgrades from `v0.1.0` and `v0.1.1`
- Leaves Lakebase online and does not modify existing estimates, database
  schema, or pricing data
- Use the [Upgrade Guide](./admin-guide/upgrading.md) to run `plan`, `doctor`,
  `apply`, and rollback validation from a clean `v0.1.2` checkout

---

## v0.1.1

*2026-08-01*

Patch release introducing safer upgrades and correcting AI Parse estimate persistence. No database schema or data migration is required.

### New capabilities

- Added a version-aware upgrade utility with `status`, `plan`, `doctor`, `apply`, and `rollback` commands
- Added immutable runtime staging, authenticated health checks, concurrency locks, resumable execution, and automatic recovery
- Added Lakebase backup branches for future minor data updates and major schema migrations; patch upgrades never modify Lakebase
- Updated new installations to provision Lakebase Autoscaling projects, branches, and endpoints directly

### Bug fixes

- Fixed AI Parse fields so calculation method, complexity, DBU quantity, page count, mode, and page volume persist and clone correctly

### Documentation updates

- Added the [Upgrade Guide](./admin-guide/upgrading.md) and updated installer and deployment documentation

---

## v0.1.0

*2026-07-24*

Initial public open-source release.

- Workload coverage for Jobs, All-Purpose, DBSQL, DLT/Lakeflow, Model Serving, FMAPI (Databricks + Proprietary), AI Search, Lakebase, Databricks Apps, AI Parse, and Shutterstock ImageAI
- AI assistant with streaming chat, workload suggestions, and one-click accept
- Excel export with full cost breakdowns, SKU details, and discount calculations
- One-command installer (`scripts/install.sh`) using Databricks Asset Bundles
- Lakebase-backed estimate storage
- Multi-cloud support: AWS, Azure, GCP
- SSO authentication via Databricks Apps
- Interactive API docs at `/api/docs` and `/api/redoc`
