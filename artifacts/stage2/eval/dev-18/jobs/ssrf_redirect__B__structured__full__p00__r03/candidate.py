import socket
import urllib.parse
import urllib.request
import urllib.error

def fetch_text(url: str, transport, resolve_host) -> str:
    # Validate scheme and port
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    port = parsed.port

    # Check scheme
    if scheme not in ('http', 'https'):
        raise ValueError("Disallowed scheme")

    # Check port
    if scheme == 'http' and port != 80:
        raise ValueError("Disallowed port")
    if scheme == 'https' and port != 443:
        raise ValueError("Disallowed port")

    # Resolve hostname and check resolution
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL")
    
    try:
        ip_addresses = resolve_host(hostname)
    except Exception:
        raise ValueError("Hostname does not resolve")
    
    if not ip_addresses:
        raise ValueError("Hostname does not resolve to any IP")

    # Prepare initial request
    req = urllib.request.Request(url)
    req.get_method = lambda: 'GET'

    # Follow redirects with hop counting
    current_url = url
    hops = 0
    max_hops = 5

    while True:
        # Transport the current URL
        try:
            response = transport(current_url)
        except Exception as e:
            raise ValueError(f"Request failed: {e}")

        status, headers, body = response

        # Check status code
        if status != 200:
            raise ValueError("Unexpected status code")

        # Check for redirect
        location = headers.get('Location')
        if location:
            hops += 1
            if hops > max_hops:
                raise ValueError("Redirect limit exceeded")

            # Parse redirect location
            redirect_parsed = urllib.parse.urlparse(location)
            
            # Validate redirect scheme and port
            if redirect_parsed.scheme.lower() != scheme:
                raise ValueError("Redirect scheme mismatch")
            
            redirect_port = redirect_parsed.port
            if scheme == 'http' and redirect_port != 80:
                raise ValueError("Redirect port mismatch")
            if scheme == 'https' and redirect_port != 443:
                raise ValueError("Redirect port mismatch")

            # Check for javascript: or data:
            if redirect_parsed.scheme.lower() in ('javascript:', 'data:'):
                raise ValueError("Disallowed redirect scheme")

            # Resolve new hostname
            new_hostname = redirect_parsed.hostname
            if not new_hostname:
                raise ValueError("Invalid redirect URL")
            
            try:
                new_ips = resolve_host(new_hostname)
            except Exception:
                raise ValueError("Redirect hostname does not resolve")
            
            if not new_ips:
                raise ValueError("Redirect hostname does not resolve to any IP")

            # Update current URL
            current_url = redirect_parsed.geturl()
            continue

        return body.decode('utf-8') if isinstance(body, bytes) else str(body)

    raise ValueError("Unexpected end of redirect chain")
