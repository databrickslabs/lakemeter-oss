---
sidebar_position: 1
---

# Installation Options

Lakemeter is a Databricks App with built-in workspace SSO. There are two
supported installation methods.

## Preferred: Databricks Marketplace

Installing from Databricks Marketplace is the preferred method for most
workspaces.

- Installation is performed in the Databricks UI.
- No local CLI, installer notebook, or personal access token is required.
- The application and pricing reference data are packaged together.
- Databricks manages the app identity and grants its selected resources during
  installation.
- New releases are reviewed and applied through the Marketplace update flow.

A workspace administrator prepares an empty Lakebase database and a Claude
Model Serving endpoint in the same workspace, then installs Lakemeter from its
Marketplace listing.

See [Marketplace Installation (Preferred)](./marketplace-installation) for the
complete walkthrough.

## Alternative: install from source

Use the source installer when the Marketplace listing is unavailable in your
workspace, or when you need to operate a customized source deployment.

The source installer requires a Databricks CLI workspace profile and runs a
Databricks Asset Bundles workflow. It provisions Lakebase, creates the
database, loads pricing data, configures the app, deploys it, and verifies the
installation.

See [Install from Source](./installer) for installation and
[Upgrade a Source Installation](./upgrading) for subsequent releases.

## Deployment inventory

The source installer creates additional jobs, secrets, workspace files, and
installation state that are not part of the Marketplace workflow. See the
[Source Deployment Inventory](./deployment-inventory) when operating a source
installation.
