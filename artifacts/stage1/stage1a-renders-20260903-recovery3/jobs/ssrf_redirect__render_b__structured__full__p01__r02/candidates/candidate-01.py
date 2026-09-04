import ipaddress
import re
import urllib.parse

def fetch_text(url, transport, resolve_host):
    MAX_REDIRECTS = 5

    def is_public_ip(ip_str):
        try:
            addr = ipaddress.ip_address(ip_str)
            if addr.version == 4:
                if addr.is_loopback:
                    return False
                if addr.is_private:
                    return False
                if addr.is_link_local:
                    return False
                if addr.is_multicast:
                    return False
                if addr.is_reserved:
                    return False
                if addr.is_unspecified:
                    return False
                if addr == ipaddress.ip_address('0.0.0.0'):
                    return False
                if addr == ipaddress.ip_address('255.255.255.255'):
                    return False
            elif addr.version == 6:
                if addr.is_loopback:
                    return False
                if addr.is_private:
                    return False
                if addr.is_link_local:
                    return False
                if addr.is_multicast:
                    return False
                if addr.is_reserved:
                    return False
                if addr.is_unspecified:
                    return False
            return True
        except ValueError:
            return False

    def validate_hostname(hostname):
        if not hostname:
            return False
        if len(hostname) > 253:
            return False
        labels = hostname.split('.')
        for label in labels:
            if not label:
                if len(labels) > 1:
                    return False
                continue
            if len(label) > 63:
                return False
            if label.startswith('-') or label.endswith('-'):
                return False
            if not re.match(r'^[a-zA-Z0-9-]+$', label):
                return False
        return True

    def validate_and_resolve(parsed_url):
        scheme = parsed_url.scheme.lower()
        if scheme not in ('http', 'https'):
            raise ValueError("Disallowed scheme")

        if parsed_url.username is not None or parsed_url.password is not None:
            raise ValueError("Credentials not allowed")

        hostname = parsed_url.hostname
        if hostname is None:
            raise ValueError("Missing hostname")

        port = parsed_url.port
        if scheme == 'http':
            if port is not None and port != 80:
                raise ValueError("Non-default port not allowed")
        elif scheme == 'https':
            if port is not None and port != 443:
                raise ValueError("Non-default port not allowed")

        if not validate_hostname(hostname):
            raise ValueError("Invalid hostname")

        try:
            ips = resolve_host(hostname)
        except Exception:
            raise ValueError("Host resolution failed")

        if not ips:
            raise ValueError("No IPs resolved")

        for ip in ips:
            if not is_public_ip(ip):
                raise ValueError("Non-public IP address")

        netloc = hostname
        if scheme == 'http':
            if port is not None and port != 80:
                netloc = f"{hostname}:{port}"
        elif scheme == 'https':
            if port is not None and port != 443:
                netloc = f"{hostname}:{port}"

        validated_url = urllib.parse.urlunparse((
            scheme,
            netloc,
            parsed_url.path,
            parsed_url.params,
            parsed_url.query,
            parsed_url.fragment
        ))

        return validated_url

    def resolve_location(current_url, location):
        if not location:
            raise ValueError("Missing Location header")
        return urllib.parse.urljoin(current_url, location)

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

            if isinstance(headers, dict):
                location = headers.get('Location')
                if location is None:
                    location = headers.get('location')
            elif isinstance(headers, (list, tuple)):
                location = None
                for name, value in headers:
                    if name.lower() == 'location':
                        location = value
                        break
            else:
                location = None

            if location is None:
                raise ValueError("Missing Location header")

            current_url = resolve_location(validated_url, location)
            parsed = urllib.parse.urlparse(current_url)
            validated_url = validate_and_resolve(parsed)
            continue

        raise ValueError("Unsupported HTTP status")
