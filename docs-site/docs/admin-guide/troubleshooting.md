---
sidebar_position: 5
---

# Troubleshooting

Common issues and their solutions when running Lakemeter.

![Troubleshooting guide documentation page](/img/guides/admin-troubleshooting-guide.png)
*The Troubleshooting guide — common issues organized by category with diagnostic commands.*

## Application Won't Start

### Check App Status

```bash
databricks apps get lakemeter -p your-profile
```

Look for the `status` field. If it shows an error, check the deployment logs in the Databricks Apps console.

### Check Health Endpoint

```bash
curl https://your-app-url.databricksapps.com/health
```

Expected response: `{"status": "healthy"}`

### Common Startup Issues

| Symptom | Cause | Solution |
|---------|-------|----------|
| App stuck in "deploying" | Missing dependencies | Check `requirements.txt` is complete |
| 500 error on load | Database connection failed | Check debug endpoint (see below) |
| Blank page | Frontend assets not built | Run `./deploy.sh` to rebuild and redeploy |
| App starts but no data | Pricing data not loaded | Re-run installer Step 5 |

## Database Connection Errors

### Diagnosing with Debug Endpoints

The most effective way to diagnose database issues is with the debug endpoint:

```bash
curl https://your-app-url.databricksapps.com/api/v1/debug/database
```

This returns:
- Environment variable values (passwords redacted)
- Token manager initialization status
- SP credential fetch status
- OAuth token generation result
- Database connection test result

### "Password authentication failed"

This usually means the OAuth token is invalid or the SP role was created incorrectly.

1. **Check SP role type**: The SP must use `identity_type=SERVICE_PRINCIPAL`, not `PG_ONLY`. See the [Permissions Guide](./permissions).
2. **Force token refresh**: `POST /api/v1/debug/database/refresh`
3. **Verify SP credentials**: Check the secret scope contains `sp_clientid` and `sp_secret` keys

### "Connection refused" or Timeout

- Verify the `DB_HOST` environment variable matches your Lakebase instance DNS
- Ensure the Lakebase instance is in `AVAILABLE` state:
  ```bash
  databricks database get-database-instance <instance-name> -p your-profile
  ```
- Check that the Lakebase instance hasn't been stopped or deleted

### Token Refresh Issues

The app proactively refreshes OAuth tokens every 30 minutes and recycles database connections every 15 minutes. If you see intermittent auth failures:

1. Check the debug database endpoint for token generation errors
2. Force a refresh: `POST /api/v1/debug/database/refresh`
3. If the error mentions "invalid authorization" or "authentication failed", the token manager automatically retries on the next request

## Pricing Data Issues

### Missing or Outdated Pricing

If cost calculations return zero or unexpected values:

1. Check that pricing data was loaded by the installer (Step 5)
2. Use the reference endpoint to verify data exists:
   ```bash
   curl https://your-app-url.databricksapps.com/api/v1/reference/pricing-bundle/status
   ```
3. Regenerate the pricing bundle if needed:
   ```bash
   curl -X POST https://your-app-url.databricksapps.com/api/v1/reference/pricing-bundle/regenerate
   ```

### Calculation Returns Error

- Verify the cloud, region, and tier combination is valid
- Check that the instance type exists for the selected cloud and region
- Ensure required fields are provided in the request

## AI Assistant Issues

### AI Not Responding

- The AI assistant requires access to Databricks Foundation Model API (FMAPI)
- Verify the service principal has FMAPI access
- Check the external API debug endpoint:
  ```bash
  curl https://your-app-url.databricksapps.com/api/v1/debug/external-api
  ```
- This shows whether SP tokens are available and tests a real API call

### Inaccurate AI Responses

The AI assistant may occasionally provide inaccurate pricing information. Always verify important pricing details against the [official Databricks pricing page](https://www.databricks.com/product/pricing).

## Deployment Issues

### Frontend Not Updating

After code changes, you must rebuild and redeploy:

```bash
# Option 1: Full automated deploy
./deploy.sh

# Option 2: Manual
cd frontend && npm ci && npm run build
cd ../backend && databricks apps deploy lakemeter --source-code-path . -p your-profile
```

:::tip
Do not restart the app — redeployment handles the restart automatically.
:::

### API Docs Not Visible

In production (`ENVIRONMENT=production`), the Swagger API docs at `/docs` and `/redoc` are disabled (the Docusaurus documentation site at `/docs/` is unaffected). To enable Swagger temporarily, set `ENVIRONMENT=development` in `app.yaml` and redeploy.

### CORS Errors

If you see CORS errors in the browser console:
- In production (same-origin): `CORS_ORIGINS` should be empty
- In development: `CORS_ORIGINS` defaults to `http://localhost:5173,http://localhost:3000,http://localhost:5175`
- For cross-origin access, add the origin to `CORS_ORIGINS` in `app.yaml`

## Performance

### Slow Page Load

- The React SPA is served as static files from FastAPI. First load may be slower due to asset download.
- Subsequent navigations are client-side and should be fast.
- If consistently slow, check the Databricks Apps resource allocation in the console.

### Slow Calculations

- Calculation endpoints query pricing data from Lakebase
- If the first request after startup is slow, it may be due to initial database connection setup
- Subsequent requests use the connection pool and should be fast

## Getting Help

If you encounter issues not covered here:

1. Check the debug endpoints (`/api/v1/debug/database`, `/api/v1/debug/external-api`, `/api/v1/debug/headers`)
2. Check the application logs in the Databricks Apps console
3. Verify your Databricks workspace and Lakebase instance are healthy
