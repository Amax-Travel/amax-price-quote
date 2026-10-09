# Opportunity stages and CRM publication

## Agreed lifecycle

| Milestone | Opportunity `stage` |
| --- | --- |
| Building price quote / Building Quote | `BUILDING_QUOTE` |
| Package quote presented to the client, after Finalize & Push to CRM | `PACKAGE_QUOTE_PRESENTED` |

Update the opportunity's `stage`, not the quote's `status`. The quote remains `draft` during preparation and becomes `finalized` on successful publication. Do not invent separate “price quote created” or “price quote sent” fields. Stop at `PACKAGE_QUOTE_PRESENTED`; subsequent transitions require further user instructions.

This stage is the user's chosen process milestone, not proof of customer message delivery. Do not call `/quotes/{id}/mark-sent`, set `QUOTE_SENT`, accept the quote, invoice it, or message the customer as part of this workflow.

## Stage connection

Use an existing authorized Twenty CRM write tool to update only `stage` on the exact linked opportunity ID. Read back and verify the saved value. Confirm the enum against runtime metadata if the schema differs. Preserve owner, contact, and all other fields.

Core's existing integration uses Twenty `updateOpportunity` with variables `id` and `data: {stage: STAGE_VALUE}` and validates the returned stage. Use the connected tool's supported schema/authentication; never extract server credentials or write database projection rows directly.

The bundled loopback CLI currently has no stage-only command. If the runtime has no authorized CRM stage-write tool, report the missing integration and do not claim success. Do not use `/opportunities/{id}/touch` as a substitute: it records an actual call, email, or WhatsApp contact, which building a quote does not establish. A developer testing the server integration through approved maintenance access does not prove the sales agent has that capability.

Read the stage before beginning. A matching `BUILDING_QUOTE` needs no write. Do not reset later-stage opportunities simply because a job was resumed. For a new opportunity, set the building stage once the created ID is available.

## Finalize & Push to CRM

1. Establish authorization from the conversation to finalize the specific reviewed quote. Do not ask again when already authorized. Draft edits, PDF downloads, and skill packaging alone do not authorize publication.
2. Inspect the original journal for pending/uncertain writes or blocked costs. Read live quote and totals, reconcile out-of-band edits, verify opportunity linkage, and review customer/internal PDFs. Disclose unresolved inputs; names the user allows to remain pending must not be invented. Confirm a CRM stage-write connection is available before beginning the combined operation.
3. Record quote ID, opportunity ID, reviewed grand total, time, and pending publication state in a private lifecycle record beside the journal. Keep customer records outside the skill. Do not alter the draft operation journal to fabricate lifecycle entries.
4. Invoke `POST /quotes/{quote_id}/finalize` with no request body using the authorized Core connection. The `Client` in `scripts/quote_api.py` can make this request on the sales host; `apply` does not call it. Core writes `totalPackageValue`, `pricePerPerson`, and the customer PDF attachment. Do not manually duplicate those writes or attach the internal PDF.
5. Require the same quote/opportunity IDs and `status: finalized` in the response. Read back the quote, CRM amounts, and PDF attachment; compare against reviewed values. Finalization locks this version. Later cost edits require a new version, not an overwrite.
6. Core currently attempts `QUOTE_FINALIZED` automatically after publication. For this expressly requested workflow, then set and verify `PACKAGE_QUOTE_PRESENTED`. This is a deliberate override of Core's intermediate stage; the quote itself stays finalized. If another actor has advanced the opportunity beyond `QUOTE_FINALIZED`, reconcile before overwriting their work.
7. Record publication and stage results separately. Stop after both are verified and report remaining unknowns. Do not infer that the customer received anything.

## Partial success and retries

Core's automatic stage update is best-effort: a successful finalize response does not prove the opportunity stage changed. If publication succeeded but the stage write failed, report “quote finalized and published; opportunity stage update pending.” Retry only the stage after resolving the failure.

Do not re-finalize an already finalized quote to repeat the stage update. Verify the existing amounts and customer attachment, then complete only the missing authorized stage step.

A timeout, 502, or malformed response may leave partial external CRM writes even if Core still says draft. Mark the attempt uncertain and inspect Core and CRM before any retry. Do not blindly re-upload a PDF. A 409 is not evidence that the combined workflow completed.
