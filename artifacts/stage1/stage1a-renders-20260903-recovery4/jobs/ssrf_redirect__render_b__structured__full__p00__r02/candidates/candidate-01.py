import ipaddress
import urllib.parse


def fetch_text(url, transport, resolve_host):
    max_hops = 5
    hop_count = 0
    current_url = url

    while True:
        parsed = urllib.parse.urlparse(current_url)

        # Validate scheme
        if parsed.scheme not in ('http', 'https'):
            raise ValueError("Invalid scheme")

        # Validate port
        default_port = 80 if parsed.scheme == 'http' else 443
        if parsed.port is not None and parsed.port != default_port:
            raise ValueError("Non-default port not allowed")
        if parsed.port is None:
            # Ensure no explicit port in netloc that urlparse missed
            # Check for : in hostname part (excluding IPv6)
            hostname_part = parsed.netloc
            if '@' in hostname_part:
                hostname_part = hostname_part.split('@')[-1]
            if hostname_part.startswith('['):
                # IPv6 literal
                if ']:' in hostname_part:
                    raise ValueError("Non-default port not allowed")
            else:
                if ':' in hostname_part:
                    raise ValueError("Non-default port not allowed")

        # Validate credentials (userinfo)
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Credentials not allowed")

        # Extract hostname
        hostname = parsed.hostname
        if hostname is None:
            raise ValueError("Missing hostname")

        # Resolve and validate IP addresses
        try:
            ip_texts = resolve_host(hostname)
        except Exception:
            raise ValueError("DNS resolution failed")

        for ip_text in ip_texts:
            try:
                ip = ipaddress.ip_address(ip_text)
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

        # Call transport
        status, headers, body = transport(current_url)

        # Handle redirects
        if status in (301, 302, 303, 307, 308):
            if hop_count >= max_hops:
                raise ValueError("Too many redirects")

            location = headers.get('Location')
            if location is None:
                raise ValueError("Missing Location header")

            # Resolve Location against current URL
            try:
                current_url = urllib.parse.urljoin(current_url, location)
            except Exception:
                raise ValueError("Invalid Location header")

            hop_count += 1
            continue

        # Handle success
        if status == 200:
            return body

        # Any other status is an error
        raise ValueError(f"Unexpected status: {status}")
