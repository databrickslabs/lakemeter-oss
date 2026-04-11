---
sidebar_position: 1
---

# Getting Started

Lakemeter is a **Databricks App** — a managed web application with built-in SSO authentication that runs entirely on the Databricks platform.

## Prerequisites

- **Databricks CLI** installed and configured with a workspace profile ([installation guide](https://docs.databricks.com/en/dev-tools/cli/install.html))

All required permissions (Lakebase, secret scopes, Apps, serverless compute) are granted to workspace users by default. No special admin setup is needed.

## Install

```bash
git clone <repository-url>
cd lakemeter-opensource

./scripts/install.sh --profile <your-cli-profile>
```

The installer provisions everything automatically in **~15 minutes**: Lakebase instance, database schema, pricing data, app configuration, and deployment. See the [Installer Guide](./installer) for the full walkthrough.

For a list of all resources created by the installer, see the [Deployment Inventory](./deployment-inventory).

## After Installation

Once the installer completes, your app is live at:

```
https://lakemeter-<workspace-id>.aws.databricksapps.com
```

Users access the app through their Databricks workspace — authentication is handled automatically via SSO. No additional user setup is required.

## Updating

To update Lakemeter after a new release:

```bash
git pull
./scripts/install.sh --profile <your-cli-profile>
```

The installer is idempotent — re-running it updates pricing data and redeploys the app without losing existing estimates.
