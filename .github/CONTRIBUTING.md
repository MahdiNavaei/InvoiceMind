# Contributing to InvoiceMind

Thank you for considering contributing. Please follow these steps:

1. Fork the repo and create a topic branch.
2. Run backend tests: `python -m pytest -q tests/unit tests/integration`.
3. Run frontend checks:
   - `cd frontend && npm run typecheck`
   - `cd frontend && npm run test`
4. Open a PR with a clear description and link to any relevant issue.

Coding style: follow existing project style. For Python, target 3.10+ and for frontend use strict TypeScript.
