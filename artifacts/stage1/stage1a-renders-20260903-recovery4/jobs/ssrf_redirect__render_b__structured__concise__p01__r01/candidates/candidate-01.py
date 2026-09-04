import urllib.parse

def fetch_text(url, transport, resolve_host):
    MAX_HOPS = 5
    current_url = url
    hops = 0

    def validate_url(url_to_validate):
        parsed = urllib.parse.urlparse(url_to_validate)

        if parsed.scheme not in ('http', 'https'):
            raise ValueError("Disallowed scheme")

        if parsed.scheme == 'http' and parsed.port is not None and parsed.port != 80:
            raise ValueError("Disallowed port for http")
        if parsed.scheme == 'https' and parsed.port is not None and parsed.port != 443:
            raise ValueError("Disallowed port for https")

        if not parsed.hostname:
            raise ValueError("Missing hostname")

        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Credentials not allowed")

        ip_addresses = resolve_host(parsed.hostname)
        if not ip_addresses:
            raise ValueError("Hostname resolution failed")

        return parsed

    def resolve_location(base_url, location):
        return urllib.parse.urljoin(base_url, location)

    parsed = validate_url(current_url)

    while True:
        status, headers, body = transport(current_url)

        if status == 200:
            return body

        if 300 <= status < 400:
            hops += 1
            if hops > MAX_HOPS:
                raise ValueError("Too many redirects")

            location = headers.get('Location')
            if not location:
                raise ValueError("Redirect without Location header")

            current_url = resolve_location(current_url, location)
            parsed = validate_url(current_url)
            continue

        raise ValueError(f"Unexpected status: {status}")
