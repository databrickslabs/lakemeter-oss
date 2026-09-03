# Lakemeter

[![Databricks Labs](https://img.shields.io/badge/Databricks-Labs-FF3621?logo=databricks&logoColor=white)](https://www.databricks.com/learn/labs)
[![CI](https://github.com/databrickslabs/lakemeter-oss/actions/workflows/ci.yml/badge.svg)](https://github.com/databrickslabs/lakemeter-oss/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/databrickslabs/lakemeter-oss)](https://github.com/databrickslabs/lakemeter-oss/releases/latest)
[![Documentation](https://img.shields.io/badge/docs-online-blue)](https://databrickslabs.github.io/lakemeter-oss/)
[![GitHub stars](https://img.shields.io/github/stars/databrickslabs/lakemeter-oss?style=social)](https://github.com/databrickslabs/lakemeter-oss/stargazers)

**Estimate Databricks workload costs in minutes—with transparent assumptions you can review, share, and export.**

Lakemeter is an open-source cost estimation and workload sizing tool that runs as a **Databricks App** with built-in SSO. Configure expected usage, calculate regional costs, and export a detailed Excel estimate instead of maintaining sizing spreadsheets by hand.

![Lakemeter cost summary showing workload costs and detailed breakdowns](docs-site/static/img/gifs/cost-summary.gif)

## What you can estimate

**Compute and SQL**

- [Lakeflow Jobs](https://databrickslabs.github.io/lakemeter-oss/user-guide/jobs-compute)
- [All-Purpose Compute](https://databrickslabs.github.io/lakemeter-oss/user-guide/all-purpose-compute)
- [Lakeflow Spark Declarative Pipelines](https://databrickslabs.github.io/lakemeter-oss/user-guide/dlt-pipelines)
- [Databricks SQL warehouses](https://databrickslabs.github.io/lakemeter-oss/user-guide/dbsql-warehouses)

**AI, ML, and data services**

- [Model Serving](https://databrickslabs.github.io/lakemeter-oss/user-guide/model-serving)
- [Vector Search](https://databrickslabs.github.io/lakemeter-oss/user-guide/vector-search)
- [Databricks-hosted foundation models](https://databrickslabs.github.io/lakemeter-oss/user-guide/fmapi-databricks)
- [Proprietary foundation models](https://databrickslabs.github.io/lakemeter-oss/user-guide/fmapi-proprietary)
- [Lakebase](https://databrickslabs.github.io/lakemeter-oss/user-guide/lakebase)
- [Databricks Apps](https://databrickslabs.github.io/lakemeter-oss/user-guide/databricks-apps)
- [AI Parse](https://databrickslabs.github.io/lakemeter-oss/user-guide/ai-parse)
- [Shutterstock ImageAI](https://databrickslabs.github.io/lakemeter-oss/user-guide/shutterstock-imageai)

See the [workload sizing catalog](https://databrickslabs.github.io/lakemeter-oss/user-guide/workloads) for the inputs and calculation behavior of every workload.

## Why Lakemeter

- **Transparent calculations** — Review usage quantities, billing units, SKUs, rates, VM costs, storage, and discounts behind every total.
- **Workload-specific sizing** — Use forms tailored to each supported Databricks workload rather than a generic calculator.
- **AI-assisted estimates** — Describe a workload in natural language, review the suggested configuration, and accept it with one click.
- **Excel export** — Generate a detailed workbook for customer conversations, procurement reviews, RFPs, and internal planning.
- **Cloud and region awareness** — Model the cloud, region, tier, and pricing options available in the app.
- **Built for teams** — Create, duplicate, share, and compare multi-workload estimates in a Databricks workspace.

## Quick start

You need a Databricks workspace and a configured [Databricks CLI profile](https://docs.databricks.com/aws/en/dev-tools/cli/profiles.html).

```bash
git clone https://github.com/databrickslabs/lakemeter-oss.git
cd lakemeter-oss

./scripts/install.sh --profile <your-cli-profile>
```

The one-command installer provisions Lakebase, loads pricing data, deploys the app, and verifies the installation. It typically completes in **5–15 minutes**.

For permissions, deployment inventory, non-interactive installation, and troubleshooting, see the [installation guide](https://databrickslabs.github.io/lakemeter-oss/admin-guide/installer).

## See the workflow

Add workload assumptions and calculate their estimated cost:

![Adding and configuring a workload](docs-site/static/img/gifs/adding-workload.gif)

Export the completed estimate to Excel:

![Exporting a Lakemeter estimate to Excel](docs-site/static/img/gifs/export-excel.gif)

## Documentation

- [User guide](https://databrickslabs.github.io/lakemeter-oss/user-guide/overview) — Create estimates, inspect pricing, use AI assistance, and export
- [Workload sizing guides](https://databrickslabs.github.io/lakemeter-oss/user-guide/workloads) — Inputs and calculation behavior for every supported workload
- [Admin guide](https://databrickslabs.github.io/lakemeter-oss/admin-guide/deployment) — Installation, architecture, permissions, and API reference
- [Changelog](https://databrickslabs.github.io/lakemeter-oss/changelog) — Releases and upgrade notes

## Contributing

Bug reports, feature requests, documentation improvements, and pull requests are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) before contributing, or [open an issue](https://github.com/databrickslabs/lakemeter-oss/issues/new) to start a discussion.

If Lakemeter helps you size or explain a Databricks workload, consider [starring the repository](https://github.com/databrickslabs/lakemeter-oss) so others can discover it.

## Technology

- **Frontend:** React, TypeScript, Tailwind CSS, Vite
- **Backend:** FastAPI, SQLAlchemy, Pydantic
- **Database:** Lakebase (managed PostgreSQL on Databricks)
- **AI:** Claude through Databricks Foundation Model APIs
- **Hosting:** Databricks Apps with SSO and managed compute

## License

Copyright (2026) Databricks, Inc. This software includes software developed at Databricks and is subject to [LICENSE.md](LICENSE.md). Third-party dependency notices are provided in [NOTICE.md](NOTICE.md).
