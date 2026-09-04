import ipaddress
import re
import urllib.parse


def fetch_text(url, transport, resolve_host):
    def is_public_ip(ip_str):
        try:
            addr = ipaddress.ip_address(ip_str)
            return not (
                addr.is_private
                or addr.is_loopback
                or addr.is_link_local
                or addr.is_multicast
                or addr.is_reserved
                or addr.is_unspecified
                or getattr(addr, 'is_site_local', False)
            )
        except ValueError:
            return False

    def validate_url(target_url):
        parsed = urllib.parse.urlparse(target_url)

        if parsed.scheme not in ('http', 'https'):
            raise ValueError("Disallowed scheme")

        default_port = 443 if parsed.scheme == 'https' else 80
        port = parsed.port if parsed.port is not None else default_port
        if port != default_port:
            raise ValueError("Disallowed port")

        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Disallowed credentials")

        if not parsed.hostname:
            raise ValueError("Missing hostname")

        hostname = parsed.hostname.lower()

        if hostname.startswith('[') and hostname.endswith(']'):
            raise ValueError("IPv6 literal not allowed")

        if re.match(r'^\d+\.\d+\.\d+\.\d+$', hostname):
            raise ValueError("IPv4 literal not allowed")

        if not re.match(r'^[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?)*$', hostname):
            raise ValueError("Invalid hostname")

        ips = resolve_host(hostname)
        if not ips:
            raise ValueError("No DNS resolution")

        for ip in ips:
            if not is_public_ip(ip):
                raise ValueError("Non-public IP")

        return urllib.parse.urlunparse((
            parsed.scheme,
            parsed.netloc if parsed.port is None else f"{parsed.hostname}:{parsed.port}",
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))

    current_url = validate_url(url)

    for hop in range(5):
        status, headers, body = transport(current_url)

        if status == 200:
            return body

        if 300 <= status < 400:
            location = None
            for key, value in headers.items() if hasattr(headers, 'items') else headers:
                if key.lower() == 'location':
                    location = value
                    break

            if location is None:
                raise ValueError("Missing Location header")

            current_url = validate_url(urllib.parse.urljoin(current_url, location))
            continue

        raise ValueError(f"Unexpected status: {status}")

    raise ValueError("Too many redirects")
