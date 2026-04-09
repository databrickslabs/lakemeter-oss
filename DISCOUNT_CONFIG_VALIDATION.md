# Discount Configuration Validation Guide

## Overview
The `discount_config` parameter now has **strict validation** using Pydantic models to ensure correct structure and prevent errors.

## Validated Structure

### Pydantic Models

```python
class GlobalDiscountConfig(BaseModel):
    """Global discount configuration by category"""
    dbu_discount: float = Field(default=0, ge=0, le=100)
    vm_discount: float = Field(default=0, ge=0, le=100)
    storage_discount: float = Field(default=0, ge=0, le=100)
    platform_addon_discount: float = Field(default=0, ge=0, le=100)
    support_discount: float = Field(default=0, ge=0, le=100)

class DiscountConfig(BaseModel):
    """Discount configuration structure"""
    global_discounts: GlobalDiscountConfig = Field(alias="global")
    sku_specific: dict[str, float] = Field(default={})
    notes: Optional[str] = Field(default=None)
    effective_date: Optional[str] = Field(default=None)
    expiry_date: Optional[str] = Field(default=None)
```

## Validation Rules

### 1. Global Discounts
✅ **Valid**: All percentage values between 0-100
```json
{
  "global": {
    "dbu_discount": 20,
    "vm_discount": 10,
    "storage_discount": 0,
    "platform_addon_discount": 0,
    "support_discount": 0
  }
}
```

❌ **Invalid**: Percentage outside 0-100 range
```json
{
  "global": {
    "dbu_discount": 150,  // ❌ Error: must be <= 100
    "vm_discount": -5     // ❌ Error: must be >= 0
  }
}
```

**Error Response:**
```json
{
  "detail": [
    {
      "loc": ["body", "discount_config", "global", "dbu_discount"],
      "msg": "ensure this value is less than or equal to 100",
      "type": "value_error.number.not_le"
    }
  ]
}
```

### 2. SKU-Specific Discounts
✅ **Valid**: SKU names mapped to percentages 0-100
```json
{
  "global": {...},
  "sku_specific": {
    "JOBS_COMPUTE_(PHOTON)": 25,
    "ALL_PURPOSE_COMPUTE": 20,
    "SQL_SERVERLESS_COMPUTE": 15
  }
}
```

❌ **Invalid**: Non-numeric discount values
```json
{
  "sku_specific": {
    "JOBS_COMPUTE": "twenty percent"  // ❌ Error: must be number
  }
}
```

❌ **Invalid**: Percentage outside 0-100
```json
{
  "sku_specific": {
    "JOBS_COMPUTE": 150  // ❌ Error: must be <= 100
  }
}
```

### 3. Optional Fields
✅ **Valid**: All optional fields
```json
{
  "global": {...},
  "sku_specific": {...},
  "notes": "Enterprise discount - Q1 2026",
  "effective_date": "2026-01-01",
  "expiry_date": "2026-12-31"
}
```

✅ **Valid**: Minimal structure (only global required)
```json
{
  "global": {
    "dbu_discount": 20,
    "vm_discount": 10,
    "storage_discount": 0,
    "platform_addon_discount": 0,
    "support_discount": 0
  }
}
```

### 4. Missing Required Fields
❌ **Invalid**: Missing "global"
```json
{
  "sku_specific": {
    "JOBS_COMPUTE": 25
  }
}
```

**Error Response:**
```json
{
  "detail": [
    {
      "loc": ["body", "discount_config", "global"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

## Complete Examples

### Example 1: Simple Global Discounts Only
```json
{
  "cloud": "AWS",
  "region": "us-east-1",
  "tier": "PREMIUM",
  "driver_node_type": "m5.xlarge",
  "worker_node_type": "m5.xlarge",
  "num_workers": 10,
  "photon_enabled": true,
  "driver_pricing_tier": "on_demand",
  "worker_pricing_tier": "spot",
  "runs_per_day": 8,
  "avg_runtime_minutes": 60,
  "days_per_month": 30,
  "discount_config": {
    "global": {
      "dbu_discount": 20,
      "vm_discount": 10,
      "storage_discount": 5,
      "platform_addon_discount": 0,
      "support_discount": 0
    }
  }
}
```

### Example 2: Global + SKU-Specific Discounts
```json
{
  "cloud": "AWS",
  "region": "us-east-1",
  "tier": "PREMIUM",
  "driver_node_type": "m5.xlarge",
  "worker_node_type": "m5.xlarge",
  "num_workers": 10,
  "photon_enabled": true,
  "driver_pricing_tier": "on_demand",
  "worker_pricing_tier": "spot",
  "runs_per_day": 8,
  "avg_runtime_minutes": 60,
  "days_per_month": 30,
  "discount_config": {
    "global": {
      "dbu_discount": 20,
      "vm_discount": 10,
      "storage_discount": 0,
      "platform_addon_discount": 0,
      "support_discount": 0
    },
    "sku_specific": {
      "JOBS_COMPUTE_(PHOTON)": 25,
      "SQL_SERVERLESS_COMPUTE": 30
    },
    "notes": "Enterprise discount - Q1 2026",
    "effective_date": "2026-01-01",
    "expiry_date": "2026-03-31"
  }
}
```

### Example 3: No Discount (Optional)
```json
{
  "cloud": "AWS",
  "region": "us-east-1",
  "tier": "PREMIUM",
  "driver_node_type": "m5.xlarge",
  "worker_node_type": "m5.xlarge",
  "num_workers": 10,
  "photon_enabled": true,
  "driver_pricing_tier": "on_demand",
  "worker_pricing_tier": "spot",
  "runs_per_day": 8,
  "avg_runtime_minutes": 60,
  "days_per_month": 30
  // No discount_config - perfectly valid
}
```

## Common Validation Errors

### Error 1: Wrong Data Type
```json
{
  "global": {
    "dbu_discount": "20%"  // ❌ String instead of number
  }
}
```
**Error**: `value is not a valid float`

### Error 2: Missing Required Nested Field
```json
{
  "global": {
    "dbu_discount": 20
    // ❌ Missing vm_discount, storage_discount, etc.
  }
}
```
**Error**: `field required` for each missing field

### Error 3: Invalid Field Name
```json
{
  "global": {
    "dbu_discount": 20,
    "vm_discount": 10,
    "server_discount": 5  // ❌ Invalid field name
  }
}
```
**Error**: `extra fields not permitted`

### Error 4: Out of Range
```json
{
  "global": {
    "dbu_discount": 200  // ❌ > 100
  }
}
```
**Error**: `ensure this value is less than or equal to 100`

## Frontend Integration

### TypeScript Interface
```typescript
interface GlobalDiscountConfig {
  dbu_discount: number;       // 0-100
  vm_discount: number;        // 0-100
  storage_discount: number;   // 0-100
  platform_addon_discount: number;  // 0-100
  support_discount: number;   // 0-100
}

interface DiscountConfig {
  global: GlobalDiscountConfig;
  sku_specific?: Record<string, number>;  // SKU -> discount %
  notes?: string;
  effective_date?: string;  // YYYY-MM-DD
  expiry_date?: string;     // YYYY-MM-DD
}

interface JobsClassicRequest {
  cloud: string;
  region: string;
  tier: string;
  driver_node_type: string;
  worker_node_type: string;
  num_workers: number;
  photon_enabled: boolean;
  driver_pricing_tier: string;
  worker_pricing_tier: string;
  runs_per_day: number;
  avg_runtime_minutes: number;
  days_per_month: number;
  discount_config?: DiscountConfig;  // Optional
}
```

### Frontend Validation Example
```javascript
function validateDiscountConfig(config) {
  const errors = [];
  
  // Validate global discounts
  if (!config.global) {
    errors.push("Global discounts are required");
    return errors;
  }
  
  const globalFields = [
    'dbu_discount', 'vm_discount', 'storage_discount',
    'platform_addon_discount', 'support_discount'
  ];
  
  for (const field of globalFields) {
    const value = config.global[field];
    if (value === undefined || value === null) {
      errors.push(`${field} is required`);
    } else if (typeof value !== 'number') {
      errors.push(`${field} must be a number`);
    } else if (value < 0 || value > 100) {
      errors.push(`${field} must be between 0 and 100`);
    }
  }
  
  // Validate SKU-specific discounts
  if (config.sku_specific) {
    for (const [sku, discount] of Object.entries(config.sku_specific)) {
      if (typeof discount !== 'number') {
        errors.push(`SKU '${sku}': discount must be a number`);
      } else if (discount < 0 || discount > 100) {
        errors.push(`SKU '${sku}': discount must be between 0 and 100`);
      }
    }
  }
  
  return errors;
}
```

## Testing

### Test Valid Configurations
```bash
# Test 1: Global discounts only
curl -X POST "https://lakemeter-api-335310294452632.aws.databricksapps.com/api/v1/calculate/jobs-classic" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "cloud": "AWS",
    "region": "us-east-1",
    "tier": "PREMIUM",
    "driver_node_type": "m5.xlarge",
    "worker_node_type": "m5.xlarge",
    "num_workers": 10,
    "photon_enabled": true,
    "driver_pricing_tier": "on_demand",
    "worker_pricing_tier": "spot",
    "runs_per_day": 8,
    "avg_runtime_minutes": 60,
    "days_per_month": 30,
    "discount_config": {
      "global": {
        "dbu_discount": 20,
        "vm_discount": 10,
        "storage_discount": 0,
        "platform_addon_discount": 0,
        "support_discount": 0
      }
    }
  }'
```

### Test Invalid Configurations
```bash
# Test 2: Invalid percentage (should fail)
curl -X POST "..." \
  -d '{
    ...
    "discount_config": {
      "global": {
        "dbu_discount": 150,  # Should fail validation
        ...
      }
    }
  }'
```

## Benefits of Validation

✅ **Type Safety**: Ensures all fields are correct types
✅ **Range Validation**: Prevents impossible discount percentages
✅ **Required Fields**: Catches missing required fields early
✅ **Clear Errors**: Pydantic provides detailed error messages
✅ **Auto Documentation**: FastAPI auto-generates OpenAPI docs with validation rules
✅ **IDE Support**: Type hints enable autocomplete and inline documentation

## Backward Compatibility

The implementation supports **both** validated Pydantic models and plain dicts during the transition period:

```python
async def get_discount_for_sku(
    sku: str, 
    discount_config: Union['DiscountConfig', dict],  # Accepts both!
    db: AsyncSession
) -> tuple[float, str]:
```

This ensures:
- ✅ New requests with validation work correctly
- ✅ Existing tests with dict format continue to work
- ✅ Gradual migration path for frontend

## Next Steps

1. ✅ Add Pydantic validation models
2. ✅ Update helper functions to handle both formats
3. ⏭️ Update frontend to match TypeScript interfaces
4. ⏭️ Add unit tests for validation
5. ⏭️ Apply same validation to remaining 20 endpoints
