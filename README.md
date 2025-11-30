# PromptSizer

AI-powered Databricks cost estimation tool that analyzes workload descriptions and automatically calculates DBU (Databricks Billing Unit) costs.

## Overview

**PromptSizer** helps field engineers and customers quickly estimate Databricks infrastructure costs by:
1. Analyzing natural language workload descriptions using AI
2. Recommending appropriate Databricks SKUs and infrastructure configurations
3. Calculating DBU consumption and monthly costs
4. Exporting configurations to CSV for presentations and planning

## Features

### AI-Powered Workload Analysis
- Automatically classifies workloads into families:
  - **Ingestion** - Connector-based data ingestion (Lakeflow Connect)
  - **SQL Analytics** - SQL queries and BI-ETL (SQL Warehouses)
  - **Interactive Compute** - Notebook exploration and experimentation
- Recommends optimal SKUs, instance types, and configurations

### Interactive Configuration Table
Configure infrastructure parameters:
- **Workload Type** - Select workload family
- **SKU** - Billing SKU type (Jobs Classic, Serverless, SQL Pro, etc.)
- **Driver/Worker Instances** - Choose from 100+ AWS instance types
- **Worker Count** - Number of worker nodes (1-20)
- **Run Duration** - Hours per run
- **Frequency** - Runs per day and days per month

### Automated DBU Cost Calculation
- **DBU/Hour** - Based on worker instance type (2X-Small: 4 DBU, 4X-Large: 528 DBU)
- **DBU/Day** - `DBU/Hour × Run Duration × Runs/Day`
- **DBU/Month** - `DBU/Day × Days/Month`
- **Monthly Cost** - `DBU/Month × SKU Rate` (rates from $0.20-$0.69 per DBU)

### Data Export
- Export full configuration and cost estimates to CSV
- Timestamp-based filenames for easy tracking
- Includes all parameters, DBU calculations, and AI reasoning

### Additional Features
- Dark mode support
- Expandable details showing AI reasoning for each recommendation
- Debug information for troubleshooting
- Multi-LLM provider support (OpenAI, Anthropic, Databricks)

## Tech Stack

- **Frontend**: Next.js 16 + React 19 + TypeScript + Tailwind CSS
- **Backend**: Python service for LLM API calls
- **AI**: OpenAI SDK (supports OpenAI, Anthropic, or Databricks-hosted models)
- **UI Components**: Radix UI + Lucide React icons

## Getting Started

### Prerequisites

1. **Install Node.js**
   ```bash
   brew install node
   ```

2. **Install Python 3** (if not already installed)
   ```bash
   brew install python3
   ```

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd promptsizer
   ```

2. **Install Node.js dependencies**
   ```bash
   npm install
   ```

3. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### Configuration

Create a `.env.local` file at the root folder with your API credentials:

```bash
# Option 1: Using Databricks-hosted OpenAI model (recommended)
NEXT_PUBLIC_OPENAI_API_KEY="<YOUR_DATABRICKS_TOKEN>"
NEXT_PUBLIC_OPENAI_BASE_URL="https://<workspace>.cloud.databricks.com/serving-endpoints"

# Option 2: Using OpenAI directly
NEXT_PUBLIC_OPENAI_API_KEY="<YOUR_OPENAI_API_KEY>"

# Option 3: Using Anthropic
NEXT_PUBLIC_ANTHROPIC_API_KEY="<YOUR_ANTHROPIC_API_KEY>"
```

**Notes:**
- The tool supports multiple LLM providers via environment variables
- For Databricks-hosted models, set both `OPENAI_API_KEY` (your token) and `OPENAI_BASE_URL`
- The default model is `databricks-gpt-5-1` but can be configured in [lib/config.ts](lib/config.ts)

### Running the Application

Start the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Project Structure

```
promptsizer/
├── app/                          # Next.js app directory
│   ├── page.tsx                  # Main UI component
│   ├── layout.tsx                # Root layout and metadata
│   └── api/                      # API routes
│       ├── llm/route.ts          # Primary LLM endpoint (OpenAI)
│       └── anthropic/route.ts    # Alternative Anthropic endpoint
├── lib/                          # Shared utilities
│   ├── config.ts                 # Configuration (API keys, prompts)
│   ├── system-prompt.ts          # AI system prompt for workload analysis
│   └── utils.ts                  # Utility functions
├── api_backend/                  # Python backend services
│   └── openai_service.py         # Python OpenAI API integration
├── components/                   # Reusable UI components
├── public/                       # Static assets
└── requirements.txt              # Python dependencies
```

## How It Works

1. **User Input** - Describe your data processing workload in plain English
2. **AI Analysis** - Next.js API route spawns Python subprocess to call LLM API
3. **LLM Response** - Returns JSON with recommended configuration (SKU, instances, etc.)
4. **Frontend Rendering** - Populates interactive table with recommendations
5. **DBU Calculation** - Automatically calculates costs using lookup tables and formulas
6. **Export** - Save configuration to CSV for customer presentations

## Usage Example

**Input:**
```
We need to ingest data from Salesforce and S3 daily,
run some ETL jobs to process 100GB of data, and provide
a SQL interface for 50 business analysts to query the data.
```

**Output:**
The tool will generate a configuration table with:
- Lakeflow Connect for Salesforce/S3 ingestion
- Jobs Compute for ETL processing
- SQL Warehouse Pro for analyst queries
- Recommended instance types and worker counts
- Full DBU cost breakdown per workload

## Development

This project is built with Next.js. Key files:
- [app/page.tsx](app/page.tsx) - Main application logic and UI
- [lib/config.ts](lib/config.ts) - LLM provider configuration
- [lib/system-prompt.ts](lib/system-prompt.ts) - AI instructions for workload analysis
- [api_backend/openai_service.py](api_backend/openai_service.py) - Python LLM service

## Contributing

This is a Databricks field engineering tool. For questions or contributions, contact the project maintainers.

## License

Internal Databricks tool for field engineering use.
