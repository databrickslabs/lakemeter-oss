# Lakemeter

A Databricks cost estimation tool that runs as a **Databricks App** with built-in SSO authentication.

Create, manage, and export detailed pricing estimates for 16 Databricks workload types across AWS, Azure, and GCP.

![Lakemeter home page](/docs-site/static/img/home-page.png)

## Features

- **16 workload types** — Jobs, All-Purpose, DBSQL, DLT, Model Serving, FMAPI, Vector Search, Lakebase, Databricks Apps, AI Parse, Shutterstock ImageAI
- **AI assistant** — Describe your workload in natural language, review the suggestion, and accept with one click
- **Excel export** — Full cost breakdowns with SKU details, discount calculations, and VM pricing
- **Multi-cloud** — AWS, Azure, and GCP with region-specific pricing
- **One-command install** — Provisions Lakebase, loads pricing data, and deploys the app automatically

## Quick Start

```bash
git clone https://github.com/steven-tan_data/lakemeter-opensource.git
cd lakemeter-opensource

./scripts/install.sh --profile <your-cli-profile>
```

The installer provisions everything in ~15 minutes. You only need a [Databricks CLI](https://docs.databricks.com/aws/en/dev-tools/cli/profiles.html) configured with a workspace profile.

## Documentation

Full documentation is available at **[cheeyutan.github.io/lakemeter-opensource](https://cheeyutan.github.io/lakemeter-opensource/)**.

- [User Guide](https://cheeyutan.github.io/lakemeter-opensource/user-guide/overview) — How to create estimates, configure workloads, use the AI assistant, and export
- [Admin Guide](https://cheeyutan.github.io/lakemeter-opensource/admin-guide/deployment) — Installation, deployment inventory, and API reference
- [Changelog](https://cheeyutan.github.io/lakemeter-opensource/changelog) — Release history

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React, TypeScript, Tailwind CSS, Vite |
| Backend | FastAPI, SQLAlchemy, Pydantic |
| Database | Lakebase (managed PostgreSQL on Databricks) |
| AI | Claude via Databricks Foundation Model APIs |
| Hosting | Databricks Apps (SSO, managed compute) |

## Licensing

Copyright (2026) Databricks, Inc. This Software includes software developed at Databricks (https://www.databricks.com/) and its use is subject to the included LICENSE file.

### Backend Dependencies (Python)

| Library | Purpose | License | Source |
|---------|---------|---------|--------|
| fastapi | Web framework for building APIs | MIT | [GitHub: fastapi/fastapi](https://github.com/fastapi/fastapi) |
| uvicorn | ASGI server for FastAPI | BSD-3-Clause | [GitHub: encode/uvicorn](https://github.com/encode/uvicorn) |
| sqlalchemy | SQL toolkit and ORM | MIT | [GitHub: sqlalchemy/sqlalchemy](https://github.com/sqlalchemy/sqlalchemy) |
| psycopg2-binary | PostgreSQL database adapter | LGPL | [GitHub: psycopg/psycopg2](https://github.com/psycopg/psycopg2) |
| pydantic | Data validation using Python type hints | MIT | [GitHub: pydantic/pydantic](https://github.com/pydantic/pydantic) |
| pydantic-settings | Settings management for Pydantic | MIT | [GitHub: pydantic/pydantic-settings](https://github.com/pydantic/pydantic-settings) |
| python-multipart | Streaming multipart parser | Apache-2.0 | [GitHub: Kludex/python-multipart](https://github.com/Kludex/python-multipart) |
| xlsxwriter | Excel XLSX file creation | BSD-2-Clause | [GitHub: jmcnamara/XlsxWriter](https://github.com/jmcnamara/XlsxWriter) |
| python-jose | JOSE implementation (JWT) | MIT | [GitHub: mpdavis/python-jose](https://github.com/mpdavis/python-jose) |
| passlib | Password hashing framework | BSD-3-Clause | [GitHub: glic3rern/passlib](https://github.com/glic3rern/passlib) |
| python-dotenv | Read .env files | BSD-3-Clause | [GitHub: theskumar/python-dotenv](https://github.com/theskumar/python-dotenv) |
| cachetools | Extensible memoizing collections | MIT | [GitHub: tkem/cachetools](https://github.com/tkem/cachetools) |
| databricks-sdk | Databricks SDK for Python | Databricks | [GitHub: databricks/databricks-sdk-py](https://github.com/databricks/databricks-sdk-py) |

### Frontend Dependencies (Node.js)

| Library | Purpose | License | Source |
|---------|---------|---------|--------|
| react | UI component library | MIT | [GitHub: facebook/react](https://github.com/facebook/react) |
| react-dom | React DOM rendering | MIT | [GitHub: facebook/react](https://github.com/facebook/react) |
| react-router-dom | Client-side routing | MIT | [GitHub: remix-run/react-router](https://github.com/remix-run/react-router) |
| axios | HTTP client | MIT | [GitHub: axios/axios](https://github.com/axios/axios) |
| zustand | State management | MIT | [GitHub: pmndrs/zustand](https://github.com/pmndrs/zustand) |
| framer-motion | Animation library | MIT | [GitHub: framer/motion](https://github.com/framer/motion) |
| clsx | Utility for constructing className strings | MIT | [GitHub: lukeed/clsx](https://github.com/lukeed/clsx) |
| file-saver | Client-side file saving | MIT | [GitHub: eligrey/FileSaver.js](https://github.com/eligrey/FileSaver.js) |
| react-hot-toast | Toast notifications | MIT | [GitHub: timolins/react-hot-toast](https://github.com/timolins/react-hot-toast) |
| react-markdown | Markdown renderer for React | MIT | [GitHub: remarkjs/react-markdown](https://github.com/remarkjs/react-markdown) |
| remark-gfm | GitHub Flavored Markdown support | MIT | [GitHub: remarkjs/remark-gfm](https://github.com/remarkjs/remark-gfm) |
| @headlessui/react | Unstyled accessible UI components | MIT | [GitHub: tailwindlabs/headlessui](https://github.com/tailwindlabs/headlessui) |
| @heroicons/react | SVG icon set | MIT | [GitHub: tailwindlabs/heroicons](https://github.com/tailwindlabs/heroicons) |
| @dnd-kit/core | Drag and drop toolkit | MIT | [GitHub: clauderic/dnd-kit](https://github.com/clauderic/dnd-kit) |
| @dnd-kit/sortable | Sortable preset for dnd-kit | MIT | [GitHub: clauderic/dnd-kit](https://github.com/clauderic/dnd-kit) |
| @dnd-kit/modifiers | Modifiers for dnd-kit | MIT | [GitHub: clauderic/dnd-kit](https://github.com/clauderic/dnd-kit) |
| @dnd-kit/utilities | Utilities for dnd-kit | MIT | [GitHub: clauderic/dnd-kit](https://github.com/clauderic/dnd-kit) |
| typescript | TypeScript language (dev) | Apache-2.0 | [GitHub: microsoft/TypeScript](https://github.com/microsoft/TypeScript) |
| tailwindcss | Utility-first CSS framework (dev) | MIT | [GitHub: tailwindlabs/tailwindcss](https://github.com/tailwindlabs/tailwindcss) |
| vite | Frontend build tool (dev) | MIT | [GitHub: vitejs/vite](https://github.com/vitejs/vite) |
