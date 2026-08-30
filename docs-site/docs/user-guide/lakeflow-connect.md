---
sidebar_position: 8
---

# Lakeflow Connect API Sizing

Lakeflow Connect is currently available through Lakemeter's calculation API. It is not a supported workload form in the current release.

The calculation models two possible components:

1. A Lakeflow pipeline using serverless pipeline compute
2. An optional classic gateway for database connectors

## API endpoint

```text
POST /api/v1/calculate/lakeflow-connect
```

Example with direct monthly pipeline hours:

```json
{
  "cloud": "AWS",
  "region": "us-east-1",
  "tier": "PREMIUM",
  "dlt_edition": "ADVANCED",
  "hours_per_month": 100,
  "gateway_enabled": false
}
```

Run-based pipeline usage can be expressed with:

```json
{
  "runs_per_day": 2,
  "avg_runtime_minutes": 60,
  "days_per_month": 22
}
```

Do not send direct monthly hours and run-based usage in the same request.

## Optional gateway

Database connectors can require an always-on gateway. Enable it and provide the gateway configuration:

```json
{
  "gateway_enabled": true,
  "gateway_instance_type": "i3.xlarge",
  "gateway_pricing_tier": "on_demand",
  "gateway_payment_option": "NA",
  "gateway_hours_per_month": 730
}
```

The response separates pipeline and gateway costs. Gateway cost can include both Databricks DBUs and cloud VM infrastructure.

## Current limitation

The Lakeflow Connect calculation path has known pipeline, gateway SKU, and run-based validation defects tracked in [GitHub issue #8](https://github.com/databrickslabs/lakemeter-oss/issues/8). Treat results as preliminary and verify the returned SKU, DBUs, VM cost, and hours before using them externally.

## Related

- [Lakeflow Spark Declarative Pipelines](./dlt-pipelines)
- [Calculation Reference](./calculation-reference)
- [API Reference](../admin-guide/api-reference)
