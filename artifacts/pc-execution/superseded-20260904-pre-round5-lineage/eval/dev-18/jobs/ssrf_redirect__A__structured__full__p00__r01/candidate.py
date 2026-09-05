def fetch_text(url: str, transport, resolve_host) -> str:
    from urllib.parse import urlparse, urljoin

    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    port = parsed.port

    # Guard: Accept only HTTP or HTTPS on their default ports
    allowed_schemes = {
        'http': 80,
        'https': 443
    }

    if scheme not in allowed_schemes:
        raise ValueError(f"Disallowed scheme: {scheme}")

    if port is not None and port != allowed_schemes[scheme]:
        raise ValueError(f"Disallowed port {port} for scheme {scheme}")

    # Guard: Resolve hostname and ensure it resolves to at least one IP
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("Invalid URL: missing hostname")

    try:
        ip_addresses = resolve_host(hostname)
        if not ip_addresses:
            raise ValueError(f"Hostname {hostname} does not resolve to any IP address")
    except Exception as e:
        raise ValueError(f"Failed to resolve hostname {hostname}: {e}")

    # Order: Construct the initial request URL without following redirects
    # We use the resolved scheme and port, but keep the path and query
    final_url = f"{scheme}://{hostname}{url.path}"
    if url.query:
        final_url += f"?{url.query}"

    # Attempt to open the connection
    status, headers, body = transport(final_url)

    # Guard: Reject every redirect response, even if Location appears public
    if status != 200:
        raise ValueError(f"Request failed with status {status}: {headers}")

    # Effect: Return the body text
    return body.decode('utf-8') if isinstance(body, bytes) else body
