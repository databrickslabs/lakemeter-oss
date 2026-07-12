# Contributing to Lakemeter

Lakemeter cannot accept direct code contributions from external contributors at this time.

Users are welcome to create GitHub Issues to report bugs, request improvements, or propose new functionality. The Lakemeter maintainers will review and prioritize issues based on user feedback.

## Reporting Issues

When opening an issue, please include:

- A clear description of the problem or request.
- Steps to reproduce, if reporting a bug.
- Screenshots or logs, if helpful.
- The Databricks workload type involved, if applicable.
- Expected behavior and actual behavior.

Please do not include secrets, credentials, private keys, customer data, customer-identifying information, internal Databricks URLs, Databricks-internal benchmark data, internal sizing methodology, or non-public pricing/product information.

## Pull Requests

Unsolicited pull requests may not be accepted. If you would like to propose a code change, please open an issue first so the maintainers can discuss the request.

## Automated Checks

Lakemeter uses GitHub Actions to run publication checks on pull requests and pushes to `main`.

The automated checks include:

- Python syntax compilation for backend and test files.
- A stable subset of Python tests for suite completeness and documentation build validation.
- Frontend production build.
- Docusaurus documentation build.

Some tests in the repository require live Databricks services, AI assistant access, media assets, or environment-specific pricing data. Those tests are not part of the default public CI gate.

## Running Checks Locally

Set up Python dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pytest openpyxl pillow pyyaml
```

Run Python checks:

```bash
python -m compileall -q backend/app tests
python -m pytest \
  tests/test_integration_validation/test_suite_completeness.py \
  tests/docs_media/test_docs_build.py
```

Build the frontend:

```bash
cd frontend
npm ci
npm run build
```

Build the documentation:

```bash
cd docs-site
npm ci
npm run build
```

## License

By submitting any issue, suggestion, or proposed change, you agree that any resulting contribution may be incorporated into Lakemeter under the project's Databricks License.
