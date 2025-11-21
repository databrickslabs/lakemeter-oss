Based on the user's description, respond with ONLY valid JSON (no markdown, no code blocks, no backticks) in the format below while setting the defaultValue of each attributes with the following context:

# Workload
Set the defaultValue of "Workload" based on the user input with the following context:
- Ingestion: Data loading, importing, or ingesting from sources
- Transformation: Data cleaning, processing, or transforming
- Analysis: Data analysis, aggregation, or statistical operations
- Exploration: Data exploration, discovery, or ad-hoc querying
- ML Inference: Machine learning model inference or predictions

# SKU
Set the defaultValue of "SKU" based on user input with the folowing context:

## Lakeflow Jobs
Orchestrate data processing, machine learning, and analytics pipelines on the Databricks Data Intelligence Platform.​

SKUs:
- Jobs Classic: Self-managed solution that allows you to configure and optimize underlying infrastructure for your ETL workloads.​
- Jobs Serverless: Fully managed serverless platform requiring minimal additional configuration. Available in two modes: Performance Optimized (for fast launches and execution) and Standard (for all other workloads).​

## Lakeflow Declarative Pipelines
Reliable streaming and batch data pipelines made easy on the Databricks Lakehouse Platform.​

SKUs:
- LDP Serverless: Fully managed platform to run your pipelines, requiring minimal additional configuration. Recommended for users seeking managed service.​
- LDP Classic Core: Requires customers to manage their own cloud infrastructure and provides additional control and configuration.​ Easily build scalable streaming or batch pipelines in SQL and Python
- LDP Classic Pro: Requires customers to manage their own cloud infrastructure and provides additional control and configuration. Easily build scalable streaming or batch pipelines in SQL and Python and handle change data capture (CDC) from any data source
- LDP Classic Advanced: Requires customers to manage their own cloud infrastructure and provides additional control and configuration. Easily build scalable streaming or batch pipelines in SQL and Python, handle change data capture (CDC) and maximize your data credibility with quality expectations and monitoring


## Lakeflow Connect
Built-in connectors for ingesting data from enterprise applications and databases.​

SKUs:
- Lakeflow Connect: Easily ingest data from key business systems with built-in connectors.

Databricks SQL
Run all SQL and BI applications at scale with high price-performance, unified governance, open formats, and broad tool integration.​

SKUs:
- SQL Classic: Run interactive SQL queries for data exploration on a self-managed SQL warehouse
- SQL Pro: Get better performance and extend the SQL experience on the lakehouse for exploratory SQL, SQL ETL/ELT, data science and ML on a self-managed SQL warehouse
- SQL Serverless: Get the best performance for high-concurrency BI and extend the SQL experience on the lakehouse for exploratory SQL, SQL ETL/ELT, data science and ML on a fully managed, elastic, serverless SQL warehouse hosted in the customer's Databricks account.

## Interactive Workloads
Run interactive data science and machine learning workloads. Also good for data engineering, BI and data analytics.

SKUs:
- Classic All-Purpose: Run interactive data science and machine learning workloads. Also good for data engineering, BI and data analytics.
- Serverless All-Purpose: Fully managed, elastic serverless platform to run interactive workloads.

# Driver Instance
Set the defaultValue of "Driver Instance" to "i3.xlarge"

# Worker Instance
Set the defaultValue of "Worker Instance" to "i3.xlarge"

# Worker Count
Set the defaultValue of "Worker Count" to "1"

IMPORTANT: Return ONLY the JSON object below, without any markdown formatting, code blocks, or backticks:

{
  "tableStructure": [
    {
      "attribute": "Workload",
      "inputType": "dropdown",
      "defaultValue": ""
    },
    {
      "attribute": "SKU",
      "inputType": "dropdown",
      "defaultValue": ""
    },
    {
      "attribute": "Driver Instance",
      "inputType": "dropdown",
      "defaultValue": ""
    },
    {
      "attribute": "Worker Instance",
      "inputType": "dropdown",
      "defaultValue": ""
    },
    {
      "attribute": "Worker Count",
      "inputType": "dropdown",
      "defaultValue": "1"
    },
    {
      "attribute": "Run Duration",
      "inputType": "text",
      "defaultValue": ""
    },
    {
      "attribute": "Run Freq.",
      "inputType": "text",
      "defaultValue": ""
    }
  ]
}