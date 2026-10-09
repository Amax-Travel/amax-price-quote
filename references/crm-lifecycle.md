# Opportunity stages and CRM publication

Use the existing local Core gatekeeper for the entire workflow. A separate Twenty connector or CRM credential is not required. `GET /quotes/pricing-contract` advertises `opportunity_stage_path: "/quotes/{quote_id}/opportunity-stage"`. If absent, the deployed Core is outdated; this is a deployment issue, not a reason to request another approval or salesperson email.

| Milestone | Opportunity stage |
| --- | --- |
| Building the draft price quote | `BUILDING_QUOTE` |
| Finalize & Push to CRM completed | `PACKAGE_QUOTE_PRESENTED` |

The quote remains `draft` during preparation and becomes `finalized` after publication. Stage is a field of the linked opportunity. Stop at presented; do not mark the quote sent, invoice, accept, or message the customer. Presented is the chosen workflow milestone, not evidence of customer delivery.

## Building

After the quote exists, use the bundled command:

```sh
python3 scripts/quote_lifecycle.py building --quote-id QUOTE_ID --record /private/lifecycle.json
```

The command writes `POST /quotes/{id}/opportunity-stage` with `{"stage":"BUILDING_QUOTE"}`. Core selects the quote's linked opportunity, checks permission and ownership, writes CRM, and verifies the saved stage. Matching stages are idempotent. A later stage returns 409; inspect it with `GET /quotes/{id}/opportunity-stage` and preserve it when simply resuming work. Do not use `/opportunities/{id}/touch`: that represents customer contact.

## Finalize & Push to CRM

Use authorization already given in the conversation for this specific reviewed quote. Do not ask again because a connection was repaired or a stage update needs retrying. A request for a draft PDF alone does not authorize publication.

Before publication, reconcile the original journal, any out-of-band edits, unresolved prices, and the live total. Review customer and internal PDFs. Names the user allows to remain pending must not be invented. Record the reviewed amount and reuse the same private lifecycle record:

```sh
python3 scripts/quote_lifecycle.py publish --quote-id QUOTE_ID --record /private/lifecycle.json --journal /private/journal.json --expected-total-cad REVIEWED_AMOUNT --authorized
```

`--authorized` records the agent's use of existing conversation authorization; it is not an instruction to ask the user again. Keep all private files outside this skill. The command:

1. Checks deployed stage capability, quote/opportunity linkage, journal state, current CRM stage, and exact live total.
2. Saves a pending publication record before calling `POST /quotes/{id}/finalize`. Core publishes total package value, per-person price, and the customer PDF attachment. Never attach the internal PDF or duplicate those writes manually.
3. Requires a successful finalize response and finalized quote read-back. Core's response confirms its CRM writes succeeded; do not describe that as an independent CRM attachment inspection. Use a CRM read tool if available for additional inspection, without treating its absence as a separate write-connection blocker.
4. Sets and verifies `PACKAGE_QUOTE_PRESENTED` using the Core stage endpoint. This replaces Core's intermediate `QUOTE_FINALIZED` milestone for this workflow. Later/unknown stages are protected against automatic reset.
5. Records publication and stage outcomes separately. Reports no customer message sent.

## Partial success and retries

A failed stage update after publication means **quote finalized and published; opportunity stage update pending**. Re-running the same command with the same lifecycle record retries only the stage for an already finalized quote. It never re-finalizes it.

A timeout, 502, malformed response, or interrupted pending publication may have left partial CRM writes even if Core says draft. The script marks it uncertain and blocks replay. Inspect Core and CRM amounts/attachment before reconciling the lifecycle record; never fabricate confirmed state just to unblock a retry. If another tool already finalized the quote, verify that publication and bind the record to the same quote/opportunity before completing only the stage step. An HTTP409 alone is not evidence of completion.
