import urllib.parse
import urllib.request
import urllib.error
import socket
import ssl

def fetch_text(url: str, transport, resolve_host) -> str:
    # Guard: Check scheme
    parsed_url = urllib.parse.urlparse(url)
    scheme = parsed_url.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Disallowed request: scheme must be http or https")

    # Guard: Resolve host
    hostname = parsed_url.hostname
    if not hostname:
        raise ValueError("Disallowed request: missing hostname")
    
    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise ValueError("Disallowed request: hostname resolution failed")

    # Determine port
    port = parsed_url.port
    if port is None:
        if scheme == 'http':
            port = 80
        elif scheme == 'https':
            port = 443

    # Build the request URL
    request_url = f"{scheme}://{hostname}"
    if port:
        request_url += f":{port}"
    if parsed_url.path:
        request_url += parsed_url.path
    if parsed_url.query:
        request_url += f"?{parsed_url.query}"

    # Create the request
    req = urllib.request.Request(request_url, method='GET')

    # Open the connection
    try:
        response = urllib.request.urlopen(req)
    except urllib.error.HTTPError as e:
        if e.code != 200:
            raise ValueError(f"Disallowed request: HTTP status {e.code}")
        return e.read().decode('utf-8', errors='replace')
    except urllib.error.URLError as e:
        raise ValueError(f"Disallowed request: {e.reason}")

    # Guard: Check status code
    if response.status != 200:
        raise ValueError(f"Disallowed request: HTTP status {response.status}")

    # Return body
    return response.read().decode('utf-8', errors='replace')
