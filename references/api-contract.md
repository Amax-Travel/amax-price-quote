# API and runtime contract

Run on the sales host with the existing gatekeeper at `http://127.0.0.1:8081`. The adapter uses a fixed loopback client, rejects redirects, and reads no credentials. Do not put tokens, customer data, or private journals in the skill. A remote workstation cannot use its own loopback to reach the sales host's gatekeeper.

Before mutations, `GET /quotes/pricing-contract` must advertise version 1, hotel `stay_total_per_room_micros`, transport `sar_fare_micros`, saved-transfer repricing, grouped passengers, customer group PDFs, all three commission modes, and `/quotes/{quote_id}/pricing`. Missing or incompatible capabilities block the apply before writes.

The adapter creates an opportunity and draft quote for a new journal, then origin groups, group-linked flights/passengers, hotels, transfers, and pricing. For existing journals it retains IDs and patches supported changed rows. A known finalized quote is rejected. It verifies successful writes rather than trusting HTTP status alone.

| Operation | Endpoint |
| --- | --- |
| Find salesperson by name | GET /opportunities/owners?q=NAME |
| Workflow stage | POST /quotes/{id}/opportunity-stage |
| Publish approved quote | POST /quotes/{id}/finalize |
| Create verified opportunity | POST /opportunities |
| Draft quote | POST /quotes; GET/PATCH /quotes/{id} |
| Groups, flights, passengers, hotels | POST /quotes/{id}/{kind}; PATCH /quotes/{id}/{kind}/{row_id} |
| Saved fare lookup | GET /transport-fares |
| Transport line | POST /quotes/{id}/transfers |
| Resolve margin and commission | PATCH /quotes/{id}/pricing |
| Authoritative totals | GET /quotes/{id}/totals |
| Customer PDF | GET /quotes/{id}/pdf, optional origin_group_id |
| Internal PDF | GET /quotes/{id}/pdf/internal |

The server rejects legacy hotel write fields such as nightly or combined line totals. Quote exchange-rate PATCH reprices existing draft transfers from their saved original SAR unit fare and quantity. Custom transport supplies exactly one of `sar_fare_micros` or `cad_fare_micros`. Fixed CAD unit fares multiply by quantity without FX and remain fixed on rate updates. Before CAD writes require `transport_cad_cost_input: "cad_fare_micros"` in the pricing contract. Fare-table transport requires a unique positive route/vehicle match.

Pricing sends confirmed `profit_margin_micros`, `commission_mode`, and `commission_input_micros`. Core excludes the prior commission when resolving round-up. The journal tracks pricing intent plus the engine cost/headcount basis, so unchanged apply does not compound or rewrite commission.

PDF filenames come from the server's opportunity title, with a quote fallback and group-ID suffix for grouped downloads. PDF output uses exclusive creation and private permissions. `quote_api.py apply` remains draft-only; `quote_lifecycle.py` handles explicitly authorized publication and stage updates. For authorized finalization and opportunity stages, follow [crm-lifecycle.md](crm-lifecycle.md). No customer messaging is included.

## CRM identity and naming

For the configured trusted sales service, Core resolves the quote's CRM person and omitted client name from the linked opportunity/contact. An unavailable or deleted CRM identity returns HTTP 409; it is not a request to invent a client name. Retain the original opportunity and journal while resolving the lookup.

After creation, GET the saved quote and compare `client_name`, `twenty_person_id`, and `twenty_opportunity_id` to the verified CRM identity. Verify `salesperson_name`/`salesperson_email` against the assigned owner; `created_by` is the bot actor and must not be changed to impersonate the rep. Read back the CRM stage and liveness when available. Missing projections are a configuration/sync issue, not evidence that the opportunity should be recreated.

Dashboard references use `Amax-{ClientSlug}-Q{opportunity_seq}` plus a revision suffix after version 1. PDF filenames separately follow the server's opportunity-title SOP; preserve the returned Content-Disposition filename. Do not rename files locally to disguise missing client or opportunity data.
