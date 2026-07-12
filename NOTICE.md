# Lakemeter

Copyright (2026) Databricks, Inc.

This Software includes software developed at Databricks (https://www.databricks.com/) and its use is subject to the included [LICENSE.md](LICENSE.md) file (Databricks License).

---

Dependencies are grouped below by ecosystem. Each table row lists a third-party package bundled or used at runtime, along with its purpose, license, and upstream source.

See `requirements.txt`, `backend/requirements.txt`, `frontend/package.json`, and `docs-site/package.json` for direct dependency declarations.

## Python Dependencies

| Package | Purpose | License | Source |
| --- | --- | --- | --- |
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
| python-dotenv | Read `.env` files | BSD-3-Clause | [GitHub: theskumar/python-dotenv](https://github.com/theskumar/python-dotenv) |
| cachetools | Extensible memoizing collections | MIT | [GitHub: tkem/cachetools](https://github.com/tkem/cachetools) |
| databricks-sdk | Databricks SDK for Python | Apache-2.0 | [GitHub: databricks/databricks-sdk-py](https://github.com/databricks/databricks-sdk-py) |
| httpx | HTTP client | BSD-3-Clause | [GitHub: encode/httpx](https://github.com/encode/httpx) |
| aiofiles | Async file support | Apache-2.0 | [GitHub: Tinche/aiofiles](https://github.com/Tinche/aiofiles) |

## Frontend Dependencies

| Package | Purpose | License | Source |
| --- | --- | --- | --- |
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
| typescript | TypeScript language | Apache-2.0 | [GitHub: microsoft/TypeScript](https://github.com/microsoft/TypeScript) |
| tailwindcss | Utility-first CSS framework | MIT | [GitHub: tailwindlabs/tailwindcss](https://github.com/tailwindlabs/tailwindcss) |
| vite | Frontend build tool | MIT | [GitHub: vitejs/vite](https://github.com/vitejs/vite) |

## Documentation Site Dependencies

| Package | Purpose | License | Source |
| --- | --- | --- | --- |
| @docusaurus/core | Documentation site framework | MIT | [GitHub: facebook/docusaurus](https://github.com/facebook/docusaurus) |
| @docusaurus/preset-classic | Docusaurus classic preset | MIT | [GitHub: facebook/docusaurus](https://github.com/facebook/docusaurus) |
| @mdx-js/react | MDX React integration | MIT | [GitHub: mdx-js/mdx](https://github.com/mdx-js/mdx) |
| prism-react-renderer | Syntax highlighting renderer | MIT | [GitHub: FormidableLabs/prism-react-renderer](https://github.com/FormidableLabs/prism-react-renderer) |

---

This notice is intended to summarize direct dependencies and key bundled runtime components for Lakemeter. Transitive dependencies are resolved by the relevant package managers.
