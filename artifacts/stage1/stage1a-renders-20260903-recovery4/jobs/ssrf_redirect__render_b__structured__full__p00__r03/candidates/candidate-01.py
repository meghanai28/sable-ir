import urllib.parse
import ipaddress

def fetch_text(url, transport, resolve_host):
    redirect_statuses = {301, 302, 303, 307, 308}
    hop_count = 0
    max_hops = 5
    current_url = url

    def validate_url(url_to_validate):
        parsed = urllib.parse.urlparse(url_to_validate)

        if parsed.scheme not in ('http', 'https'):
            raise ValueError("Invalid scheme")

        default_port = 80 if parsed.scheme == 'http' else 443

        if parsed.port is not None and parsed.port != default_port:
            raise ValueError("Non-default port not allowed")

        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Credentials not allowed")

        hostname = parsed.hostname
        if hostname is None:
            raise ValueError("Missing hostname")

        try:
            ip_addrs = resolve_host(hostname)
        except Exception:
            raise ValueError("DNS resolution failed")

        if not ip_addrs:
            raise ValueError("No IP addresses returned")

        for ip_str in ip_addrs:
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
            if ip.is_reserved:
                raise ValueError("Reserved IP address not allowed")
            if ip.is_unspecified:
                raise ValueError("Unspecified IP address not allowed")

        netloc = hostname
        if parsed.port is not None:
            netloc = f"{hostname}:{parsed.port}"

        normalized_url = urllib.parse.urlunparse((
            parsed.scheme,
            netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            ''
        ))

        return normalized_url

    while True:
        normalized_url = validate_url(current_url)

        status, headers, body = transport(normalized_url)

        if status in redirect_statuses:
            hop_count += 1
            if hop_count > max_hops:
                raise ValueError("Too many redirects")

            location = headers.get('Location')
            if location is None:
                raise ValueError("Missing Location header")

            try:
                current_url = urllib.parse.urljoin(normalized_url, location)
            except Exception:
                raise ValueError("Invalid Location header")

            continue

        if status == 200:
            return str(body)

        raise ValueError(f"Unexpected status: {status}")
