# ShallWe Tech Static Audience CRM

This is the GitHub Pages version of the CRM. It is designed for audience analysis, segmentation, and email-list export.

## What It Classifies

The CRM infers operational audience fields from the existing attendance list:

- `Persona`: Founder / Operator, Research / Technical, Product / Business, Student / Early Career, General Community
- `Seniority`: Decision maker, Mid-senior, Early, Unknown
- `Lifecycle`: Lead, Registered, Attendee, Partner, Speaker prospect
- `Interest`: agents, vibe coding, world models, research, product, venture, community, career
- `Engagement`: Hot, Warm, Light, Cold
- `Email readiness`: Email-ready or Needs enrichment

These mirror common CRM patterns: lifecycle/status, tags/interests, engagement score, consent/readiness, and saved segments.

## Local Private Data

Generate private local data from `crm.db`:

```bash
python3 scripts/export_static_data.py
```

This creates:

```text
web/data/contacts.private.js
```

That file contains customer PII and is ignored by git. Do not commit it to a public repository.

## Run Locally

```bash
cd web
python3 -m http.server 4174
```

Open:

```text
http://localhost:4174
```

## GitHub Pages Publishing

The workflow in `.github/workflows/pages.yml` publishes the `web/` folder to GitHub Pages on every push to `main`.

The public GitHub Pages site will use `web/data/sample-data.js` unless a private data file exists locally. This keeps the CRM publishable without exposing the real customer list.
