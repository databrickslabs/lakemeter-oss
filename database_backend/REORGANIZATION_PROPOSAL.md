# Lakebase Setup - Proposed Reorganization

## Current Issues
1. ❌ Multiple numbered folders (1_Setup, 2_Tests, 3_Debug, 3_Usage_Examples, 4_Documentation, 4_Functions, 5_Archive, 5_Function_Tests, 6_Debug)
2. ❌ Duplicate numbering (3_Debug and 3_Usage_Examples, 4_Documentation and 4_Functions, 5_Archive and 5_Function_Tests)
3. ❌ Unclear purpose of folders
4. ❌ Mixed active and archived content
5. ❌ `release_2` is unclear - what about release_1?

---

## Proposed Structure

```
Lakebase_Setup/
├── 00_Config/
│   └── Lakebase_Config.py                    # Shared config
│
├── 01_Database_Setup/                        # Initial database setup
│   ├── 01_Create_Role.sql
│   ├── 02_Create_Tables.py
│   ├── 03_Create_Views.py
│   ├── 04_Add_Columns_Cost_Calculation.sql
│   ├── 05_Add_Columns_Discount_Config.py
│   └── 06_Create_SKU_Discount_Mapping.py
│
├── 02_Schema_Migrations/                    # Database schema changes
│   ├── 2024_Q4/
│   │   └── Add_Cost_Calculation_Columns.sql
│   └── 2025_Q1/
│       ├── Add_Discount_Config.py
│       └── Add_New_Workload_Types.py
│
├── 03_Data_Operations/                      # Data backfill & migrations
│   ├── Validate_Line_Items.py
│   ├── Backfill_Line_Item_Costs.py
│   └── README.md
│
├── 04_Tests/                                # Test notebooks
│   ├── Workload_Tests/
│   │   ├── Test_JOBS_Classic.py
│   │   ├── Test_JOBS_Serverless.py
│   │   ├── Test_ALL_PURPOSE_Classic.py
│   │   ├── Test_ALL_PURPOSE_Serverless.py
│   │   ├── Test_DLT_Classic.py
│   │   ├── Test_DLT_Serverless.py
│   │   ├── Test_DBSQL_Classic.py
│   │   ├── Test_DBSQL_Pro.py
│   │   ├── Test_DBSQL_Serverless.py
│   │   ├── Test_Vector_Search.py
│   │   ├── Test_Model_Serving.py
│   │   ├── Test_FMAPI_Databricks.py
│   │   ├── Test_FMAPI_Proprietary.py
│   │   └── Test_LAKEBASE.py
│   └── Function_Tests/
│       └── [23 function test files]
│
├── 05_Utils/                                # Utility functions
│   ├── Utility_Functions.py
│   ├── DBU_Calculators_Classic.py
│   ├── DBU_Calculators_Serverless.py
│   ├── DBU_Calculators_DBSQL.py
│   ├── DBU_Calculators_Vector_Model.py
│   ├── DBU_Calculators_FMAPI.py
│   ├── VM_Cost_Calculators.py
│   └── Main_Orchestrator.py
│
├── 06_Examples/                             # Usage examples
│   ├── JOBS_Classic_Usage.py
│   ├── JOBS_Serverless_Usage.py
│   ├── ALL_PURPOSE_Classic_Usage.py
│   └── [other usage examples]
│
├── 07_Troubleshooting/                      # Debug & diagnostic tools
│   ├── Check_DLT_Product_Types.py
│   ├── Debug_DBSQL_Zero_Costs.py
│   ├── Debug_FMAPI_Pricing.py
│   └── [other debug tools]
│
├── 08_Documentation/                        # Docs only
│   ├── DATABASE_DESIGN.md
│   ├── DEVELOPER_GUIDE.md
│   ├── EXECUTION_GUIDE.md
│   └── OWNERSHIP_TROUBLESHOOTING.md
│
├── 09_Archive/                              # Deprecated/old files
│   └── [archived notebooks]
│
└── README.md                                # Main README
```

---

## Key Improvements

### 1. Clear Purpose by Folder Name
- `Database_Setup` - Initial setup
- `Schema_Migrations` - Schema changes over time
- `Data_Operations` - Backfill & data work
- `Tests` - All test notebooks
- `Utils` - Reusable functions
- `Examples` - Usage examples
- `Troubleshooting` - Debug tools
- `Documentation` - Docs only
- `Archive` - Old stuff

### 2. Chronological Organization
- Sequential numbering (01, 02, 03...)
- Schema migrations organized by quarter/year
- Clear progression from setup → operations → tests

### 3. Logical Grouping
- All tests together under `04_Tests/`
- All utils together under `05_Utils/`
- All debug tools under `07_Troubleshooting/`

### 4. Remove Ambiguity
- No duplicate numbering
- No `release_2` - use date-based migrations instead
- Clear separation of active vs archived

---

## Migration Steps

1. **Create new folder structure in workspace**
2. **Move notebooks to new locations**
3. **Update `%run` paths in notebooks**
4. **Test key workflows**
5. **Archive old structure**

---

## Alternative: Simpler Structure

If the above is too complex, a simpler option:

```
Lakebase_Setup/
├── config/                    # Config files
├── setup/                     # Initial database setup
├── migrations/                # Schema changes (dated)
├── operations/                # Backfill & data operations
├── tests/                     # All tests
├── utils/                     # Utility functions
├── examples/                  # Usage examples
├── docs/                      # Documentation
└── archive/                   # Old files
```

---

**Which approach do you prefer?**
1. Numbered folders (01_, 02_, etc.)
2. Named folders (no numbers)
3. Custom structure?
