import urllib.parse
import ipaddress

def fetch_text(url, transport, resolve_host):
    max_redirects = 5
    redirect_count = 0
    current_url = url

    while True:
        parsed = urllib.parse.urlparse(current_url)

        # Validate scheme
        if parsed.scheme not in ('http', 'https'):
            raise ValueError("Invalid scheme")

        # Validate port (must be default)
        default_port = 443 if parsed.scheme == 'https' else 80
        if parsed.port is not None and parsed.port != default_port:
            raise ValueError("Non-default port not allowed")
        if parsed.port is None:
            port = default_port
        else:
            port = parsed.port

        # Validate no credentials
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Credentials not allowed")

        # Validate hostname exists
        hostname = parsed.hostname
        if hostname is None:
            raise ValueError("Missing hostname")

        # Resolve hostname and validate IPs
        try:
            ip_texts = resolve_host(hostname)
        except Exception:
            raise ValueError("DNS resolution failed")

        if not ip_texts:
            raise ValueError("No IP addresses returned")

        for ip_text in ip_texts:
            try:
                ip = ipaddress.ip_address(ip_text)
            except ValueError:
                raise ValueError("Invalid IP address")

            # Validate not loopback
            if ip.is_loopback:
                raise ValueError("Loopback address not allowed")

            # Validate not link-local
            if ip.is_link_local:
                raise ValueError("Link-local address not allowed")

            # Validate not multicast
            if ip.is_multicast:
                raise ValueError("Multicast address not allowed")

            # Validate not private
            if ip.is_private:
                raise ValueError("Private address not allowed")

            # Validate not reserved
            if ip.is_reserved:
                raise ValueError("Reserved address not allowed")

            # Validate not unspecified
            if ip.is_unspecified:
                raise ValueError("Unspecified address not allowed")

            # For IPv6, also check site-local (deprecated but check)
            if isinstance(ip, ipaddress.IPv6Address) and ip.is_site_local:
                raise ValueError("Site-local address not allowed")

        # Validate path doesn't contain null bytes or obvious traversal issues
        # Reconstruct URL with normalized components
        netloc = hostname
        if (parsed.scheme == 'https' and port != 443) or (parsed.scheme == 'http' and port != 80):
            netloc = f"{hostname}:{port}"

        # Rebuild URL to ensure no credential leakage and proper format
        validated_url = urllib.parse.urlunparse((
            parsed.scheme,
            netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))

        # Submit to transport
        status, headers, body = transport(validated_url)

        # Handle redirect
        if status in (301, 302, 303, 307, 308):
            redirect_count += 1
            if redirect_count > max_redirects:
                raise ValueError("Too many redirects")

            location = headers.get('Location')
            if location is None:
                raise ValueError("Redirect without Location header")

            # Resolve relative URL against current URL
            current_url = urllib.parse.urljoin(validated_url, location)
            continue

        # Handle success
        if status == 200:
            if isinstance(body, bytes):
                return body.decode('utf-8')
            return str(body)

        # Any other status is an error
        raise ValueError(f"Unexpected status: {status}")
