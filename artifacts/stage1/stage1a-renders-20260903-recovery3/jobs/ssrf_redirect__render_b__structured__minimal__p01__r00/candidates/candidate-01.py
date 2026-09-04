import urllib.parse

def fetch_text(url, transport, resolve_host):
    MAX_REDIRECTS = 5
    redirect_count = 0
    current_url = url

    def validate_url(url_to_validate):
        parsed = urllib.parse.urlparse(url_to_validate)

        if parsed.scheme not in ('http', 'https'):
            raise ValueError("Only HTTP and HTTPS schemes are allowed")

        if parsed.scheme == 'http' and parsed.port is not None and parsed.port != 80:
            raise ValueError("HTTP must use default port 80")
        if parsed.scheme == 'https' and parsed.port is not None and parsed.port != 443:
            raise ValueError("HTTPS must use default port 443")

        hostname = parsed.hostname
        if hostname is None:
            raise ValueError("URL must have a hostname")

        if '@' in parsed.netloc:
            raise ValueError("Credentials in URL are not allowed")

        ip_addresses = resolve_host(hostname)
        if not ip_addresses:
            raise ValueError("Could not resolve hostname")

        for ip in ip_addresses:
            if ip.startswith('127.') or ip == '0.0.0.0' or ip == '::1' or ip.startswith('::ffff:127.'):
                raise ValueError("Loopback addresses are not allowed")
            if ip.startswith('10.') or ip.startswith('172.'):
                if ip.startswith('172.'):
                    second_octet = int(ip.split('.')[1])
                    if 16 <= second_octet <= 31:
                        raise ValueError("Private addresses are not allowed")
                else:
                    raise ValueError("Private addresses are not allowed")
            if ip.startswith('192.168.'):
                raise ValueError("Private addresses are not allowed")
            if ip.startswith('169.254.'):
                raise ValueError("Link-local addresses are not allowed")
            if ip.startswith('fc00:') or ip.startswith('fd00:'):
                raise ValueError("Unique local addresses are not allowed")
            if ip == '::' or ip == '0:0:0:0:0:0:0:0':
                raise ValueError("Unspecified address is not allowed")

        return parsed

    def resolve_location(base_url, location):
        return urllib.parse.urljoin(base_url, location)

    parsed = validate_url(current_url)

    while True:
        status, headers, body = transport(current_url)

        if status == 200:
            return body

        if status in (301, 302, 303, 307, 308):
            redirect_count += 1
            if redirect_count > MAX_REDIRECTS:
                raise ValueError("Too many redirects")

            location = None
            for key, value in headers:
                if key.lower() == 'location':
                    location = value
                    break

            if location is None:
                raise ValueError("Redirect response missing Location header")

            current_url = resolve_location(current_url, location)
            parsed = validate_url(current_url)

            continue

        raise ValueError(f"Unexpected status code: {status}")
