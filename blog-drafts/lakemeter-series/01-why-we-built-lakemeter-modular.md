# Article 1 Modular Draft: Why We Built Lakemeter

Use this file as modular building blocks. Each module can be edited, removed, expanded, or rearranged independently before assembling the final Medium article.

## Module 0: Title and Deck

Title:

**From Cost Guesswork to Clear Databricks Estimates: Meet Lakemeter**

Subtitle:

**An open-source Databricks App that helps teams turn workload assumptions into transparent, shareable cost estimates.**

## Module 1: A Better Way to Plan Databricks Costs

Lakemeter is now public and open source on Databricks Labs, making it easier for teams, customers, and partners to create transparent Databricks cost estimates before workloads go live.

This is a milestone I am personally excited about because Lakemeter was built to solve a practical problem: how do we make Databricks sizing and pricing conversations faster, clearer, and more consistent?

Links:

- GitHub: https://github.com/databrickslabs/lakemeter-oss
- Documentation: https://databrickslabs.github.io/lakemeter-oss/
- 5-minute tutorial: https://databrickslabs.github.io/lakemeter-oss/user-guide/getting-started
- v0.1.0 release: https://github.com/databrickslabs/lakemeter-oss/releases/tag/v0.1.0

[FIGURE 1 PLACEHOLDER: Lakemeter OSS GitHub repository]

Caption: Lakemeter is now available as an open-source project on Databricks Labs.

Suggested file: `assets/lakemeter-github-repo.png`

## Module 2: Why a Simple Cost Question Gets Complicated

Lakemeter started from a practical customer-facing challenge.

Every Databricks sizing conversation can require pulling together pricing assumptions, workload configuration, region and cloud differences, DBU rates, VM costs, storage costs, and exportable notes in a way that is clear enough to discuss with stakeholders.

We wanted something more structured than a one-off spreadsheet, but still practical enough for real customer conversations.

That is where Lakemeter started.

A customer might ask a simple question:

> How much would this Databricks workload cost?

But the answer usually depends on many details:

- Which cloud is the workload running on?
- Which region?
- Which Databricks tier?
- Is the workload classic or serverless?
- Is it Jobs, DBSQL, Lakeflow, Model Serving, FMAPI, Vector Search, Lakebase, or something else?
- How many hours per month does it run?
- Which DBU SKU applies?
- Are there VM costs, storage costs, or token-based costs?
- What assumptions should be documented for the customer?

The hard part is not just calculating a number. The hard part is creating an estimate that is structured, explainable, repeatable, and easy to share.

[FIGURE 2 PLACEHOLDER: From manual cost planning to structured estimates]

Caption: Lakemeter helps turn workload assumptions into a repeatable cost estimation workflow.

Suggested file: `assets/lakemeter-walkthrough.mp4`

## Module 3: Meet Lakemeter

Lakemeter is a Databricks cost estimation app designed to help teams create clearer, more structured estimates for Databricks workloads across clouds and regions.

It runs as a Databricks App, uses Lakebase as the backend database, and provides a guided way to build workload-level estimates with cost breakdowns that users can inspect and export.

At a high level, Lakemeter helps users:

- Create estimates for customer, partner, or internal planning scenarios.
- Add Databricks workloads such as Jobs, DBSQL, Lakeflow/DLT, Model Serving, FMAPI, Vector Search, Lakebase, Databricks Apps, AI Parse, and Shutterstock ImageAI.
- Review workload-level cost assumptions.
- Inspect DBU, storage, SKU, token, and VM cost breakdowns where applicable.
- Export estimates to Excel.
- Use an AI assistant to help draft workload configurations from natural language.

[FIGURE 3 PLACEHOLDER: Lakemeter calculator view]

Caption: The calculator page shows workload-level estimates and a live cost summary.

Suggested file: `assets/lakemeter-calculator-page.png`

## Module 4: Why Transparency Matters

We decided to open-source Lakemeter because cost estimation works best when the logic is transparent.

Customers and partners should be able to inspect how estimates are built, understand the assumptions behind the calculations, and deploy the app in their own Databricks environment if they want more control.

Open source also makes it easier for the community to share feedback. If a workload assumption can be improved, a pricing edge case is missing, or a deployment flow can be simplified, the implementation is visible and can evolve.

That transparency matters when the output is used in planning, architecture, and budget conversations.

## Module 5: What the First Release Includes

The first public release focuses on the core workflow: helping users move from a rough workload idea to a structured, shareable Databricks cost estimate.

### Start with a clear estimate scope

The workflow begins by creating an estimate for a customer, project, proof of concept, or planning scenario. The user selects the target cloud, region, and pricing tier at the estimate level.

Setting this context up front matters because Databricks pricing can vary by cloud, region, tier, and SKU. It also prevents these choices from becoming hidden assumptions inside an isolated spreadsheet cell. Anyone reviewing the estimate can immediately understand the environment being modeled.

[FIGURE 4 PLACEHOLDER: Creating a new estimate]

Caption: Every estimate begins with an explicit cloud, region, and pricing tier.

Suggested file: `assets/lakemeter-create-estimate.png`

### Build the estimate workload by workload

After establishing the estimate scope, users add the workloads that make up the architecture. Instead of forcing every product into one generic form, Lakemeter provides workload-specific configuration fields that reflect the way each service is consumed.

The first release covers common Databricks workload patterns, including:

- Jobs and batch data processing
- All-Purpose Compute
- Databricks SQL warehouses
- Lakeflow Spark Declarative Pipelines / DLT
- Model Serving
- Foundation Model APIs for Databricks-hosted and proprietary models
- Vector Search
- Lakebase
- Databricks Apps
- AI Parse
- Shutterstock ImageAI

The inputs change with the workload. A Jobs estimate can capture driver and worker configuration, runtime, execution frequency, Photon, and VM pricing assumptions. A DBSQL estimate can capture warehouse type, size, cluster count, and operating hours. An FMAPI estimate can capture provider, model, token type, endpoint type, context length, and monthly token volume. A Lakebase estimate can model compute range, scale-to-zero behavior, nodes, usage hours, and storage.

This workload-specific approach makes the estimate easier to build and easier to review because each line reflects the actual service being discussed.

[FIGURE 5 PLACEHOLDER: Adding and configuring a workload]

Caption: Each workload uses configuration inputs that match its pricing model.

Suggested file: `assets/lakemeter-add-workload.png`

### See the estimate update as assumptions change

Lakemeter recalculates the estimate as users adjust workload settings. The calculator shows the cost of each workload alongside an overall cost summary, making it easy to understand which services contribute most to the estimate.

This is useful during an interactive planning conversation. A user can change worker count, runtime, warehouse size, usage hours, token volume, storage, or another relevant input and immediately see the modeled impact.

The goal is not to claim that an early estimate is an invoice prediction. The goal is to make planning assumptions explicit and make scenario discussions faster. Teams can explore questions such as:

- What happens if this workload runs every day instead of only on business days?
- How does a different warehouse size affect the monthly estimate?
- How much of the total is compute versus storage?
- Which workload is the main cost driver?
- What changes if the deployment moves to a different region or pricing tier?

[FIGURE 6 PLACEHOLDER: Calculator with multiple workloads and live cost summary]

Caption: Workload-level costs and the total estimate update as configuration assumptions change.

Suggested file: `assets/lakemeter-estimate-with-workloads.png`

### Inspect the calculation instead of trusting a black box

Every workload can be expanded to show the calculation details behind the displayed cost. Depending on the workload, this may include usage hours, DBU consumption, regional price per DBU, VM assumptions, storage quantities, token rates, SKU selection, and the resulting monthly cost.

This detail is especially valuable in customer and partner conversations. Rather than presenting a number without context, the estimate can be reviewed step by step. Reviewers can challenge an assumption, change it, and see the effect.

That transparency also makes it easier to distinguish between:

- Databricks DBU cost and cloud VM cost
- Serverless and classic compute assumptions
- Compute, storage, and backup-related costs
- Hourly and token-based consumption
- List pricing and any separately modeled discounts

[FIGURE 7 PLACEHOLDER: Expanded workload calculation breakdown]

Caption: Lakemeter exposes the assumptions and formulas behind each workload estimate.

Suggested file: `assets/lakemeter-cost-breakdown.png`

### Use AI assistance without giving up control

The first release includes an AI assistant that can help turn a natural-language requirement into a proposed workload configuration.

For example, a user might describe a nightly ETL pipeline, a serverless analytics warehouse, or a model serving endpoint. The assistant can propose a relevant Lakemeter workload and populate an initial set of configuration values.

The proposal is not applied silently. The user can review it, edit the assumptions, and decide whether to accept it. This keeps the human in control while reducing the effort required to translate an architecture discussion into the calculator.

[FIGURE 8 PLACEHOLDER: AI assistant proposing a workload configuration]

Caption: The AI assistant proposes a configuration that users can review, modify, and accept.

Suggested file: `assets/lakemeter-ai-assistant.png`

### Export a shareable planning artifact

Once the estimate is ready, it can be exported to Excel. The export carries the estimate context, workload configurations, pricing details, cost breakdowns, assumptions, and notes into a portable format.

This makes the output useful beyond the calculator itself. The spreadsheet can support:

- Customer follow-up discussions
- Budget and architecture reviews
- Internal approval workflows
- RFP and proposal preparation
- Partner planning sessions
- Comparison of alternative scenarios

The exported file is still an estimate, not a bill or contractual quote, but it gives everyone a common artifact to review and refine.

[FIGURE 9 PLACEHOLDER: Lakemeter Excel export]

Caption: Excel export turns the estimate into a portable artifact for planning and follow-up discussions.

Suggested file: `assets/lakemeter-excel-export.png`

Together, these steps form the core v0.1.0 workflow: define the scenario, add workloads, review the assumptions, inspect the calculations, use AI where helpful, and export the result.

This first release already supports an end-to-end estimation conversation, while leaving room for more workload coverage, examples, templates, and distribution options in future releases.

[FIGURE 10 PLACEHOLDER: Lakemeter v0.1.0 release page]

Caption: The v0.1.0 release marks the first public open-source release of Lakemeter.

Suggested file: `assets/lakemeter-v0.1.0-release.png`

## Module 6: What Comes Next—and How You Can Help

Lakemeter v0.1.0 establishes the core estimation workflow, but it is only the starting point.

The next phase will focus on three areas that can make Lakemeter more useful in real planning conversations.

### Model discounts directly in an estimate

List pricing is a useful starting point, but many planning conversations also need to account for discounts. We want to make it easier to model discount assumptions directly in Lakemeter and see their effect clearly in the workload breakdown, estimate total, and exported spreadsheet.

The goal is not to replace customer-specific commercial guidance. It is to let users distinguish list price from an explicitly stated planning assumption, without hiding that adjustment inside a separate spreadsheet.

### Make estimates easier to share within an organization

Cost estimates are rarely created for one person. They are reviewed by solution architects, account teams, platform owners, partners, finance teams, and other stakeholders.

We want to improve how estimates can be shared and reused within an organization, so teams can collaborate on the same assumptions instead of circulating disconnected spreadsheet copies. Over time, this could make it easier to review an estimate, learn from previous sizing work, and use an existing scenario as the starting point for a new one.

### Expand workload coverage

Databricks continues to grow, and Lakemeter needs to grow with it. We plan to support more workloads and continue refining the existing calculators as pricing models and customer needs evolve.

We also want community feedback to help determine what comes next. If an important workload is missing, an assumption needs to be clearer, or a calculation could be easier to validate, opening an issue gives us a concrete place to discuss and improve it.

This is why open-sourcing Lakemeter matters: the roadmap can be shaped by the people using it in real customer and partner conversations.

If Lakemeter is useful to you, try it, share it with your team, star the repository, and tell us what you would like to see next.

- GitHub: https://github.com/databrickslabs/lakemeter-oss
- 5-minute tutorial: https://databrickslabs.github.io/lakemeter-oss/user-guide/getting-started
- Release: https://github.com/databrickslabs/lakemeter-oss/releases/tag/v0.1.0

[FIGURE 11 PLACEHOLDER: Lakemeter GitHub repository]

Caption: Star the repository, open an issue, and help shape the next phase of Lakemeter.

Suggested file: `assets/lakemeter-github-repo.png`

## Suggested Assembly Order

1. Module 0: Title and Deck
2. Module 1: A Better Way to Plan Databricks Costs
3. Module 2: Why a Simple Cost Question Gets Complicated
4. Module 3: Meet Lakemeter
5. Module 4: Why Transparency Matters
6. Module 5: What the First Release Includes
7. Module 6: What Comes Next—and How You Can Help

## Optional Shorter Version

If the Medium article feels too long, combine:

- Module 1 and Module 2 into one opening/problem section.
- Module 5 and Module 6 into one “What is included and what comes next” section.

