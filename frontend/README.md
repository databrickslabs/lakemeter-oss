# Lakemeter Frontend

React + TypeScript + Tailwind CSS frontend for the Databricks Pricing Calculator.

## Features

- 🎨 Modern, dark-themed UI inspired by Databricks
- 📊 Create and manage pricing estimates
- 💾 Save estimates to database
- 📥 Export estimates to Excel
- ⚡ Fast and responsive with Framer Motion animations
- 🔧 Configure multiple workload types:
  - Jobs Compute
  - Delta Live Tables (DLT)
  - SQL Warehouses (DBSQL)
  - Interactive Clusters
  - Serverless Compute
  - Model Serving (Foundation Models)

## Setup

1. Install dependencies:
```bash
npm install
```

2. Start development server:
```bash
npm run dev
```

3. Build for production:
```bash
npm run build
```

## Project Structure

```
src/
├── api/          # API client functions
├── components/   # Reusable UI components
│   ├── Layout.tsx
│   └── LineItemForm.tsx
├── pages/        # Page components
│   ├── Dashboard.tsx
│   ├── Calculator.tsx
│   └── EstimateDetail.tsx
├── store/        # Zustand state management
├── types/        # TypeScript type definitions
├── App.tsx       # Main app with routing
├── main.tsx      # Entry point
└── index.css     # Tailwind styles
```

## Configuration

The frontend proxies API requests to `http://localhost:8000` by default. Update `vite.config.ts` to change the backend URL.

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **Framer Motion** - Animations
- **Zustand** - State management
- **React Router** - Routing
- **Axios** - HTTP client
- **React Hot Toast** - Notifications


