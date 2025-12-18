# Lakemeter API - Databricks App

FastAPI backend for Lakemeter cost calculator.

## Files

- `app.py` - FastAPI application
- `app.yaml` - Databricks App configuration
- `requirements.txt` - Python dependencies

## Deploy to Databricks Apps

```bash
cd api_backend
databricks apps create lakemeter-api --profile lakemeter --source-code-path .
```

## Get App URL

```bash
databricks apps get lakemeter-api --profile lakemeter
```

## Test API

```bash
# Health check
curl https://YOUR-APP-URL/health

# Get all regions
curl https://YOUR-APP-URL/api/v1/regions

# Get AWS regions
curl https://YOUR-APP-URL/api/v1/regions?cloud=AWS
```

## API Documentation

FastAPI auto-generates docs at:
- Swagger UI: `https://YOUR-APP-URL/docs`
- ReDoc: `https://YOUR-APP-URL/redoc`

## Update App

```bash
databricks apps update lakemeter-api --source-code-path .
```

## Delete App

```bash
databricks apps delete lakemeter-api
```

