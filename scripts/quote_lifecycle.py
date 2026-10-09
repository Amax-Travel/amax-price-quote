#!/usr/bin/env python3
"""Quote stage and approved publication through the existing Core gatekeeper."""
import argparse
import json
from pathlib import Path

from quote_api import Client, lock, save
from quote_contract import CapabilityError, check_capability
from quote_payload import micros


def stage(client, quote_id, opportunity_id, value):
    result = client.request('POST', f'/quotes/{quote_id}/opportunity-stage', {'stage': value})
    if result.get('id') != quote_id or result.get('twenty_opportunity_id') != opportunity_id or result.get('stage') != value:
        raise ValueError('Stage response did not verify the linked quote and opportunity')
    return value


def run(client, command, quote_id, record_path, expected_total=None, journal_path=None, authorized=False):
    if type(quote_id) is not int or quote_id <= 0:
        raise ValueError('Quote ID must be a positive integer')
    contract = check_capability(client)
    if contract.get('opportunity_stage_path') != '/quotes/{quote_id}/opportunity-stage':
        raise CapabilityError('Core stage capability is unavailable; no writes were sent')
    quote = client.request('GET', f'/quotes/{quote_id}')
    opportunity_id = quote.get('twenty_opportunity_id')
    if quote.get('id') != quote_id or not opportunity_id:
        raise ValueError('Quote identity or opportunity linkage is missing')
    path = Path(record_path)
    record = json.loads(path.read_text()) if path.exists() else {'quote_id': quote_id, 'opportunity_id': opportunity_id}
    if record.get('quote_id') != quote_id or record.get('opportunity_id') != opportunity_id:
        raise ValueError('Lifecycle record belongs to another quote or opportunity')
    if command == 'building':
        if quote.get('status') != 'draft':
            raise ValueError('Building stage requires a draft; do not reset a later workflow')
        record['building_stage'] = stage(client, quote_id, opportunity_id, 'BUILDING_QUOTE')
        save(path, record)
        return record
    if not authorized or expected_total is None or journal_path is None:
        raise ValueError('Publication requires existing user authorization, reviewed total, and original journal')
    journal = json.loads(Path(journal_path).read_text())
    entries = journal.get('operations', {})
    if entries.get('quote:main', {}).get('id') != quote_id or journal.get('blocked'):
        raise ValueError('Journal does not identify this quote or still has blocked work')
    if any(e.get('state') != 'applied' for e in entries.values()):
        raise ValueError('Reconcile unresolved draft writes before publication')
    total = micros(expected_total)
    totals = client.request('GET', f'/quotes/{quote_id}/totals')
    if totals.get('grand_total_micros') != total:
        raise ValueError('Live total differs from the reviewed amount; reconcile before publication')
    if record.get('reviewed_total_micros', total) != total:
        raise ValueError('Lifecycle record has a different reviewed total')
    record['reviewed_total_micros'] = total
    current_stage = client.request('GET', f'/quotes/{quote_id}/opportunity-stage')
    allowed = {'NEW_LEAD', 'CONTACTED', 'BUILDING_QUOTE', 'PACKAGE_QUOTE_PRESENTED', 'NEGOTIATING', 'QUOTE_FINALIZED'}
    if current_stage.get('id') != quote_id or current_stage.get('twenty_opportunity_id') != opportunity_id or current_stage.get('stage') not in allowed:
        raise ValueError('Linked opportunity is at a later or unknown stage; reconcile before publication')
    if quote.get('status') == 'draft':
        if record.get('publication') in ('pending', 'uncertain', 'confirmed'):
            raise ValueError('Previous publication needs reconciliation; never replay it blindly')
        record['publication'] = 'pending'
        save(path, record)
        try:
            published = client.request('POST', f'/quotes/{quote_id}/finalize')
            if published.get('id') != quote_id or published.get('twenty_opportunity_id') != opportunity_id or published.get('status') != 'finalized':
                raise ValueError('Publication response did not match the quote')
            saved = client.request('GET', f'/quotes/{quote_id}')
            if saved.get('status') != 'finalized' or saved.get('twenty_opportunity_id') != opportunity_id:
                raise ValueError('Publication read-back failed')
            record['publication'] = 'confirmed'
            save(path, record)
        except Exception:
            record['publication'] = 'uncertain'
            save(path, record)
            raise ValueError('Publication outcome uncertain; inspect Core and CRM before any retry') from None
    elif quote.get('status') == 'finalized':
        if record.get('publication') != 'confirmed':
            raise ValueError('Already finalized: verify the previous CRM publication and reconcile the lifecycle record first')
    else:
        raise ValueError('Quote is beyond the supported publication workflow')
    record['presented_stage'] = 'pending'
    save(path, record)
    try:
        record['presented_stage'] = stage(client, quote_id, opportunity_id, 'PACKAGE_QUOTE_PRESENTED')
        save(path, record)
    except Exception:
        raise ValueError('Quote finalized and published; opportunity stage update pending. Retry this command after resolving the stage failure; it will not finalize again.') from None
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['building', 'publish'])
    parser.add_argument('--quote-id', required=True, type=int)
    parser.add_argument('--record', required=True)
    parser.add_argument('--journal')
    parser.add_argument('--expected-total-cad')
    parser.add_argument('--authorized', action='store_true', help='Use only when the conversation already authorizes this publication')
    args = parser.parse_args()
    try:
        with lock(args.record):
            result = run(Client(timeout=120), args.command, args.quote_id, args.record, args.expected_total_cad, args.journal, args.authorized)
        print(json.dumps(result, indent=2))
    except Exception as exc:
        parser.exit(1, str(exc) + '\n')
