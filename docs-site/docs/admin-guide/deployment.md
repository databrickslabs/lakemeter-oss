---
sidebar_position: 1
---

# Getting Started

Lakemeter is a **Databricks App** — a managed web application with built-in SSO authentication that runs entirely on the Databricks platform.

## Prerequisites

You need a **Databricks CLI** configured with a [workspace profile](https://docs.databricks.com/aws/en/dev-tools/cli/profiles.html). All other permissions (Lakebase, secret scopes, Apps, serverless compute) are granted to workspace users by default.

:::tip No local CLI? Use the notebook terminal
If you can't install the Databricks CLI locally, you can run the installer directly from your workspace. Create any notebook on a serverless cluster, click the **terminal button** (bottom-right corner), and use the pre-installed CLI — no profile needed since it's already authenticated.

![Notebook with terminal button highlighted](/img/guides/notebook-terminal-button.png)
*Click the terminal button in the bottom-right corner of any notebook.*

![Terminal open with Databricks CLI available](/img/guides/notebook-terminal-cli.png)
*The Databricks CLI is pre-installed and authenticated in the notebook terminal.*

```bash
# In the notebook terminal — CLI is pre-installed and authenticated
git clone <repository-url>
cd lakemeter-opensource
./scripts/install.sh --non-interactive
```
:::

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
https://lakemeter-<workspace-id>.<cloud>.databricksapps.com
```

Users access the app through their Databricks workspace — authentication is handled automatically via SSO. No additional user setup is required.

## Updating

To update Lakemeter after a new release:

```bash
git pull
./scripts/install.sh --profile <your-cli-profile>
```

The installer is idempotent — re-running it updates pricing data and redeploys the app without losing existing estimates.
