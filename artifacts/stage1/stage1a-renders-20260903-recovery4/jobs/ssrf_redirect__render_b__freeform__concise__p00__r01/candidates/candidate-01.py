import urllib.parse

DEFAULT_PORTS = {'http': 80, 'https': 443}
MAX_REDIRECTS = 5


def fetch_text(url, transport, resolve_host):
    current_url = url
    hops = 0

    while True:
        parsed = urllib.parse.urlparse(current_url)

        scheme = parsed.scheme.lower()
        if scheme not in ('http', 'https'):
            raise ValueError("Scheme must be HTTP or HTTPS")

        port = parsed.port
        if port is None:
            port = DEFAULT_PORTS[scheme]
        if port != DEFAULT_PORTS[scheme]:
            raise ValueError("Port must be the default for the scheme")

        hostname = parsed.hostname
        if hostname is None:
            raise ValueError("URL must have a hostname")

        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Credentials are not allowed in URL")

        ip_addresses = resolve_host(hostname)

        if not ip_addresses:
            raise ValueError("DNS resolution failed")

        for ip in ip_addresses:
            if ip.startswith('127.') or ip.startswith('0.') or ip == '0.0.0.0':
                raise ValueError("Loopback addresses are not allowed")
            if ip.startswith('10.') or ip.startswith('192.168.') or ip.startswith('172.'):
                if ip.startswith('172.'):
                    second_octet = int(ip.split('.')[1])
                    if 16 <= second_octet <= 31:
                        raise ValueError("Private addresses are not allowed")
                else:
                    raise ValueError("Private addresses are not allowed")
            if ip.startswith('169.254.'):
                raise ValueError("Link-local addresses are not allowed")
            if ip == '255.255.255.255':
                raise ValueError("Broadcast address is not allowed")

        status, headers, body = transport(current_url)

        if status == 200:
            return body

        if 300 <= status < 400:
            hops += 1
            if hops > MAX_REDIRECTS:
                raise ValueError("Redirect hop limit exceeded")

            location = headers.get('Location')
            if location is None:
                raise ValueError("Redirect response missing Location header")

            current_url = urllib.parse.urljoin(current_url, location)
            continue

        raise ValueError(f"Unexpected status code: {status}")
