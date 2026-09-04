import ipaddress
import re
import urllib.parse

def fetch_text(url, transport, resolve_host):
    MAX_REDIRECTS = 5
    redirect_count = 0
    current_url = url

    def validate_hostname_syntax(hostname):
        if not hostname:
            return False
        if len(hostname) > 253:
            return False
        labels = hostname.split('.')
        for label in labels:
            if not label:
                return False
            if len(label) > 63:
                return False
            if label.startswith('-') or label.endswith('-'):
                return False
            if not re.match(r'^[a-zA-Z0-9-]+$', label):
                return False
        return True

    def is_public_ip(ip_str):
        try:
            addr = ipaddress.ip_address(ip_str)
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
            if hasattr(addr, 'is_global') and not addr.is_global:
                if not (addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_multicast or addr.is_reserved or addr.is_unspecified):
                    return False
            return True
        except ValueError:
            return False

    def validate_and_resolve(parsed_url):
        scheme = parsed_url.scheme.lower()
        if scheme not in ('http', 'https'):
            raise ValueError("Disallowed scheme")

        if parsed_url.username is not None or parsed_url.password is not None:
            raise ValueError("Credentials not allowed")

        hostname = parsed_url.hostname
        if hostname is None:
            raise ValueError("Missing hostname")

        if not validate_hostname_syntax(hostname):
            raise ValueError("Invalid hostname syntax")

        port = parsed_url.port
        if scheme == 'http' and port is not None and port != 80:
            raise ValueError("Non-default port for http")
        if scheme == 'https' and port is not None and port != 443:
            raise ValueError("Non-default port for https")

        try:
            resolved_ips = resolve_host(hostname)
        except Exception:
            raise ValueError("Host resolution failed")

        if not resolved_ips:
            raise ValueError("No IPs resolved")

        for ip_str in resolved_ips:
            if not is_public_ip(ip_str):
                raise ValueError("Non-public IP address")

        netloc = hostname
        if port is not None:
            if scheme == 'http' and port == 80:
                netloc = hostname
            elif scheme == 'https' and port == 443:
                netloc = hostname
            else:
                netloc = f"{hostname}:{port}"
        else:
            netloc = hostname

        validated_url = urllib.parse.urlunparse((
            scheme,
            netloc,
            parsed_url.path,
            parsed_url.params,
            parsed_url.query,
            parsed_url.fragment
        ))

        return validated_url

    def get_location(headers):
        if headers is None:
            return None
        if isinstance(headers, dict):
            for key, value in headers.items():
                if key.lower() == 'location':
                    return value
            return None
        if isinstance(headers, (list, tuple)):
            for item in headers:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    if item[0].lower() == 'location':
                        return item[1]
            return None
        return None

    parsed = urllib.parse.urlparse(current_url)
    current_url = validate_and_resolve(parsed)

    while True:
        status, headers, body = transport(current_url)

        if status == 200:
            return body

        if status in (301, 302, 303, 307, 308):
            redirect_count += 1
            if redirect_count > MAX_REDIRECTS:
                raise ValueError("Too many redirects")

            location = get_location(headers)
            if location is None:
                raise ValueError("Missing Location header")

            try:
                next_url = urllib.parse.urljoin(current_url, location)
            except Exception:
                raise ValueError("Invalid Location header")

            try:
                parsed_next = urllib.parse.urlparse(next_url)
            except Exception:
                raise ValueError("Invalid redirect URL")

            current_url = validate_and_resolve(parsed_next)
            continue

        raise ValueError(f"Unsupported HTTP status: {status}")
