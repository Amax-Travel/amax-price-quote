#!/usr/bin/env python3
"""Incremental draft-only quote API client; Python standard library only."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import tempfile
import urllib.error
import urllib.request
from quote_payload import plan, micros
from quote_contract import CapabilityError, check_capability, verify_write
from quote_pdf import download_pdf

BASE = 'http://127.0.0.1:8081'


class ApiError(Exception):
    def __init__(self, status, allow=None):
        self.status, self.allow = status, allow
        super().__init__('API request rejected: HTTP ' + str(status))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Client:
    def __init__(self, base=BASE):
        if base != BASE:
            raise ValueError('Only the existing local gatekeeper http://127.0.0.1:8081 is allowed')
        self.base = base
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def request(self, method, path, payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        req = urllib.request.Request(self.base + path, data=data, method=method,
                                     headers={'Content-Type': 'application/json'})
        try:
            with self.opener.open(req, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            # Never print arbitrary response bodies containing customer data.
            raise ApiError(exc.code, exc.headers.get('Allow')) from None


def save(path, data):
    path = Path(path)
    fd, tmp = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(data, stream, indent=2, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


@contextmanager
def lock(path):
    import fcntl
    # Keep inode in place after unlock; unlinking allows concurrent lock races.
    fd = os.open(str(path) + '.lock', os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Journal already in use') from None
        yield
    finally:
        os.close(fd)


def load_journal(path, job, job_path, target):
    binding = {'job_id': job['job_id'], 'job_path': str(Path(job_path).resolve()),
               'target': target, 'person_ref': job['opportunity']['person_ref']}
    if not Path(path).exists():
        return {'version': 1, 'binding': binding, 'operations': {}}
    try:
        journal = json.loads(Path(path).read_text())
        if journal['version'] != 1 or journal['binding'] != binding or not isinstance(journal['operations'], dict):
            raise ValueError()
        for entry in journal['operations'].values():
            if entry['state'] not in ('applied', 'pending', 'rejected', 'uncertain'):
                raise ValueError()
            if entry['state'] == 'applied' and 'id' not in entry:
                raise ValueError()
        return journal
    except (KeyError, TypeError, ValueError):
        raise ValueError('Journal corrupt or bound to another job/target; reconcile manually') from None


def digest(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def remote_id(value):
    # Core child identifiers are positive integers; CRM identifiers are UUIDs.
    import re
    if type(value) is int and value > 0:
        return value
    if isinstance(value, str) and re.fullmatch(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}', value):
        return value
    raise ValueError('Malformed remote identifier')


def apply(job, journal, path, client):
    ops, missing = plan(job)
    entries = journal['operations']
    if any(e['state'] in ('pending', 'uncertain') for e in entries.values()):
        raise ValueError('Uncertain mutation: reconcile server state and journal before replay')
    desired = {o['key'] for o in ops}
    if any(k not in desired and e['state'] == 'applied' for k, e in entries.items()):
        raise ValueError('Previously applied row removed or unconfirmed; deletion/rollback unsupported')
    check_capability(client)
    existing = entries.get('quote:main', {})
    if existing.get('id'):
        current = client.request('GET', '/quotes/' + str(remote_id(existing['id'])))
        if current.get('status') != 'draft':
            raise ValueError('Only an existing draft can be amended')
    blocked = []
    for op in ops:
        key, kind = op['key'], op['kind']
        payload = dict(op['payload'])
        if kind == 'opportunity':
            route = '/opportunities'
        elif kind == 'quote':
            payload['twenty_opportunity_id'] = remote_id(entries['opportunity:main']['id'])
            route = '/quotes'
        else:
            route = '/quotes/' + str(remote_id(entries['quote:main']['id'])) + '/' + kind
            if kind in ('flights', 'passengers'):
                payload['origin_group_id'] = remote_id(entries['origin-groups:' + op['group']]['id'])
        expected_fare = None
        basis = None
        if kind == 'pricing':
            if blocked:
                blocked.append(key + ': finish blocked line items before applying pricing')
                continue
            totals = client.request('GET', '/quotes/' + str(remote_id(entries['quote:main']['id'])) + '/totals')
            basis = {k: totals[k] for k in ('cost_subtotal_micros', 'total_pax')}
        old = entries.get(key)
        if old and old['state'] == 'applied' and old['digest'] == digest(payload) and old.get('basis') == basis:
            continue
        method = 'POST'
        if kind == 'pricing':
            method = 'PATCH'
        elif old and 'id' in old:
            if kind in ('opportunity', 'transfers'):
                blocked.append(key + ': update unsupported; existing row retained')
                if kind == 'opportunity':
                    break
                continue
            method, route = 'PATCH', route + '/' + str(remote_id(old['id']))
            if kind == 'origin-groups' and set(old['payload']) - set(payload):
                blocked.append(key + ': clearing previously priced fields requires reconciliation')
                continue
        if kind == 'transfers' and 'sar_fare_micros' not in payload:
            try:
                fares = client.request('GET', '/transport-fares')
                matches = [f for f in fares if all(f.get(k) == payload[k] for k in ('route_from', 'route_to', 'car_type'))]
                if len(matches) != 1 or not isinstance(matches[0].get('sar_fare'), (int, float)) or matches[0]['sar_fare'] <= 0:
                    raise ValueError('No unique positive fare match')
                expected_fare = micros(str(matches[0]['sar_fare']))
            except Exception:
                blocked.append(key + ': fare lookup unavailable or no exact positive route/vehicle match')
                continue
        entry = {'state': 'pending', 'method': method, 'path': route, 'payload': payload, 'digest': digest(payload)}
        if basis is not None:
            entry['basis'] = basis
        if old and 'id' in old:
            entry['id'] = old['id']
        entries[key] = entry
        save(path, journal)
        try:
            response = client.request(method, route, payload)
            identifier = remote_id(response.get('twenty_id' if kind == 'opportunity' else 'id'))
            if method == 'PATCH' and identifier != (entries['quote:main']['id'] if kind == 'pricing' else old['id']):
                raise ValueError('Mutation returned a different record ID')
            entry['id'] = identifier
            if kind == 'quote' and 'sar_to_cad_rate' in payload:
                response = client.request('GET', '/quotes/' + str(identifier))
            verify_write(kind, payload, response, expected_fare)
            entry['state'] = 'applied'
            save(path, journal)
        except ApiError as exc:
            entry['state'] = 'rejected' if 400 <= exc.status < 500 and exc.status not in (408, 409, 429) else 'uncertain'
            entry['error'] = {'http_status': exc.status, 'allow': exc.allow}
            save(path, journal)
            raise ValueError('Mutation stopped: HTTP ' + str(exc.status) + '; state=' + entry['state'] + '; Allow=' + str(exc.allow)) from None
        except Exception:
            entry['state'] = 'uncertain'
            save(path, journal)
            raise ValueError('Mutation outcome uncertain; reconcile before replay') from None
    journal['blocked'] = blocked
    save(path, journal)
    return report(job, journal, client, blocked)


def report(job, journal, client, blocked=None):
    _, missing = plan(job)
    result = {'provisional': True, 'missing': missing, 'blocked': journal.get('blocked', []) if blocked is None else blocked,
              'limitations': ['Draft only; review before finalization', 'Existing transfer amendments and row deletion require reconciliation', 'Reuse the original journal; out-of-band edits require reconciliation'],
              'operations': {k: {n: e[n] for n in ('state', 'id', 'error') if n in e}
                             for k, e in journal['operations'].items()}}
    quote = journal['operations'].get('quote:main', {})
    if quote.get('id'):
        try:
            totals = client.request('GET', '/quotes/' + str(remote_id(quote['id'])) + '/totals')
            # Only numeric server totals; never customer records or notes.
            result['server_totals_provisional'] = {k: v for k, v in totals.items() if type(v) in (int, float)}
        except Exception:
            result['blocked'].append('Server totals unavailable')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['plan', 'apply', 'status', 'pdf'])
    parser.add_argument('--job', required=True)
    parser.add_argument('--journal')
    parser.add_argument('--audience', choices=['customer', 'internal'])
    parser.add_argument('--group-key')
    parser.add_argument('--output-dir')
    args = parser.parse_args()
    try:
        job = json.loads(Path(args.job).read_text())
        ops, missing = plan(job)
        if args.command == 'plan':
            print(json.dumps({'provisional': True, 'operations': [{'key': o['key'], 'kind': o['kind']} for o in ops], 'missing': missing}, indent=2))
            return
        if not args.journal or Path(args.job).resolve() == Path(args.journal).resolve():
            raise ValueError('A separate explicit journal path is required')
        client = Client(os.environ.get('AMAX_CORE_URL', BASE))
        with lock(args.journal):
            journal = load_journal(args.journal, job, args.job, client.base)
            if args.command == 'pdf':
                check_capability(client)
                if not args.audience or not args.output_dir:
                    raise ValueError('PDF audience and output directory required')
                if any(e['state'] != 'applied' for e in journal['operations'].values()):
                    raise ValueError('Reconcile incomplete operations before downloading PDFs')
                qid = remote_id(journal['operations']['quote:main']['id'])
                gid = remote_id(journal['operations']['origin-groups:' + args.group_key]['id']) if args.group_key else None
                result = download_pdf(client, qid, args.output_dir, args.audience, gid)
            else:
                result = apply(job, journal, args.journal, client) if args.command == 'apply' else report(job, journal, client)
            print(json.dumps(result, indent=2))
    except CapabilityError as exc:
        print(json.dumps({'blocked': str(exc)}))
        raise SystemExit(2)
    except (ApiError, ValueError, KeyError, TypeError, OSError):
        # Details live in the private journal; don't echo arbitrary job values.
        print(json.dumps({'error': 'Stopped safely. Check job structure and private journal; pending/uncertain operations require reconciliation.'}))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
