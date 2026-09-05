import socket
import urllib.parse
import urllib.request
import urllib.error

def fetch_text(url: str, transport, resolve_host) -> str:
    # Validate scheme and port
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    port = parsed.port

    if scheme not in ('http', 'https'):
        raise ValueError("Disallowed request")

    if scheme == 'http':
        default_port = 80
    elif scheme == 'https':
        default_port = 443
    else:
        raise ValueError("Disallowed request")

    if port is None:
        port = default_port
    elif port != default_port:
        raise ValueError("Disallowed request")

    # Resolve hostname
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("Disallowed request")
    
    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise ValueError("No IP address found for hostname")

    # Prepare initial request
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'Python-urllib')

    # Redirect handling
    max_redirects = 5
    current_url = url
    final_body = None
    redirect_count = 0

    while redirect_count < max_redirects:
        try:
            response = transport(current_url)
            status, headers, body = response
        except Exception as e:
            raise ValueError(f"Request failed: {e}")

        if status != 200:
            raise ValueError(f"Non-200 status code: {status}")

        final_body = body

        # Check for redirect
        location = headers.get('Location')
        if location:
            redirect_count += 1
            # Resolve relative URL
            try:
                current_url = urllib.parse.urljoin(url, location)
            except ValueError as e:
                raise ValueError(f"Invalid redirect URL: {e}")

            # Validate redirect URL
            redirect_parsed = urllib.parse.urlparse(current_url)
            redirect_scheme = redirect_parsed.scheme.lower()
            redirect_port = redirect_parsed.port

            # Check scheme
            if redirect_scheme not in ('http', 'https'):
                raise ValueError("Redirect to disallowed scheme")

            # Check port
            if redirect_scheme == 'http':
                default_port = 80
            elif redirect_scheme == 'https':
                default_port = 443
            else:
                raise ValueError("Redirect to disallowed scheme")

            if redirect_port is None:
                redirect_port = default_port
            elif redirect_port != default_port:
                raise ValueError("Redirect to non-default port")

            # Check for javascript: or data:
            if redirect_scheme in ('javascript', 'data'):
                raise ValueError("Redirect to disallowed scheme (javascript/data)")

            # Check same scheme and port
            if redirect_scheme != scheme or redirect_port != port:
                raise ValueError("Redirect to different scheme or port")

        else:
            break

    if final_body is None:
        raise ValueError("No body received")

    # Ensure body is text (decode if bytes)
    if isinstance(final_body, bytes):
        final_body = final_body.decode('utf-8', errors='replace')

    return final_body
