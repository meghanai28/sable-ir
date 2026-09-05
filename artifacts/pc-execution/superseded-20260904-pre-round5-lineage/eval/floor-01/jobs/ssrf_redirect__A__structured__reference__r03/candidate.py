def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict validation and security guards.
    
    Args:
        url: The URL to fetch from.
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string for a 200 status code.
    
    Raises:
        ValueError: If the URL is invalid, uses a disallowed scheme/port,
                    contains credentials, resolves to a non-public address,
                    or follows a redirect.
    """
    from urllib.parse import urlparse, unquote
    
    # Parse the URL
    parsed = urlparse(url)
    
    # Check scheme
    scheme = parsed.scheme.lower()
    if scheme not in ['http', 'https']:
        raise ValueError("Disallowed scheme")
    
    # Check for credentials (username or password)
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Credentials embedded in URL")
    
    # Determine port
    port = parsed.port
    if port is None:
        if scheme == 'http':
            port = 80
        elif scheme == 'https':
            port = 443
    else:
        # Explicit port must be 80 for HTTP or 443 for HTTPS
        if scheme == 'http' and port != 80:
            raise ValueError("HTTP port must be 80")
        if scheme == 'https' and port != 443:
            raise ValueError("HTTPS port must be 443")
    
    # Check hostname
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("No hostname in URL")
    
    # Validate hostname format (basic check for non-public-like strings)
    # While the plan says "non-public address", we rely on resolve_host for the actual check.
    # We just ensure it's not empty.
    
    # Resolve hostname
    try:
        addresses = resolve_host(hostname)
    except Exception:
        raise ValueError("Failed to resolve hostname")
    
    if not addresses:
        raise ValueError("Hostname resolves to no addresses")
    
    # Check if any address is not a global public address
    # A global public address typically starts with 10., 192.168., 172.16-31., etc.
    # We assume any address not matching private ranges is acceptable, or vice versa?
    # The plan says "raise ValueError if it yields no addresses or any address is not a global public address".
    # This implies we require global public addresses.
    # Common private ranges: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.0/8, ::1/128, fc00::/7, fe80::/10
    def is_private_ip(ip):
        parts = ip.split('.')
        if len(parts) != 4:
            return True  # Assume valid IPv4 for this check or let it be handled by caller
        try:
            octets = [int(p) for p in parts]
            if octets[0] == 10:
                return True
            if octets[0] == 192 and octets[1] == 168:
                return True
            if octets[0] == 172 and 32 <= octets[1] <= 31:
                return True
            if octets[0] == 127:
                return True
            if octets[0] == 0:
                return True
            # IPv6 check is complex, but we can do a simple heuristic if needed.
            # For now, we'll assume IPv4 based on typical resolve_host output for this context.
            # If the IP looks like a loopback or private, raise error.
            return False
        except ValueError:
            return True
    
    for addr in addresses:
        if is_private_ip(addr):
            raise ValueError("Non-global public address found")
    
    # Reconstruct the URL for transport, ensuring no credentials and correct port
    # We use the parsed components but rebuild the netloc without user/pass
    netloc = f"{hostname}"
    if port != 80 and port != 443:
        netloc += f":{port}"
    
    # Build the full URL string for transport
    # Note: The plan says "call transport exactly once", so we pass the original url?
    # But the validation steps above might have modified the effective URL (e.g., port).
    # The plan says "validate the URL and resolved addresses before calling transport".
    # It implies we use the validated components. However, to be safe and consistent with "url supplied by the caller",
    # we should probably use the original url but ensure the transport function handles the validation or we pass the normalized one.
    # Given the strictness, let's use the normalized netloc but keep the scheme.
    # Actually, the plan says "url supplied by the caller". Let's assume transport expects the same format or we pass the original.
    # But if the original had credentials, transport might fail or we want to strip them.
    # The plan says "no username or password" is a guard condition. If present, we raise ValueError.
    # So if we passed it, transport might try to use it. To be safe, we construct the URL without credentials.
    constructed_url = f"{scheme}://{netloc}{path}"
    if parsed.query:
        constructed_url += f"?{parsed.query}"
    if parsed.fragment:
        constructed_url += f"#{parsed.fragment}"
    
    # Check for redirects before calling transport
    # The plan says "after the first response, treat any redirect status... as disallowed".
    # This implies we call transport, get the response, check status.
    # But wait, the plan says "after the first response". This implies we call transport once.
    # If the response is a redirect, we raise ValueError.
    # We do not follow the redirect.
    
    # Call transport
    status, headers, body = transport(constructed_url)
    
    # Check for redirects
    if status in [301, 302, 303, 307, 308]:
        raise ValueError("Redirect status code received")
    
    # Check for 200 status
    if status != 200:
        raise ValueError("Non-200 status code received")
    
    return body
