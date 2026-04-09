# Lakemeter Backend

FastAPI backend for the Databricks Pricing Calculator.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your database credentials
```

4. Run the development server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Database

The backend connects to a Databricks Lakebase (PostgreSQL-compatible) database with the following schema:

- `lakemeter.users` - User accounts
- `lakemeter.estimates` - Pricing estimates
- `lakemeter.line_items` - Individual workload configurations
- `lakemeter.templates` - Estimate templates
- `lakemeter.ref_workload_types` - Reference workload type configurations
- `lakemeter.sharing` - Estimate sharing
- `lakemeter.conversation_messages` - AI conversation history
- `lakemeter.decision_records` - Decision tracking

## Key Endpoints

### Estimates
- `GET /api/v1/estimates` - List all estimates
- `POST /api/v1/estimates` - Create new estimate
- `GET /api/v1/estimates/{id}` - Get estimate details
- `PUT /api/v1/estimates/{id}` - Update estimate
- `DELETE /api/v1/estimates/{id}` - Delete estimate
- `POST /api/v1/estimates/{id}/duplicate` - Duplicate estimate

### Line Items
- `GET /api/v1/line-items/estimate/{id}` - List line items for estimate
- `POST /api/v1/line-items` - Create line item
- `PUT /api/v1/line-items/{id}` - Update line item
- `DELETE /api/v1/line-items/{id}` - Delete line item

### Export
- `GET /api/v1/export/estimate/{id}/excel` - Export estimate to Excel
- `GET /api/v1/export/estimates/excel` - Export all estimates summary

### Reference Data
- `GET /api/v1/reference/clouds` - Cloud providers and regions
- `GET /api/v1/reference/instance-types/{cloud}` - Instance types by cloud
- `GET /api/v1/reference/dbsql-sizes` - SQL Warehouse sizes
- `GET /api/v1/reference/dlt-editions` - DLT editions
- `GET /api/v1/reference/fmapi-models` - Foundation models


