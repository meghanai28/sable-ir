import urllib.parse
import urllib.request
import socket
import os

def fetch_text(url: str, transport, resolve_host) -> str:
    # Resolve hostname to IP address
    try:
        hostname = urllib.parse.urlparse(url).hostname
        if hostname is None:
            raise ValueError("Invalid URL format")
        ip_addresses = resolve_host(hostname)
        if not ip_addresses:
            raise ValueError("Hostname resolution failed")
    except Exception:
        raise ValueError("Invalid request")

    # Parse URL and check port
    parsed_url = urllib.parse.urlparse(url)
    scheme = parsed_url.scheme.lower()
    port = parsed_url.port

    # Validate scheme and port
    valid_schemes = ['http', 'https']
    if scheme not in valid_schemes:
        raise ValueError("Only HTTP and HTTPS are allowed")

    if scheme == 'http':
        default_port = 80
    elif scheme == 'https':
        default_port = 443
    else:
        raise ValueError("Invalid scheme")

    if port is None:
        port = default_port
    elif port != default_port:
        raise ValueError("Only default ports are allowed")

    # Construct the request URL
    request_url = parsed_url._replace(port=port).geturl()

    # Fetch the response using the provided transport
    try:
        response = transport(request_url)
        status_code = response[0]

        if status_code != 200:
            raise ValueError("Only status 200 is allowed")

        headers = response[1]
        body = response[2]

        # Decode the body if necessary
        if isinstance(body, bytes):
            body = body.decode('utf-8')

        return body
    except Exception:
        raise ValueError("Invalid request")
