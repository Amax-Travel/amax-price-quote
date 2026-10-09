---
name: amax-price-quote
description: Build and review AMAX travel quotes, download customer and internal PDFs, and finalize approved quotes into CRM with opportunity stage updates. Use for AMAX price-quote and quote-costing requests.
---

# AMAX price quote

Turn confirmed sales inputs into a resumable draft quote. Core is authoritative for prices and totals. Use the bundled API adapter; keep each client's job, journal, and downloaded PDFs in private sales working folders outside this skill.

## Workflow

1. Read [quote-inputs.md](references/quote-inputs.md) when collecting or changing inputs. Identify the existing quote and original journal before creating anything. Confirm CRM person reference and salesperson ownership through authorized CRM lookups; never fabricate IDs. Follow [crm-lifecycle.md](references/crm-lifecycle.md) to set and verify the opportunity stage `BUILDING_QUOTE` when building begins, once its ID is available. Do not reset a later-stage opportunity automatically.
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

The bundled CLI handles draft edits and PDF downloads. Finalization and stage changes use the authorized Core and CRM connections described in the lifecycle reference; `apply` does not perform them.
