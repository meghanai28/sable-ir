import ipaddress
import urllib.parse


def fetch_text(url, transport, resolve_host):
    MAX_REDIRECTS = 5
    redirect_count = 0

    def validate_and_fetch(current_url):
        nonlocal redirect_count

        parsed = urllib.parse.urlparse(current_url)

        # Validate scheme
        scheme = parsed.scheme.lower()
        if scheme not in ('http', 'https'):
            raise ValueError("Invalid scheme")

        # Validate port
        if parsed.port is not None:
            if scheme == 'http' and parsed.port != 80:
                raise ValueError("Invalid HTTP port")
            if scheme == 'https' and parsed.port != 443:
                raise ValueError("Invalid HTTPS port")

        # Validate credentials (userinfo)
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Credentials not allowed")

        # Extract hostname
        hostname = parsed.hostname
        if hostname is None:
            raise ValueError("Missing hostname")

        # Resolve and validate IP addresses
        try:
            ip_addresses = resolve_host(hostname)
        except Exception:
            raise ValueError("DNS resolution failed")

        if not ip_addresses:
            raise ValueError("No IP addresses returned")

        for ip_text in ip_addresses:
            try:
                ip = ipaddress.ip_address(ip_text)
            except ValueError:
                raise ValueError("Invalid IP address format")

            # Reject private, loopback, link-local, and multicast ranges
            if ip.is_private:
                raise ValueError("Private IP address not allowed")
            if ip.is_loopback:
                raise ValueError("Loopback IP address not allowed")
            if ip.is_link_local:
                raise ValueError("Link-local IP address not allowed")
            if ip.is_multicast:
                raise ValueError("Multicast IP address not allowed")
            # Also reject reserved, unspecified, and other non-public ranges
            if ip.is_reserved:
                raise ValueError("Reserved IP address not allowed")
            if ip.is_unspecified:
                raise ValueError("Unspecified IP address not allowed")

        # Call transport
        status, headers, body = transport(current_url)

        # Handle redirects
        if status in (301, 302, 303, 307, 308):
            redirect_count += 1
            if redirect_count > MAX_REDIRECTS:
                raise ValueError("Too many redirects")

            location = headers.get('Location')
            if location is None:
                raise ValueError("Missing Location header")

            # Resolve Location against current URL to form absolute URL
            new_url = urllib.parse.urljoin(current_url, location)

            return validate_and_fetch(new_url)

        # Handle successful response
        if status == 200:
            return body

        # Any other status is disallowed
        raise ValueError(f"Unexpected status: {status}")

    return validate_and_fetch(url)
