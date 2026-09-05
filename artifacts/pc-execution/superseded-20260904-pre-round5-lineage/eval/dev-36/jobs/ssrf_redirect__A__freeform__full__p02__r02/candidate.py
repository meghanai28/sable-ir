import socket
import urllib.parse
import urllib.request
import urllib.error

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL using the provided transport.
    
    Args:
        url: The URL to fetch from.
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The body of the response as a string for status 200.
    
    Raises:
        ValueError: If the scheme is not HTTP or HTTPS, or if the request is disallowed.
    """
    # Parse the URL
    parsed_url = urllib.parse.urlparse(url)
    
    # Validate scheme
    scheme = parsed_url.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError(f"Only HTTP and HTTPS schemes are allowed, got {scheme}")
    
    # Resolve hostname
    hostname = parsed_url.hostname
    if not hostname:
        raise ValueError("Invalid URL: No hostname found")
    
    try:
        ip_addresses = resolve_host(hostname)
        if not ip_addresses:
            raise ValueError(f"No IP addresses found for {hostname}")
    except Exception as e:
        raise ValueError(f"Failed to resolve hostname {hostname}: {e}")
    
    # Open the connection
    try:
        request = urllib.request.Request(url)
        # Set the host header to the resolved IP to avoid DNS issues
        request.add_header('Host', hostname)
        
        # Create the opener
        opener = urllib.request.build_opener()
        
        # Open the URL
        response = opener.open(url, timeout=10)
        
        # Read the body
        body = response.read().decode('utf-8', errors='replace')
        
        # Check status code
        if response.status != 200:
            raise ValueError(f"Status code {response.status} is not 200")
        
        return body
    
    except urllib.error.HTTPError as e:
        if e.code != 200:
            raise ValueError(f"HTTP error {e.code}: {e.reason}")
        raise ValueError(f"Unexpected error: {e}")
    except Exception as e:
        raise ValueError(f"Error: {e}")
