"""Serialize confirmed inputs; Core owns totals, FX and commission arithmetic."""
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext
import re


def micros(value):
    if not isinstance(value, (str, int)) or isinstance(value, bool):
        raise ValueError('Money must be a decimal string or integer')
    try:
        amount = Decimal(value)
        if not amount.is_finite() or amount < 0 or amount > Decimal('9223372036854'):
            raise ValueError('Money outside supported nonnegative range')
        with localcontext() as ctx:
            ctx.prec = 40
            encoded = amount * Decimal(1000000)
        if encoded != encoded.to_integral_value():
            raise ValueError('Money has more than six decimal places')
        return int(encoded)
    except InvalidOperation as exc:
        raise ValueError('Invalid decimal money') from exc


def select(row, fields):
    return {k: row[k] for k in fields.split() if k in row}


def hotel_room(row, stay_micros):
    return dict(room_type=row['room_type'], qty=row['qty'], stay_total_per_room_micros=stay_micros)


def rate(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d+(?:\.\d{1,6})?', value):
        raise ValueError('Exchange rate must be a decimal string with at most six decimals')
    if not Decimal(0) < Decimal(value) < Decimal(10000):
        raise ValueError('Exchange rate outside supported range')
    return value


def plan(job):
    """Return deterministic operations and unresolved inputs, never arbitrary HTTP."""
    if not re.fullmatch(r'[A-Za-z0-9_-]+', job['job_id']):
        raise ValueError('job_id must be a stable simple identifier')
    missing, ops = list(job.get('unresolved', [])), []

    def add(key, kind, payload, group=None):
        if not re.fullmatch(r'[A-Za-z0-9_-]+', key):
            raise ValueError('Entry keys must be stable simple identifiers')
        ident = kind + ':' + key
        if any(o['key'] == ident for o in ops):
            raise ValueError('Duplicate entry key')
        ops.append(dict(key=ident, kind=kind, payload=payload, group=group))

    def money(row, field, basis, label, currency='CAD'):
        cost = row.get(field) or {}
        if cost.get('confirmed') is not True or cost.get('currency') != currency or cost.get('basis') != basis:
            missing.append(label + ': confirm ' + currency + ' amount and ' + basis + ' basis')
            return None
        return micros(cost['amount'])

    opp = select(job['opportunity'], 'person_ref package_type travel_month pax_adult pax_child pax_infant owner_email')
    if not opp.get('person_ref') or not opp.get('owner_email'):
        raise ValueError('Verified person_ref and owner_email are required')
    for name in ('pax_adult', 'pax_child', 'pax_infant'):
        if type(opp.get(name)) is not int or opp[name] < 0:
            raise ValueError('All passenger counts must be confirmed nonnegative integers')
    add('main', 'opportunity', opp)
    quote = select(job.get('quote', {}), 'client_name star_rating prepared_by destination travel_date flight_route_info flight_notes')
    quote.update(select(opp, 'pax_adult pax_child pax_infant'))
    quote['currency_code'] = 'CAD'
    fx = job.get('quote', {}).get('sar_to_cad_rate')
    if fx is not None:
        if fx.get('confirmed') is True:
            quote['sar_to_cad_rate'] = rate(fx['value'])
        else:
            missing.append('Confirm SAR to CAD exchange rate; existing/default rate retained')
    add('main', 'quote', quote)
    group_keys = set()
    for row in job.get('origin_groups', []):
        group_keys.add(row['key'])
        payload = select(row, 'origin_iata label pax_adult pax_child pax_infant flight_route_info flight_notes sort_order')
        for category in ('adult', 'child', 'infant'):
            if payload.get('pax_' + category, 0):
                for field, target in [('flight_', 'flight_cost_'), ('visa_', 'visa_'),
                                      ('extra_flight_', 'extra_flight_'), ('seat_', 'seat_'), ('bag_', 'bag_')]:
                    if field not in ('flight_', 'visa_') and field + category not in row:
                        continue
                    value = money(row, field + category, 'per_' + category, row['key'] + ' ' + field + category)
                    if value is not None:
                        payload[target + category + '_micros'] = value
        if 'visa_nationalities' in row:
            if row.get('visa_nationalities_confirmed') is True:
                payload['visa_nationalities'] = row['visa_nationalities']
            else:
                missing.append(row['key'] + ': passport nationalities unconfirmed')
        add(row['key'], 'origin-groups', payload)
    if not group_keys:
        raise ValueError('At least one origin group is required')
    for category in ('adult', 'child', 'infant'):
        counts = [r.get('pax_' + category, 0) for r in job['origin_groups']]
        if any(type(v) is not int or v < 0 for v in counts) or sum(counts) != opp['pax_' + category]:
            raise ValueError('Origin-group passenger counts must match opportunity')
    for kind, fields in [('flights', 'leg_date airline flight_no depart_time from_airport arrive_time at_airport journey duration sort_order'),
                         ('passengers', 'name category sort_order')]:
        for row in job.get(kind, []):
            if row['group_key'] not in group_keys:
                raise ValueError(kind + ' references unknown origin group')
            if kind == 'passengers':
                if row.get('confirmed') is not True:
                    missing.append(row['key'] + ': confirm passenger name and category')
                    continue
                if not isinstance(row.get('name'), str) or not row['name'].strip() or row.get('category') not in ('Adult', 'Child', 'Infant'):
                    raise ValueError('Passenger requires a name and Adult, Child or Infant category')
            add(row['key'], kind, select(row, fields), row['group_key'])
    for row in job.get('hotels', []):
        amount = money(row, 'cost', 'per_room_stay', row['key'] + ' hotel')
        if row.get('stay_confirmed') is not True or type(row.get('qty')) is not int or row['qty'] < 1:
            missing.append(row['key'] + ': confirm stay dates and room quantity')
            continue
        if amount is None:
            continue
        if not row.get('check_in') or not row.get('check_out'):
            missing.append(row['key'] + ': confirm check-in and check-out dates')
            continue
        if date.fromisoformat(row['check_out']) <= date.fromisoformat(row['check_in']):
            raise ValueError('Hotel check-out must follow check-in')
        payload = select(row, 'city hotel_name distance star_rating breakfast food_plan check_in check_out')
        payload['rooms'] = [hotel_room(row, amount)]
        add(row['key'], 'hotels', payload)
    for row in job.get('transfers', []):
        if type(row.get('qty')) is not int or not 1 <= row['qty'] <= 10000:
            missing.append(row['key'] + ': confirm ticket or vehicle quantity')
            continue
        if not all(row.get(k) for k in ('route_from', 'route_to', 'car_type')):
            missing.append(row['key'] + ': confirm route and transport type')
            continue
        source = row.get('pricing_source', 'fare_table')
        payload = select(row, 'route_from route_to car_type qty sort_order')
        if source == 'custom':
            basis = 'per_passenger' if row['car_type'].lower() == 'train' else 'per_vehicle'
            amount = money(row, 'fare', basis, row['key'] + ' fare', 'SAR')
            if amount is None:
                continue
            if amount > 1_000_000_000_000:
                raise ValueError('Transport unit fare exceeds supported range')
            payload['sar_fare_micros'] = amount
        elif source != 'fare_table' or 'fare' in row:
            raise ValueError('Explicit custom pricing_source required for supplied fares')
        add(row['key'], 'transfers', payload)
    pricing = job.get('pricing', {})
    margin = money(pricing, 'margin', 'per_quote', 'Profit margin')
    commission = pricing.get('commission') or {}
    mode = commission.get('mode', 'flat')
    bases = {'flat': 'per_quote', 'per_person': 'per_person', 'round_up': 'target_per_person'}
    if mode not in bases:
        raise ValueError('Unknown commission mode')
    amount = money(pricing, 'commission', bases[mode], 'Commission')
    if margin is not None and amount is not None:
        add('main', 'pricing', dict(profit_margin_micros=margin, commission_mode=mode, commission_input_micros=amount))
    return ops, missing
