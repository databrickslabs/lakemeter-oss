# Lakemeter

A Databricks cost estimation tool that runs as a **Databricks App** with built-in SSO authentication.

Create, manage, and export detailed pricing estimates for 16 Databricks workload types across AWS, Azure, and GCP.

![Lakemeter home page](/docs-site/static/img/home-page.png)

## Features

- **16 workload types** — Jobs, All-Purpose, DBSQL, DLT, Model Serving, FMAPI, Vector Search, Lakebase, Databricks Apps, AI Parse, Shutterstock ImageAI
- **AI assistant** — Describe your workload in natural language, review the suggestion, and accept with one click
- **Excel export** — Full cost breakdowns with SKU details, discount calculations, and VM pricing
- **Multi-cloud** — AWS, Azure, and GCP with region-specific pricing
- **One-command install** — Provisions Lakebase, loads pricing data, and deploys the app automatically

## Quick Start

```bash
git clone https://github.com/steven-tan_data/lakemeter-opensource.git
cd lakemeter-opensource

./scripts/install.sh --profile <your-cli-profile>
```

The installer provisions everything in ~15 minutes. You only need a [Databricks CLI](https://docs.databricks.com/aws/en/dev-tools/cli/profiles.html) configured with a workspace profile.

## Documentation

Full documentation is available at **[cheeyutan.github.io/lakemeter-opensource](https://cheeyutan.github.io/lakemeter-opensource/)**.

- [User Guide](https://cheeyutan.github.io/lakemeter-opensource/user-guide/overview) — How to create estimates, configure workloads, use the AI assistant, and export
- [Admin Guide](https://cheeyutan.github.io/lakemeter-opensource/admin-guide/deployment) — Installation, deployment inventory, and API reference
- [Changelog](https://cheeyutan.github.io/lakemeter-opensource/changelog) — Release history

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React, TypeScript, Tailwind CSS, Vite |
| Backend | FastAPI, SQLAlchemy, Pydantic |
| Database | Lakebase (managed PostgreSQL on Databricks) |
| AI | Claude via Databricks Foundation Model APIs |
| Hosting | Databricks Apps (SSO, managed compute) |

## License

MIT
