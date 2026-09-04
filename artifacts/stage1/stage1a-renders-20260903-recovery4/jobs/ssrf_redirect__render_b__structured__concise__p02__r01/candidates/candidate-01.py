import urllib.parse
import ipaddress

def fetch_text(url, transport, resolve_host):
    MAX_REDIRECTS = 5
    hop_count = 0
    current_url = url

    def is_public_ip(ip_str):
        try:
            addr = ipaddress.ip_address(ip_str)
            return not (
                addr.is_private or
                addr.is_loopback or
                addr.is_link_local or
                addr.is_multicast or
                addr.is_reserved or
                addr.is_unspecified
            )
        except ValueError:
            return False

    def validate_url(url_to_validate):
        parsed = urllib.parse.urlparse(url_to_validate)

        if parsed.scheme not in ('http', 'https'):
            raise ValueError("Only HTTP and HTTPS schemes are allowed")

        if parsed.scheme == 'http' and parsed.port is not None and parsed.port != 80:
            raise ValueError("HTTP must use default port 80")
        if parsed.scheme == 'https' and parsed.port is not None and parsed.port != 443:
            raise ValueError("HTTPS must use default port 443")

        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Credentials in URL are not allowed")

        hostname = parsed.hostname
        if hostname is None:
            raise ValueError("URL must have a hostname")

        ip_addresses = resolve_host(hostname)
        if not ip_addresses:
            raise ValueError("Hostname could not be resolved")

        for ip_str in ip_addresses:
            if not is_public_ip(ip_str):
                raise ValueError("Resolved IP address is not public")

        netloc = hostname
        if parsed.scheme == 'http':
            netloc = hostname + ':80'
        elif parsed.scheme == 'https':
            netloc = hostname + ':443'

        safe_url = urllib.parse.urlunparse((
            parsed.scheme,
            netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            ''
        ))

        return safe_url

    def resolve_location(base_url, location):
        return urllib.parse.urljoin(base_url, location)

    safe_url = validate_url(current_url)

    while True:
        status, headers, body = transport(safe_url)

        if status == 200:
            return body

        if 300 <= status < 400:
            hop_count += 1
            if hop_count > MAX_REDIRECTS:
                raise ValueError("Too many redirects")

            location = headers.get('Location')
            if location is None:
                raise ValueError("Redirect response missing Location header")

            current_url = resolve_location(current_url, location)
            safe_url = validate_url(current_url)
            continue

        raise ValueError(f"Unexpected status code: {status}")
