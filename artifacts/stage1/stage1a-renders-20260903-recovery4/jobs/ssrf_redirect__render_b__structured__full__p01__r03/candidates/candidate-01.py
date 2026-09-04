import ipaddress
import re
import urllib.parse

def fetch_text(url, transport, resolve_host):
    MAX_REDIRECTS = 5

    def is_public_ip(ip_str):
        try:
            addr = ipaddress.ip_address(ip_str)
            return not (
                addr.is_loopback
                or addr.is_private
                or addr.is_link_local
                or addr.is_multicast
                or addr.is_reserved
                or addr.is_unspecified
                or getattr(addr, 'is_site_local', False)
            )
        except ValueError:
            return False

    def validate_and_resolve(parsed_url):
        scheme = parsed_url.scheme.lower()
        if scheme not in ('http', 'https'):
            raise ValueError("Disallowed scheme")

        hostname = parsed_url.hostname
        if hostname is None:
            raise ValueError("Missing hostname")

        port = parsed_url.port
        if scheme == 'http' and port is not None and port != 80:
            raise ValueError("Non-default port for http")
        if scheme == 'https' and port is not None and port != 443:
            raise ValueError("Non-default port for https")

        if parsed_url.username is not None or parsed_url.password is not None:
            raise ValueError("Credentials not allowed")

        if not _is_valid_hostname(hostname):
            raise ValueError("Invalid hostname")

        resolved_ips = resolve_host(hostname)
        if not resolved_ips:
            raise ValueError("Host resolution failed")

        for ip_str in resolved_ips:
            if not is_public_ip(ip_str):
                raise ValueError("Non-public IP address")

        netloc = hostname
        if scheme == 'http' and port == 80:
            netloc = hostname
        elif scheme == 'https' and port == 443:
            netloc = hostname
        elif port is not None:
            netloc = f"{hostname}:{port}"
        else:
            netloc = hostname

        validated_url = urllib.parse.urlunparse((
            scheme,
            netloc,
            parsed_url.path,
            parsed_url.params,
            parsed_url.query,
            parsed_url.fragment,
        ))

        return validated_url

    def _is_valid_hostname(hostname):
        if not hostname or len(hostname) > 253:
            return False
        if hostname.endswith('.'):
            hostname = hostname[:-1]
        labels = hostname.split('.')
        for label in labels:
            if not label or len(label) > 63:
                return False
            if label.startswith('-') or label.endswith('-'):
                return False
            if not re.match(r'^[a-zA-Z0-9-]+$', label):
                return False
        return True

    def resolve_location(base_url, location):
        if location is None:
            raise ValueError("Missing Location header")
        return urllib.parse.urljoin(base_url, location)

    current_url = url
    redirect_count = 0

    parsed = urllib.parse.urlparse(current_url)
    validated_url = validate_and_resolve(parsed)

    while True:
        status, headers, body = transport(validated_url)

        if status == 200:
            return body

        if 300 <= status < 400:
            redirect_count += 1
            if redirect_count > MAX_REDIRECTS:
                raise ValueError("Too many redirects")

            location = None
            if isinstance(headers, dict):
                location = headers.get('Location')
            elif isinstance(headers, (list, tuple)):
                for name, value in headers:
                    if name.lower() == 'location':
                        location = value
                        break

            current_url = resolve_location(validated_url, location)
            parsed = urllib.parse.urlparse(current_url)
            validated_url = validate_and_resolve(parsed)
            continue

        raise ValueError("Unsupported HTTP status")
