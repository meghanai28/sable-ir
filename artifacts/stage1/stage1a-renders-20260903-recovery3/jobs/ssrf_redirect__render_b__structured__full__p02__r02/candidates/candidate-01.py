import ipaddress
import urllib.parse

def fetch_text(url, transport, resolve_host):
    max_redirects = 5
    hop_count = 0
    current_url = url

    while True:
        # Step 1: Parse the input URL into components and normalize
        parsed = urllib.parse.urlparse(current_url)

        # Step 2: Validate scheme
        scheme = parsed.scheme.lower()
        if scheme not in ('http', 'https'):
            raise ValueError("Invalid scheme")

        # Validate port is default or absent
        if parsed.port is not None:
            if scheme == 'http' and parsed.port != 80:
                raise ValueError("Invalid port for http")
            if scheme == 'https' and parsed.port != 443:
                raise ValueError("Invalid port for https")

        # Validate absence of userinfo credentials
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Credentials not allowed")

        # Validate hostname is present
        hostname = parsed.hostname
        if not hostname:
            raise ValueError("Missing hostname")

        # Step 3: Call resolve_host on the hostname
        try:
            ip_addresses = resolve_host(hostname)
        except Exception:
            raise ValueError("DNS resolution failed")

        if not ip_addresses:
            raise ValueError("No IP addresses returned")

        # Validate each returned IP address
        for ip_str in ip_addresses:
            try:
                ip = ipaddress.ip_address(ip_str)
            except ValueError:
                raise ValueError("Invalid IP address format")

            # Reject private, loopback, link-local, multicast, and unspecified addresses
            if ip.is_private:
                raise ValueError("Private IP address not allowed")
            if ip.is_loopback:
                raise ValueError("Loopback IP address not allowed")
            if ip.is_link_local:
                raise ValueError("Link-local IP address not allowed")
            if ip.is_multicast:
                raise ValueError("Multicast IP address not allowed")
            if ip.is_unspecified:
                raise ValueError("Unspecified IP address not allowed")

        # Step 4: Reconstruct the canonical validated URL without credentials
        # Build netloc without userinfo, with default port omitted
        if scheme == 'https':
            default_port = 443
        else:
            default_port = 80

        if parsed.port is not None and parsed.port != default_port:
            # This shouldn't happen due to earlier validation, but for safety
            netloc = hostname + ':' + str(parsed.port)
        else:
            netloc = hostname

        # Reconstruct URL with original path, query, fragment
        validated_url = urllib.parse.urlunparse((
            scheme,
            netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))

        # Step 5: Call transport with validated URL
        try:
            status, headers, body = transport(validated_url)
        except Exception:
            raise ValueError("Transport failed")

        # Step 6: If status is 200, return body
        if status == 200:
            return body

        # Step 7: If status is redirect (3xx) with Location header
        if 300 <= status < 400:
            location = headers.get('Location')
            if location is None:
                raise ValueError("Redirect without Location header")

            hop_count += 1
            if hop_count > max_redirects:
                raise ValueError("Too many redirects")

            # Step 8: Resolve Location against current validated URL per RFC 3986
            current_url = urllib.parse.urljoin(validated_url, location)
            continue

        # Step 9: Non-200, non-redirect status
        raise ValueError("Unexpected HTTP status: {}".format(status))
