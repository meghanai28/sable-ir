import socket
import urllib.parse
import urllib.request
import urllib.error
import ssl

def fetch_text(url: str, transport, resolve_host) -> str:
    # Parse the URL to extract scheme, host, port, and path
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    port = parsed.port
    hostname = parsed.hostname
    path = parsed.path

    # Validate scheme
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")

    # Validate port
    if port is None:
        port = 80 if scheme == 'http' else 443
    elif port != 80 and port != 443:
        raise ValueError("Only default ports (80 for HTTP, 443 for HTTPS) are allowed.")

    # Resolve hostname to IP address(es)
    if hostname is None:
        raise ValueError("Invalid URL: missing hostname.")

    try:
        ip_addresses = resolve_host(hostname)
    except Exception as e:
        raise ValueError(f"Failed to resolve hostname {hostname}: {e}") from e

    if not ip_addresses:
        raise ValueError(f"No IP addresses found for hostname {hostname}.")

    # Select the first IP address to use
    ip_address = ip_addresses[0]

    # Construct the full URL with the resolved IP and validated port
    # If the original URL had a path, we use it; otherwise, we use the default root path
    if path:
        full_url = f"{scheme}://{ip_address}:{port}{path}"
    else:
        full_url = f"{scheme}://{ip_address}:{port}/"

    # Create an HTTP request
    req = urllib.request.Request(full_url)

    try:
        response = urllib.request.urlopen(req)
    except urllib.error.HTTPError as e:
        raise ValueError(f"HTTP request failed with status {e.code}: {e.reason}") from e
    except urllib.error.URLError as e:
        raise ValueError(f"URL request failed: {e.reason}") from e

    # Check status code
    status = response.status
    if status != 200:
        raise ValueError(f"Expected status 200, got {status}.")

    # Read and return the body
    body = response.read().decode('utf-8')
    return body
