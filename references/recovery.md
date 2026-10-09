# Resume, reconciliation, and known limits

Preserve the original job path, job ID, journal path, operation keys, IDs, and request history. The version-1 journal uses a lock and atomic private writes. It is operational state, not a disposable log.

- `applied`: compare proposed inputs and live state before changing a previously edited quote. Unchanged payloads are skipped.
- `rejected`: a known client error may be corrected and retried; retain its record ID for PATCH.
- `pending` or `uncertain`: stop automatic mutation. Read the private journal and inspect the server through authorized reads. Establish whether the operation committed before repairing journal state. Never delete an entry, invent success, or repeat a POST just to get past the block.
- Capability failure: deploy or restore a compatible Core service through its normal maintenance workflow; do not bypass the contract check.
- Out-of-band edits: compare live values with job and journal, preserve user changes, and reconcile only the intended fields. The journal is not a bidirectional synchronization engine.
- Changed existing transfer or removal: unsupported. Keep the row and report the limitation; do not silently delete and recreate it. Rate changes are supported through quote PATCH.

For a legacy hotel job, preserve a private backup, convert the confirmed combined room cost to exact per-room stay input, and retain existing hotel keys/IDs. The next apply patches the existing rows. Historical hotel values are not automatically migrated.

## Known review issues

If a saved draft has a blank client name, a generic `Amax-Client-…` reference, missing person link, or an unexpected owner/opportunity, pause PDF delivery and publication. Keep the draft ID and journal; compare the saved quote against the verified CRM opportunity/contact. Do not recreate the deal or quote, overwrite the audit creator, or infer a replacement owner. Core must be deployed with its exact trusted sales-service identity configured for linked CRM projections. Ask an authorized operator to repair confirmed legacy draft identity; this adapter does not repair it. Finalized historical quotes require a separate reviewed correction. A successful pricing request does not prove the CRM identity is correct.

The internal PDF may show a quote-level passenger-count warning when origin-group counts already match. Verify totals against the groups; do not double-count or remove valid travellers to suppress the warning.

Missing names, nationalities, and PNR can remain explicitly pending for a draft at the salesperson's direction. A successful draft/PDF walkthrough is not approval to send a customer quote or finalize bookings.
