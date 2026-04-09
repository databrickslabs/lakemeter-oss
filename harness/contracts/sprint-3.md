# Sprint 3 Contract: User Guide Screenshots (Part 2) + Admin Screenshots

## Acceptance Criteria

- [ ] All 8 user-guide Part 2 screenshots exist in `docs-site/static/img/guides/`:
  - `ai-assistant-guide.png`, `ai-assistant-tools.png`
  - `export-guide.png`, `export-excel-structure.png`
  - `calculation-reference-guide.png`, `calculation-worked-example.png`
  - `faq-guide.png`, `faq-workload-table.png`
- [ ] All 8 admin-guide screenshots exist in `docs-site/static/img/guides/`:
  - `admin-deployment-guide.png`, `admin-configuration-guide.png`
  - `admin-api-reference-guide.png`, `admin-architecture-guide.png`
  - `admin-database-guide.png`, `admin-database-schema.png`
  - `admin-permissions-guide.png`, `admin-troubleshooting-guide.png`
- [ ] Each screenshot is referenced in its corresponding doc page with markdown image syntax
- [ ] Each reference has descriptive alt text (>=10 characters)
- [ ] Each reference has an italic caption line (starts with `*`) immediately below
- [ ] No forbidden customer names ("Maya", "Merchant", "Commerci") in alt text or captions
- [ ] Screenshot files are non-empty and reasonably sized (10KB–2MB)
- [ ] Validation tests written covering all 16 screenshots (file, reference, caption, sanitization)
- [ ] Full test suite passes (`pytest` exit code 0)

## Screenshot-to-Doc-Page Mapping

| Screenshot | Doc Page |
|-----------|----------|
| `ai-assistant-guide.png` | `user-guide/ai-assistant.md` |
| `ai-assistant-tools.png` | `user-guide/ai-assistant.md` |
| `export-guide.png` | `user-guide/exporting.md` |
| `export-excel-structure.png` | `user-guide/exporting.md` |
| `calculation-reference-guide.png` | `user-guide/calculation-reference.md` |
| `calculation-worked-example.png` | `user-guide/calculation-reference.md` |
| `faq-guide.png` | `user-guide/faq.md` |
| `faq-workload-table.png` | `user-guide/faq.md` |
| `admin-deployment-guide.png` | `admin-guide/deployment.md` |
| `admin-configuration-guide.png` | `admin-guide/configuration.md` |
| `admin-api-reference-guide.png` | `admin-guide/api-reference.md` |
| `admin-architecture-guide.png` | `admin-guide/architecture.md` |
| `admin-database-guide.png` | `admin-guide/database.md` |
| `admin-database-schema.png` | `admin-guide/database.md` |
| `admin-permissions-guide.png` | `admin-guide/permissions.md` |
| `admin-troubleshooting-guide.png` | `admin-guide/troubleshooting.md` |

## Test Plan

- File existence and size validation (16 screenshots × 3 checks + 1 count = 49 tests)
- Doc page reference validation (16 screenshots × 3 checks = 48 tests)
- Customer name sanitization (16 tests)
- Total: ~113 tests
- Full test suite: `pytest` exit code 0
- Docs site build: `cd docs-site && npm run build` — zero errors
