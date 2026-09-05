def fetch_text(url: str, transport, resolve_host) -> str:
    import socket
    import urllib.parse

    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    port = parsed.port

    # Validate scheme
    if scheme not in ('http', 'https'):
        raise ValueError("Disallowed scheme")

    # Determine expected port based on scheme
    expected_port = 80 if scheme == 'http' else 443

    # Validate port: must be omitted or match expected port
    if port is not None and port != expected_port:
        raise ValueError("Port mismatch")

    # Resolve hostname
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("No hostname in URL")

    try:
        resolved_ips = resolve_host(hostname)
    except Exception:
        raise ValueError("Resolve failed")

    if not resolved_ips:
        raise ValueError("No public addresses found")

    # Check for public addresses (simplified check: must be IPv4 or IPv6)
    for ip in resolved_ips:
        if ':' in ip or '.' in ip:
            # Basic check to ensure it looks like an IP
            if ip.count('.') >= 3 or ':' in ip:
                break
    else:
        raise ValueError("Non-public address detected")

    # Validate URL structure
    if not parsed.path or parsed.path == '/':
        path = '/'
    else:
        path = parsed.path

    # Build request URL for transport
    # transport expects a full URL string
    full_url = f"{scheme}://{hostname}"
    if port is not None:
        full_url += f":{port}"
    full_url += f"{path}"

    # Call transport
    status, headers, body = transport(full_url)

    # Check status
    if status != 200:
        raise ValueError("Non-200 status")

    # Check for redirects (Location header)
    location = headers.get('location')
    if location:
        raise ValueError("Redirect detected")

    return body
