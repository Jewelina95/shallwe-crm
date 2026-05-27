# ShallWe Tech Static Audience CRM

This folder is the GitHub Pages version of the CRM.

It is designed to publish the app code without publishing the real customer list.
The real export is written to `web/data/contacts.private.js`, and that file is ignored by git.

## Local preview

From the repository root:

```bash
python3 scripts/export_static_data.py
cd web
python3 -m http.server 8765
```

Open:

```text
http://localhost:8765
```

## GitHub Pages publishing

Publish the `web/` folder through GitHub Pages. The public site will load `sample-data.js` unless you deliberately upload a private data file somewhere. Do not commit `contacts.private.js` to a public repo because it contains emails, phone numbers, LinkedIn URLs, notes, and event records.

## CRM model

The static CRM classifies contacts into:

- Audience type: founder/operator, AI builder, researcher, product/business, investor/ecosystem, student, enterprise leader, community/media.
- Lifecycle: prospect, member, active member, champion, speaker prospect, partner prospect.
- Engagement: cold, warm, hot, champion.
- Email readiness: ready, needs review, no email, missing consent.

Saved segments are built from those fields so the team can export targeted email lists instead of sending generic blasts.
