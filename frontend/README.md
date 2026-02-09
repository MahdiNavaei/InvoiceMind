# InvoiceMind Frontend

Next.js App Router UI for `InvoiceMind` with bilingual UX (English / فارسی), run operations, quarantine workflows, and governance visibility.

## Development

```bash
npm install
npm run dev
```

## Quality

```bash
npm run typecheck
npm run test
npm run build
```

## Environment

Copy sample env:

```bash
cp .env.local.example .env.local
```

PowerShell alternative:

```powershell
Copy-Item .env.local.example .env.local
```

Required variable:
- `INVOICEMIND_API_BASE_URL`

Optional:
- `INVOICEMIND_API_TOKEN`
- `INVOICEMIND_API_USERNAME`
- `INVOICEMIND_API_PASSWORD`

## Main routes

- `/[lang]/dashboard`
- `/[lang]/upload`
- `/[lang]/runs`
- `/[lang]/runs/[runId]`
- `/[lang]/runs/[runId]/compare/[otherRunId]`
- `/[lang]/quarantine`
- `/[lang]/governance`
- `/[lang]/settings`

For full project overview, see root `README.md`.
