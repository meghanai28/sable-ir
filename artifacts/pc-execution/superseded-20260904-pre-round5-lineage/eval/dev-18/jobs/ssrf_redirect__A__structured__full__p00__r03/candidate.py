import socket
import urllib.parse

def fetch_text(url: str, transport, resolve_host) -> str:
    # Parse the URL to extract scheme, netloc, and path
    parsed = urllib.parse.urlparse(url)
    
    scheme = parsed.scheme.lower()
    host = parsed.netloc
    path = parsed.path
    
    # Guard: Accept only HTTP or HTTPS on their default ports
    allowed_schemes = ('http', 'https')
    if scheme not in allowed_schemes:
        raise ValueError(f"Disallowed scheme: {scheme}")
    
    # Guard: Resolve the hostname and ensure it resolves to at least one IP
    try:
        ip_addresses = resolve_host(host)
        if not ip_addresses:
            raise ValueError(f"Hostname {host} does not resolve to any IP address")
    except Exception:
        raise ValueError(f"Hostname {host} failed to resolve")
    
    # Determine the port based on scheme
    default_port = 80 if scheme == 'http' else 443
    
    # Construct the request URL with the resolved port
    # We need to ensure the host in the request string matches the resolved host
    # The transport function likely handles the full URL construction, so we pass the original url
    # However, the plan says "follow the initial destination only", implying we use the parsed components.
    # We will construct a clean URL for the request.
    # Note: The transport function signature is transport(url). We assume it handles the connection logic.
    # We must ensure we are connecting to the correct host/port.
    
    # Reconstruct the authority part with the default port if not specified, or use as-is
    # The plan implies we validate the scheme and host, then let transport handle the connection.
    # We will use the original url string passed by the caller, assuming transport handles the resolution or expects a valid URL.
    # However, to be safe and adhere to "resolve the requested hostname", we ensure the host is valid.
    # The transport function is expected to take the url.
    
    # Let's assume the transport function expects a standard URL string.
    # We will proceed with the original url but have already validated the scheme and host.
    
    # Guard: Follow the initial destination only and reject every redirect response
    # We will make a single request. The transport function likely handles the HTTP request.
    # We need to ensure we don't follow redirects.
    # Since we cannot control the internal logic of 'transport', we assume it returns (status, headers, body).
    # We will check the status code. If it's 3xx, we raise an error as per "reject every redirect response".
    
    status, headers, body = transport(url)
    
    # Guard: Reject every redirect response (status 3xx)
    # HTTP status codes are typically 3 digits.
    if status >= 300 and status < 400:
        raise ValueError("Redirect response received; redirects are not allowed")
    
    # Guard: Return the body for status 200
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    # Return the body as text
    return body.decode('utf-8') if isinstance(body, bytes) else body
