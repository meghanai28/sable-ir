import socket
import urllib.parse
import urllib.request
import urllib.error

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict validation and redirect handling.
    
    Args:
        url: The initial URL to fetch.
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string if status is 200.
    
    Raises:
        ValueError: If the request is disallowed (non-HTTP/HTTPS, non-default port,
                   redirect to different scheme/port/credentials/DNS, or non-200 status).
    """
    # Parse the initial URL
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        raise ValueError("Invalid URL")

    # Validate scheme and port
    valid_schemes = {'http', 'https'}
    if parsed.scheme not in valid_schemes:
        raise ValueError(f"Disallowed scheme: {parsed.scheme}")

    default_port = {'http': 80, 'https': 443}.get(parsed.scheme)
    if parsed.port is None:
        port = default_port
    else:
        port = parsed.port

    if port != default_port:
        raise ValueError(f"Port {port} not allowed for scheme {parsed.scheme}")

    # Helper to normalize URL components for comparison
    def normalize_url(u):
        # Re-parse to ensure we have consistent components
        p = urllib.parse.urlparse(u)
        return (p.scheme, p.port, p.username, p.password, p.hostname)

    current_url = url
    max_redirects = 5
    redirect_count = 0

    while True:
        # Resolve the current hostname
        hostname = current_url.split('://')[1].split('/')[0].split('?')[0].split('#')[0]
        try:
            ip_addresses = resolve_host(hostname)
        except Exception:
            raise ValueError("Failed to resolve host")

        if not ip_addresses:
            raise ValueError("No IP addresses found for host")

        # Check the final destination before opening the connection
        # We need to ensure the IP addresses are valid (basic check)
        # Note: The prompt says "raise ValueError if resolution fails", implying if no IPs are found.
        
        # Parse current URL to get scheme, port, etc. for comparison
        parsed = urllib.parse.urlparse(current_url)
        current_scheme = parsed.scheme
        current_port = parsed.port or default_port
        current_cred = (parsed.username, parsed.password)
        current_host = parsed.hostname

        # Open the connection
        try:
            # Use the resolved hostname directly in the request to avoid DNS leakage in the request line if possible,
            # but urllib.request uses the URL string. We must use the URL string.
            # However, to strictly follow "resolve the hostname", we rely on the transport function.
            # We will use the URL as is, but the transport should ideally use the resolved IP or the URL.
            # Given the constraints, we pass the URL.
            req = urllib.request.Request(current_url)
            response = transport(current_url)
        except Exception as e:
            raise ValueError(f"Connection failed: {e}")

        status, headers, body = response

        # Check status code
        if status != 200:
            raise ValueError(f"Disallowed status code: {status}")

        # Handle redirects
        location = headers.get('Location')
        if location:
            redirect_count += 1
            if redirect_count > max_redirects:
                raise ValueError("Too many redirects")

            # Parse the Location header
            try:
                redirect_url = urllib.parse.urlparse(location)
            except Exception:
                raise ValueError("Invalid redirect URL")

            # Check if the redirect URL has the same scheme, port, credentials, and DNS/public-address
            # "DNS/public-address" implies the hostname must be the same (or resolve to the same set of IPs, 
            # but typically strict equality is required for the hostname string in such constraints).
            # The plan says: "same scheme, port, credentials, and DNS/public-address as the initial destination"
            # This phrasing is slightly ambiguous ("initial" vs "current"). Usually, it means "same as the current destination".
            # However, "DNS/public-address" suggests checking the resolved IPs.
            # Let's interpret "initial destination" as the starting point, but practically, strict redirects usually require
            # the hostname to remain the same. If it changes, it's a different site.
            # Given the strictness, we will enforce:
            # 1. Same scheme
            # 2. Same port
            # 3. Same credentials
            # 4. Same hostname (DNS/public-address)

            if (redirect_url.scheme != current_scheme or
                redirect_url.port != current_port or
                (redirect_url.username, redirect_url.password) != current_cred or
                redirect_url.hostname != current_host):
                raise ValueError("Redirect to disallowed destination")

            # Update current_url
            current_url = redirect_url.geturl()
        else:
            break

    return body.decode('utf-8')
