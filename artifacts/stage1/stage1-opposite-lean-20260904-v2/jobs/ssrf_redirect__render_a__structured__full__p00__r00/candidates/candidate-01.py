import ipaddress
import urllib.parse

def fetch_text(url, transport, resolve_host):
    max_hops = 5
    hop_count = 0
    current_url = url

    def validate_and_resolve(url_to_validate):
        parsed = urllib.parse.urlparse(url_to_validate)

        scheme = parsed.scheme.lower()
        if scheme not in ('http', 'https'):
            raise ValueError("Invalid scheme")

        if scheme == 'http':
            default_port = 80
        else:
            default_port = 443

        if parsed.port is not None and parsed.port != default_port:
            raise ValueError("Non-default port not allowed")

        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Credentials not allowed")

        hostname = parsed.hostname
        if hostname is None:
            raise ValueError("Missing hostname")

        ip_addresses = resolve_host(hostname)

        for ip_str in ip_addresses:
            try:
                ip = ipaddress.ip_address(ip_str)
            except ValueError:
                raise ValueError("Invalid IP address")

            if ip.is_private:
                raise ValueError("Private IP address not allowed")
            if ip.is_loopback:
                raise ValueError("Loopback IP address not allowed")
            if ip.is_link_local:
                raise ValueError("Link-local IP address not allowed")
            if ip.is_multicast:
                raise ValueError("Multicast IP address not allowed")

        return parsed

    while True:
        parsed = validate_and_resolve(current_url)

        status, headers, body = transport(current_url)

        if status in (301, 302, 303, 307, 308):
            location = headers.get('Location')
            if location is None:
                raise ValueError("Missing Location header")

            current_url = urllib.parse.urljoin(current_url, location)

            hop_count += 1
            if hop_count > max_hops:
                raise ValueError("Too many redirects")

            continue

        if status == 200:
            return str(body)

        raise ValueError("Non-200 terminal status")
