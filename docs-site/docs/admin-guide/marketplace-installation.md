---
sidebar_position: 2
---

# Install Lakemeter from Databricks Marketplace

Lakemeter can be installed directly from Databricks Marketplace as a managed
Databricks App. The Marketplace package includes the application and its
pricing reference data, so no local CLI, installer notebook, personal access
token, or separate data upload is required.

## Prerequisites

A Databricks workspace administrator must prepare the resources and perform
the installation. The administrator needs permission to install Marketplace
apps, create or select Lakebase resources, select a Model Serving endpoint,
and grant those resources to the new app.

Prepare both resources before starting the Marketplace installation.

### Empty Lakebase database

Provision a dedicated Lakebase Autoscaling project and database for Lakemeter
with the following configuration:

| Setting | Requirement |
| --- | --- |
| Cloud | AWS or Azure |
| Region | A region that supports Lakebase Autoscaling |
| Project | A new project dedicated to this Lakemeter installation |
| Branch | `production`, or another dedicated writable branch |
| Database | An empty database; the default `databricks_postgres` database is supported |
| Compute | Default capacity is sufficient; enable scale-to-zero if desired |
| App permission | `CAN_CONNECT_AND_CREATE` |

The database must not already contain a `lakemeter` schema created by another
Lakemeter app. Each installation receives its own Databricks App service
principal, which creates and owns the schema during first-start bootstrap.
Reusing a schema owned by another app identity causes a permission error.

Do not create tables or load pricing data manually. Lakemeter creates its
schema, tables, calculation functions, and reference data automatically when
the app first starts.

### Claude Model Serving endpoint

Prepare a running Databricks Model Serving endpoint backed by a Claude model.
Any Claude endpoint available for the intended users' use can be selected,
provided it supports the Databricks chat-completions request format.

During installation, Lakemeter binds the endpoint as `claude-endpoint` with
`CAN_QUERY`. The app service principal uses that permission when an end user
invokes the AI assistant. Users do not provide endpoint credentials to
Lakemeter.

Check the endpoint's availability and rate limits before installation. A
throttled endpoint affects the optional AI assistant but not manual estimates,
calculations, or Excel export.

## Installation flow

### 1. Find Lakemeter in Marketplace

In the Databricks workspace, open **Marketplace**, search for **Lakemeter**,
and select **Lakemeter - Databricks Cost Estimation App**.

![Find Lakemeter in Databricks Marketplace](/img/guides/marketplace-search.png)

Select **Install** on the listing page.

### 2. Configure the app resources

Under **Database**, select the dedicated Lakebase project, writable branch,
and empty database prepared for this installation.

Under **Serving endpoint**, select the prepared Claude endpoint. Keep the
default app compute configuration unless your organization requires a
different size or instance count.

![Configure the Lakebase database and Claude endpoint](/img/guides/marketplace-configure-resources.png)

The package requests these resource permissions:

| Resource key | Resource | Permission |
| --- | --- | --- |
| `postgres` | Selected Lakebase database | `CAN_CONNECT_AND_CREATE` |
| `claude-endpoint` | Selected Model Serving endpoint | `CAN_QUERY` |

Select **Next**.

### 3. Review authorizations

Review the permissions shown by Databricks and confirm that the selected
Lakebase database and Model Serving endpoint are the intended resources.
Continue only after the authorization review is complete.

### 4. Add metadata and install

Enter an app name and description. The app name cannot be changed after the
app is created. Select the serverless usage policy required by your
organization, then select **Install**.

![Add the app metadata and install Lakemeter](/img/guides/marketplace-add-metadata.png)

### 5. Wait for the app to start

Databricks creates the app identity, grants the two bound resources, deploys
the Marketplace package, and starts the app. On first start, Lakemeter
automatically:

1. Connects to Lakebase with a short-lived OAuth database credential.
2. Creates the `lakemeter` schema and application tables.
3. Installs the calculation functions and reference records.
4. Loads the packaged pricing data, including cloud VM pricing.
5. Records the installed application version and pricing checksum.

Wait until the app status is **Running** and the active deployment is
**Succeeded**, then select **Open app**. No additional bootstrap or pricing
data step is required.
