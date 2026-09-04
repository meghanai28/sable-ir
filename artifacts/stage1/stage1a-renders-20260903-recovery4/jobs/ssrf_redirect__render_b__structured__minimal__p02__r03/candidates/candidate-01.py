import urllib.parse
import ipaddress

def fetch_text(url, transport, resolve_host):
    MAX_REDIRECTS = 5
    redirect_count = 0
    current_url = url

    def validate_scheme_port(parsed):
        if parsed.scheme not in ('http', 'https'):
            raise ValueError("Disallowed URL scheme")
        if parsed.scheme == 'http' and parsed.port is not None and parsed.port != 80:
            raise ValueError("Disallowed non-default port for http")
        if parsed.scheme == 'https' and parsed.port is not None and parsed.port != 443:
            raise ValueError("Disallowed non-default port for https")

    def validate_hostname(hostname):
        if not hostname:
            raise ValueError("Missing hostname")

    def validate_ips(hostname):
        ips = resolve_host(hostname)
        if not ips:
            raise ValueError("No IP addresses resolved")
        for ip_str in ips:
            try:
                ip = ipaddress.ip_address(ip_str)
            except ValueError:
                raise ValueError("Invalid IP address from DNS")
            if ip.is_loopback or ip.is_private or ip.is_reserved or ip.is_multicast or ip.is_link_local:
                raise ValueError("Disallowed IP address")
            if ip.version == 6 and ip.ipv4_mapped is not None:
                ipv4 = ip.ipv4_mapped
                if ipv4.is_loopback or ipv4.is_private or ipv4.is_reserved or ipv4.is_multicast or ipv4.is_link_local:
                    raise ValueError("Disallowed IPv4-mapped address")
        return ips

    def validate_url(url_str):
        parsed = urllib.parse.urlparse(url_str)
        if not parsed.scheme or not parsed.hostname:
            raise ValueError("Invalid URL")
        validate_scheme_port(parsed)
        validate_hostname(parsed.hostname)
        validate_ips(parsed.hostname)
        return parsed

    def resolve_location(current_parsed, location):
        resolved = urllib.parse.urljoin(current_parsed.geturl(), location)
        resolved_parsed = urllib.parse.urlparse(resolved)
        return resolved_parsed

    def check_credentials(parsed):
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Credentials not allowed in URL")

    parsed = validate_url(current_url)
    check_credentials(parsed)

    while True:
        status, headers, body = transport(current_url)

        if status == 200:
            return body

        if 300 <= status < 400:
            redirect_count += 1
            if redirect_count > MAX_REDIRECTS:
                raise ValueError("Too many redirects")

            location = headers.get('Location')
            if not location:
                raise ValueError("Redirect without Location header")

            current_parsed = urllib.parse.urlparse(current_url)
            new_parsed = resolve_location(current_parsed, location)

            if not new_parsed.scheme or not new_parsed.hostname:
                raise ValueError("Invalid redirect URL")

            if new_parsed.scheme != current_parsed.scheme:
                raise ValueError("Redirect scheme changed")

            validate_scheme_port(new_parsed)

            if new_parsed.port != current_parsed.port:
                raise ValueError("Redirect port changed")

            check_credentials(new_parsed)

            validate_hostname(new_parsed.hostname)
            validate_ips(new_parsed.hostname)

            current_url = new_parsed.geturl()
            continue

        raise ValueError(f"Unsupported HTTP status: {status}")
