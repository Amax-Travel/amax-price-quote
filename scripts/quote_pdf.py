"""Download reviewed draft PDFs through the existing loopback gatekeeper."""
from email.message import Message
from pathlib import Path
import re
import urllib.request


def download_pdf(client, quote_id, output_dir, audience, group_id=None):
    if type(quote_id) is not int or quote_id <= 0 or audience not in ('customer', 'internal'):
        raise ValueError('Invalid PDF selection')
    if group_id is not None and (type(group_id) is not int or group_id <= 0 or audience != 'customer'):
        raise ValueError('Group copies are customer PDFs only')
    path = '/quotes/' + str(quote_id) + '/pdf' + ('/internal' if audience == 'internal' else '')
    if group_id is not None:
        path += '?origin_group_id=' + str(group_id)
    directory = Path(output_dir)
    if not directory.is_dir():
        raise ValueError('PDF output directory must already exist')
    request = urllib.request.Request(client.base + path, method='GET')
    with client.opener.open(request, timeout=180) as response:
        header = Message()
        header['Content-Disposition'] = response.headers.get('Content-Disposition', '')
        name = header.get_filename()
        if not name or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*\.pdf', name):
            raise ValueError('Server returned an unsafe PDF filename')
        if group_id is not None:
            name = name[:-4] + '-group-' + str(group_id) + '.pdf'
        data = response.read(20 * 1024 * 1024 + 1)
        if len(data) > 20 * 1024 * 1024 or not data.startswith(b'%PDF'):
            raise ValueError('Invalid or oversized PDF response')
    # Never overwrite a prior reviewed customer or internal copy.
    target = directory / name
    import os
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return {'downloaded': True, 'audience': audience, 'group_id': group_id, 'bytes': len(data)}
