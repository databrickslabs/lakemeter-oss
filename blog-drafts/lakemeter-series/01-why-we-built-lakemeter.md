# Why We Built Lakemeter: Open-Source Cost Estimation for Databricks Workloads

Lakemeter is now public and open source on Databricks Labs.

- GitHub: https://github.com/databrickslabs/lakemeter-oss
- Documentation: https://databrickslabs.github.io/lakemeter-oss/
- 5-minute tutorial: https://databrickslabs.github.io/lakemeter-oss/user-guide/getting-started
- v0.1.0 release: https://github.com/databrickslabs/lakemeter-oss/releases/tag/v0.1.0

![Suggested image: Lakemeter calculator page with a sample estimate](assets/lakemeter-calculator-page.png)

## The Problem We Kept Running Into

Lakemeter started as a small side project within the ASEAN + GCR field team.

The original problem was simple: Databricks sizing and pricing conversations can get complex quickly.

A customer might start with a straightforward question:

> “How much would this Databricks workload cost?”

But the answer often depends on many moving parts:

- Which cloud?
- Which region?
- Which pricing tier?
- Classic or serverless?
- Jobs, SQL, Lakeflow, AI, Lakebase, Vector Search, or something else?
- How many hours per month?
- Which DBU SKU?
- Is there storage involved?
- What assumptions should be shown to the customer?

The hard part is not just calculating a number. The hard part is making the estimate structured, explainable, repeatable, and easy to share.

That is why we built Lakemeter.

## What Lakemeter Is

Lakemeter is a Databricks cost estimation app designed to help teams create clearer, more structured estimates for Databricks workloads across clouds and regions.

It runs as a Databricks App, uses Lakebase as the backend database, and provides a guided way to build workload-level estimates with cost breakdowns that users can inspect and export.

At a high level, Lakemeter helps users:

- Create an estimate for a customer, project, or workload scenario.
- Add Databricks workloads such as Jobs, DBSQL, Lakeflow/DLT, Model Serving, FMAPI, Vector Search, Lakebase, Databricks Apps, AI Parse, and Shutterstock ImageAI.
- Review workload-level cost assumptions.
- See DBU, storage, and SKU-level breakdowns where applicable.
- Export estimates to Excel for customer conversations, planning, or internal review.
- Use an AI assistant to help draft workload configurations from natural language.

![Suggested image: expanded workload cost breakdown](assets/lakemeter-cost-breakdown.png)

## Why Open Source?

We decided to open-source Lakemeter because cost estimation works best when the logic is transparent.

Customers and partners should be able to inspect how estimates are built, deploy the app in their own Databricks environment, adapt it to their own workflows, and contribute feedback where assumptions can be improved.

Open source also makes the tool easier to share. Instead of treating the estimate as a black box, users can see the implementation, review the documentation, and understand the pricing basis behind each workload.

## Built as a Databricks App

Lakemeter is not just a spreadsheet or a static calculator.

It is a deployable application built on the Databricks platform:

- Frontend: React and TypeScript
- Backend: FastAPI
- Database: Lakebase
- Hosting: Databricks Apps
- Authentication: Databricks SSO
- AI assistance: Databricks Foundation Model APIs

This architecture lets Lakemeter run inside a Databricks workspace with managed authentication and a Lakebase-backed persistence layer.

## What v0.1.0 Includes

The initial public release includes:

- Databricks Apps deployment with SSO
- Lakebase-backed estimate storage
- Multi-cloud, region-specific pricing
- Workload-level cost breakdowns
- Excel export
- AI-assisted estimate creation
- One-command install flow
- Public documentation and a 5-minute tutorial

This is intentionally a v0.1.0 release. It is useful today, but it is also just the start.

## What Comes Next

There is still more to do.

Some of the areas we want to continue improving include:

- Publishing Lakemeter through Databricks Marketplace.
- Expanding workload coverage.
- Improving pricing freshness and release versioning.
- Adding more examples and templates.
- Making installation and upgrades easier.
- Continuing to refine the cost breakdowns based on customer and partner feedback.

## Thank You

A big thank you to the contributors who helped build and shape Lakemeter:

- Jun Yi Tiong
- Chang Shi Lim
- David O'Keeffe

Special thanks to Deepak Sekar and Vihag Gupta as project sponsors for helping initiate and support the project from the beginning, and to Jason Pohl for supporting the open-source initiative.

## Try It

If you are planning Databricks workloads and want a transparent, deployable way to estimate costs, please try Lakemeter, share feedback, and star the repo if you find it useful.

- GitHub: https://github.com/databrickslabs/lakemeter-oss
- 5-minute tutorial: https://databrickslabs.github.io/lakemeter-oss/user-guide/getting-started
- Release: https://github.com/databrickslabs/lakemeter-oss/releases/tag/v0.1.0

