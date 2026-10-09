"""Fail-closed contract and write acknowledgements for the deployed quote API."""
from decimal import Decimal


class CapabilityError(Exception):
    """The server must explicitly support these inputs before any mutation."""


def check_capability(client):
    try:
        contract = client.request('GET', '/quotes/pricing-contract')
        expected = {'version': 1, 'hotel_cost_input': 'stay_total_per_room_micros',
                    'transport_cost_input': 'sar_fare_micros',
                    'draft_rate_reprices_saved_transfers': True, 'passenger_origin_groups': True,
                    'customer_group_pdfs': True,
                    'pricing_path': '/quotes/{quote_id}/pricing'}
        if any(contract.get(k) != v for k, v in expected.items()):
            raise ValueError('Unsupported pricing contract')
        if set(contract.get('commission_modes', [])) != {'flat', 'per_person', 'round_up'}:
            raise ValueError('Unsupported commission modes')
        return contract
    except Exception:
        raise CapabilityError('Quote pricing API is unavailable or incompatible. No mutations were sent.') from None


def verify_write(kind, payload, response, expected_fare=None):
    """Do not mark successful HTTP as applied if authoritative inputs were ignored."""
    if kind == 'opportunity' and (response.get('owner_email') or '').lower() != payload['owner_email'].lower():
        raise ValueError('Opportunity owner mismatch')
    if kind == 'hotels':
        returned = response.get('rooms') or []
        fields = ('stay_total_per_room_micros', 'qty', 'room_type')
        if len(returned) != len(payload['rooms']) or any(
            any(returned[i].get(k) != room[k] for k in fields)
            for i, room in enumerate(payload['rooms'])
        ):
            raise ValueError('Hotel room unit price or quantity mismatch')
    if kind == 'transfers':
        if any(response.get(k) != payload[k] for k in ('route_from', 'route_to', 'car_type', 'qty')):
            raise ValueError('Transport input mismatch')
        if 'cad_fare_micros' in payload:
            if response.get('fare_source') != 'custom' or response.get('cad_fare_micros') != payload['cad_fare_micros'] or response.get('cad_amount_micros') != payload['cad_fare_micros'] * payload['qty']:
                raise ValueError('Fixed CAD fare not persisted exactly')
        elif 'sar_fare_micros' in payload:
            if response.get('fare_source') != 'custom' or response.get('sar_fare_micros') != payload['sar_fare_micros']:
                raise ValueError('Custom fare not persisted')
        elif response.get('fare_matched') is not True or response.get('sar_fare_micros') != expected_fare:
            raise ValueError('Fare table changed or no matched fare was saved')
    if kind == 'passengers' and any(response.get(k) != payload[k] for k in ('name', 'category', 'origin_group_id')):
        raise ValueError('Passenger not saved in requested group')
    if kind == 'quote' and 'sar_to_cad_rate' in payload:
        if Decimal(str(response.get('sar_to_cad_rate'))) != Decimal(payload['sar_to_cad_rate']):
            raise ValueError('Exchange rate not persisted')
    if kind == 'pricing':
        if response.get('profit_margin_micros') != payload['profit_margin_micros']:
            raise ValueError('Margin not persisted')
        if type(response.get('commission_micros')) is not int or not isinstance(response.get('totals'), dict):
            raise ValueError('Missing authoritative pricing totals')
