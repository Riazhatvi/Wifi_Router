"""RouterOS v7 HTTPS REST client. Credentials remain in memory."""
import base64
import json
import ssl
from urllib import request, error, parse
from decimal import Decimal, InvalidOperation

GB = 1_000_000_000


def quota_bytes(value):
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount <= 0 or amount > 1_000_000:
            raise ValueError()
        result = int(amount * GB)
        if result < 1:
            raise ValueError()
        return result
    except (InvalidOperation, ValueError, OverflowError):
        raise ValueError('Allowance must be above zero and at most 1,000,000 GB.') from None


class RouterError(Exception):
    pass


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Router:
    def __init__(self, host, username, password, ca_file=None):
        host = host.strip().rstrip('/')
        if '://' not in host:
            host = 'https://' + host
        url = parse.urlsplit(host)
        if url.scheme != 'https' or not url.hostname or url.username or url.password or url.path not in ('', '/') or url.query or url.fragment:
            raise ValueError('Enter an HTTPS router hostname or IP, optionally with a port; no path.')
        self.base = host + '/rest/'
        self.context = ssl.create_default_context(cafile=ca_file or None)
        self.authorization = 'Basic ' + base64.b64encode(f'{username}:{password}'.encode()).decode()

    def call(self, path, method='GET', payload=None):
        data = json.dumps(payload).encode() if payload is not None else None
        req = request.Request(self.base + path, data=data, method=method,
                              headers={'Authorization': self.authorization, 'Content-Type': 'application/json'})
        try:
            # Never forward router credentials through an inherited Internet proxy.
            opener = request.build_opener(request.ProxyHandler({}), NoRedirect(), request.HTTPSHandler(context=self.context))
            with opener.open(req, timeout=20) as response:
                body = response.read()
                return json.loads(body) if body else None
        except error.HTTPError as exc:
            raise RouterError(f'Router returned HTTP {exc.code}. Check account permissions and RouterOS configuration. Refresh before retrying a change.') from None
        except (error.URLError, TimeoutError, OSError, ValueError):
            raise RouterError('Router connection failed. Check HTTPS certificate trust, address, network access, and REST service. Refresh before retrying a change; its outcome may be unknown.') from None

    def identity(self):
        return self.call('system/identity')

    def users(self):
        return self.call('ip/hotspot/user')

    def active(self):
        return self.call('ip/hotspot/active')

    @staticmethod
    def item(user_id):
        return 'ip/hotspot/user/' + parse.quote(user_id, safe='')

    def create(self, name, password, allowance, profile):
        if not name.strip() or not password or not profile.strip():
            raise ValueError('Customer username, password, and an existing HotSpot profile are required.')
        return self.call('ip/hotspot/user', 'PUT', {'name': name.strip(), 'password': password,
                         'limit-bytes-total': str(quota_bytes(allowance)), 'profile': profile.strip(), 'disabled': 'false'})

    def set_quota(self, user_id, allowance):
        return self.call(self.item(user_id), 'PATCH', {'limit-bytes-total': str(quota_bytes(allowance))})

    def disconnect(self, user_id):
        users = self.users()
        matches = [u for u in users if u['.id'] == user_id]
        if not matches:
            raise RouterError('Customer no longer exists. Refresh the list.')
        for session in self.active():
            if session.get('user') == matches[0].get('name'):
                self.call('ip/hotspot/active/' + parse.quote(session['.id'], safe=''), 'DELETE')

    def enable(self, user_id, enabled):
        self.call(self.item(user_id), 'PATCH', {'disabled': 'false' if enabled else 'true'})
        if not enabled:
            self.disconnect(user_id)

    def renew(self, user_id):
        # Fail closed during a multi-step renewal; do not enable until counters reset.
        self.enable(user_id, False)
        self.call('ip/hotspot/user/reset-counters', 'POST', {'.id': user_id})
        self.enable(user_id, True)
