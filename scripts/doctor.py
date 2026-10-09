#!/usr/bin/env python3
"""Read-only skill completeness and optional sales API capability check."""
import argparse
import json
from pathlib import Path

REQUIRED = (
    'SKILL.md', 'references/api-contract.md', 'references/crm-lifecycle.md',
    'references/examples.md', 'references/quote-inputs.md', 'references/recovery.md',
    'references/runtime.md', 'scripts/quote_api.py', 'scripts/quote_payload.py',
    'scripts/quote_contract.py', 'scripts/quote_pdf.py', 'scripts/quote_lifecycle.py',
)


def check(root, api=False):
    missing = [name for name in REQUIRED if not (root / name).is_file()]
    result = {'files_complete': not missing, 'missing_files': missing}
    if missing or not api:
        return result
    try:
        from quote_api import Client
        from quote_contract import check_capability
        client = Client()
        contract = check_capability(client)
        result['fixed_cad_transport'] = contract.get('transport_cad_cost_input') == 'cad_fare_micros'
        result['opportunity_stages'] = contract.get('opportunity_stage_path') == '/quotes/{quote_id}/opportunity-stage'
        result['salesperson_lookup'] = contract.get('owner_lookup_path') == '/opportunities/owners'
        result['pricing_contract'] = 'compatible'
        fares = client.request('GET', '/transport-fares')
        if not isinstance(fares, list):
            raise ValueError('Unexpected fare response')
        result['fare_lookup'] = 'available'
        result['fare_count'] = len(fares)
    except Exception as exc:
        result['api_check'] = 'failed'
        result['error_type'] = type(exc).__name__
        if hasattr(exc, 'status'):
            result['http_status'] = exc.status
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--api', action='store_true', help='Read pricing contract and fare table; no writes')
    args = parser.parse_args()
    result = check(Path(__file__).resolve().parents[1], args.api)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['files_complete'] and result.get('api_check') != 'failed' else 1)
