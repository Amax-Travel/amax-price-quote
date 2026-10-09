---
name: amax-price-quote
description: Build and review AMAX travel quotes, download customer and internal PDFs, and finalize approved quotes into CRM with opportunity stage updates. Use for AMAX price-quote and quote-costing requests.
---

# AMAX price quote

Turn confirmed sales inputs into a resumable draft quote. Core is authoritative for prices and totals. Use the bundled API adapter; keep each client's job, journal, and downloaded PDFs in private sales working folders outside this skill.

## Start by acting

“AMAX/Amex price code,” “price quote,” and “create the PDF” mean execute this quote workflow in a client conversation. Do not ask whether to author a new SKILL.md unless the user explicitly requests skill development. Reuse all confirmed facts and corrections from the conversation; do not restart an intake questionnaire.

First locate this complete skill folder and run `python3 scripts/doctor.py --api` when shell execution is available. Read [runtime.md](references/runtime.md) for missing files, tool-only runtimes, or connection failures. Do not report “no CRM/computer” before checking available API tools: a browser is not required. Recover missing public skill files before asking the user to fix the installation.

Use authorized lookups for CRM identity, existing opportunities, owner, fare tables, and quote state. A person ID is not an opportunity ID. No matching opportunity is the supported create-or-reuse path through `POST /opportunities`, not a reason to demand an opportunity link. See [quote-inputs.md](references/quote-inputs.md).

This assistant serves multiple salespeople. Determine ownership per conversation and quote from verified sender context or the user's named salesperson. Never carry the previous chat's owner into a different client's job. Resolve a name with `GET /opportunities/owners?q=NAME`; a job may use `opportunity.owner_name` instead of an email. When no owner is known, ask who should own the quote, accepting a name. Preserve existing deal ownership unless explicitly instructed to change it; do not confuse the bot's API identity with the human owner.

Ask only for a fact that changes price, scope, or identity and cannot be resolved from the conversation or authorized sources. Ask one concise bundled question while continuing independent work. Do not ask the user to supply available fare-table prices. A short “yes” confirms a single clear proposition; if your prior question offered conflicting alternatives, narrow only that unresolved point. Later specific corrections override earlier general confirmations.

“Create PDF” authorizes saving the requested draft and downloading its customer PDF. Continue through API writes, server totals, and download, then provide the actual file. It does not authorize finalization or customer messaging. A missing optional name, nationality, or PNR may stay explicitly pending for a draft. Missing required prices must remain unresolved; never call a subtotal the final customer price.

## Workflow

1. Read [quote-inputs.md](references/quote-inputs.md) when collecting or changing inputs. Identify the existing quote and original journal before creating anything. Confirm CRM person reference and salesperson ownership through authorized CRM lookups; never fabricate IDs. Follow [crm-lifecycle.md](references/crm-lifecycle.md) to set and verify the opportunity stage `BUILDING_QUOTE` when building begins, once the draft quote ID is available. Do not reset a later-stage opportunity automatically.
2. Record the user's confirmed amounts, currency, quantity basis, dates, and passenger counts in the job. Preserve unresolved inputs explicitly. A supplied first name may be recorded as supplied; it is not a verified passport name. Missing names do not reduce the confirmed passenger count.
3. Read [api-contract.md](references/api-contract.md) before the first API operation. Run `plan`, then `apply` when the user's request authorizes those draft changes. Do not ask again for values or edits already confirmed in the conversation.
4. Inspect `missing`, `blocked`, and server totals. When updating a quote, reconcile edits made outside the journal before applying. For errors or ambiguous responses, read [recovery.md](references/recovery.md); never start a replacement journal to bypass a failure.
5. Review cost subtotal, profit margin, commission, and grand total separately with the salesperson. Flat commission is the total for the quote. Apply pricing after costs; let Core resolve per-person or round-up intent.
6. Download and review customer and internal PDFs. Check names, group counts, dates (including overnight arrivals), rooms, route/vehicle details, totals, and filenames. Customer copies must not reveal internal component costs. A rounded per-person display can differ from the exact grand total when multiplied back.
7. When the user authorizes **Finalize & Push to CRM**, follow [crm-lifecycle.md](references/crm-lifecycle.md): finalize the reviewed quote, verify customer PDF and prices in CRM, then set and verify the opportunity stage `PACKAGE_QUOTE_PRESENTED`. Stop here; later stages require further user instructions.
8. Report quote status, CRM publish result, stage, totals, downloads, and remaining unknowns separately. Editing or testing the skill itself does not authorize a live finalization. Publishing into CRM does not authorize sending customer messages or marking the quote sent.

## Commands

Resolve `scripts/quote_api.py` relative to this skill's directory, not a sales workspace scripts folder. Python 3.10+ and the local AMAX sales gatekeeper are required; there are no third-party Python dependencies.

```sh
python3 scripts/quote_api.py plan --job /private/job.json
python3 scripts/quote_api.py apply --job /private/job.json --journal /private/journal.json
python3 scripts/quote_api.py status --job /private/job.json --journal /private/journal.json
python3 scripts/quote_api.py pdf --job /private/job.json --journal /private/journal.json --audience internal --output-dir /private/review
python3 scripts/quote_api.py pdf --job /private/job.json --journal /private/journal.json --audience customer --output-dir /private/review
```

Create the private output directory first. For one departure group, add `--group-key GROUP_KEY` to the customer PDF command. Existing PDF files are never overwritten. A customer PDF request may stamp the PDF-generated field; it does not send or finalize.

Use [examples.md](references/examples.md) for a synthetic job. Do not copy its placeholder identity or prices into a real job.

## Boundaries

- Never infer nationality from departure city, name, or residence, or convert an unknown cost into confirmed zero.
- Preserve exact hotel allocations, including fractions of a cent. Train fares use explicit ticket quantities, not an assumed passenger count.
- Existing transfer amendments, row deletion, and CRM identity repair are outside this adapter. Report them for the appropriate authorized workflow.
- Pricing and PDF validation do not prove travel inventory availability or passport-name accuracy.

`quote_api.py` handles draft edits and PDFs. `quote_lifecycle.py` handles stage updates and authorized publication through the same Core connection; no separate CRM connection is required. Follow the lifecycle reference and reuse saved approval. `apply` never finalizes.
