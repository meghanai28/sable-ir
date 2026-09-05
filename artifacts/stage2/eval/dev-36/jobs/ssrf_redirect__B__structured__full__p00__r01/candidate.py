import socket
import urllib.parse
import urllib.request

def fetch_text(url: str, transport: callable, resolve_host: callable) -> str:
    """
    Fetch text from a URL using the provided transport and host resolution functions.
    
    Args:
        url: The URL to fetch.
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string if status is 200.
    
    Raises:
        ValueError: If the scheme is not http/https or if no IP addresses are resolved.
    """
    # Parse the URL to extract scheme and host
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    host = parsed.hostname
    
    # GUARD: Check scheme
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    # GUARD: Resolve host
    ip_addresses = resolve_host(host)
    if not ip_addresses:
        raise ValueError("No IP addresses resolved for the hostname.")
    
    # Determine the port based on scheme
    port = 80 if scheme == 'http' else 443
    
    # Create a request object and get the response
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req) as response:
            status = int(response.status)
            if status != 200:
                raise ValueError(f"Unexpected status code: {status}")
            body = response.read().decode('utf-8')
            return body
    except urllib.error.HTTPError as e:
        raise ValueError(f"HTTP error occurred: {e.code}")
    except Exception as e:
        raise ValueError(f"Connection failed: {str(e)}")
