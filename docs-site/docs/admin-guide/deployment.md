---
sidebar_position: 1
---

# Getting Started

Lakemeter is a **Databricks App** — a managed web application with built-in SSO authentication that runs entirely on the Databricks platform.

## Prerequisites

You need:

- An **AWS or Azure Databricks workspace** in a
  [Lakebase-supported region](https://docs.databricks.com/en/oltp/projects/manage-projects.html)
- A **Databricks CLI** configured with a
  [workspace profile](https://docs.databricks.com/aws/en/dev-tools/cli/profiles.html)

Lakemeter must be hosted on AWS or Azure because Lakebase Autoscaling is not
available for this installer on GCP. Once installed, the app can still create
workload estimates for AWS, Azure, and GCP. All other permissions (Lakebase,
secret scopes, Apps, serverless compute) are granted to workspace users by
default.

:::tip No local CLI? Use the notebook terminal
If you can't install the Databricks CLI locally, you can run the installer directly from your workspace. Create any notebook on a serverless cluster, click the **terminal button** (bottom-right corner), and use the pre-installed CLI — no profile needed since it's already authenticated.

![Notebook with terminal button highlighted](/img/guides/notebook-terminal-button.png)
*Click the terminal button in the bottom-right corner of any notebook.*

![Terminal open with Databricks CLI available](/img/guides/notebook-terminal-cli.png)
*The Databricks CLI is pre-installed and authenticated in the notebook terminal.*

```bash
# In the notebook terminal — CLI is pre-installed and authenticated
git clone <repository-url>
cd lakemeter-oss
./scripts/install.sh --non-interactive
```
:::

## Install

```bash
git clone <repository-url>
cd lakemeter-oss

./scripts/install.sh --profile <your-cli-profile>
```

The installer provisions everything automatically: a direct Lakebase
Autoscaling project, database schema, pricing data, app configuration, and
deployment. See the [Installer Guide](./installer) for the full walkthrough.

For a list of all resources created by the installer, see the [Deployment Inventory](./deployment-inventory).

## After Installation

Once the installer completes, your app is live at:

```
https://lakemeter-<workspace-id>.<cloud>.databricksapps.com
```

Users access the app through their Databricks workspace — authentication is handled automatically via SSO. No additional user setup is required.

## Updating

Use the version-aware upgrade utility from a clean checkout of the release you
want to install:

```bash
git fetch --tags
git checkout <release-tag>
git status --short  # should return no output

./scripts/upgrade.sh plan --profile <your-cli-profile>
./scripts/upgrade.sh doctor --profile <your-cli-profile>
./scripts/upgrade.sh apply --profile <your-cli-profile>
```

See the [Upgrade Guide](./upgrading) for release policy, database backups,
idempotency, verification, and rollback.
