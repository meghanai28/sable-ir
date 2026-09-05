import socket
import urllib.parse
from urllib.request import urlopen, Request
from urllib.error import URLError

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL following the specified plan.
    
    Args:
        url: The URL to fetch.
        transport: A function that returns (status, headers, body) for a given URL.
        resolve_host: A function that returns textual IP addresses for a hostname.
    
    Returns:
        The response body as a string if status is 200.
    
    Raises:
        ValueError: For disallowed requests or non-200 status.
    """
    parsed_url = urllib.parse.urlparse(url)
    
    # Guard: Accept only HTTP or HTTPS on default ports
    scheme = parsed_url.scheme.lower()
    port = parsed_url.port
    
    if scheme not in ['http', 'https']:
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    if scheme == 'http':
        default_port = 80
    else:
        default_port = 443
    
    if port != default_port:
        raise ValueError("Only default ports are allowed")
    
    # Guard: Resolve the initial hostname
    hostname = parsed_url.hostname
    if not hostname:
        raise ValueError("Invalid URL: missing hostname")
    
    try:
        ip_addresses = resolve_host(hostname)
    except Exception as e:
        raise ValueError(f"Failed to resolve hostname {hostname}: {e}")
    
    # Parse the current URL for redirect logic
    current_url = url
    
    # Follow redirects (at most 5)
    max_redirects = 5
    redirect_count = 0
    
    while redirect_count < max_redirects:
        # Prepare the request
        req = Request(current_url)
        
        # Get response using transport
        try:
            response = transport(current_url)
        except Exception as e:
            raise ValueError(f"Transport error: {e}")
        
        status, headers, body = response
        
        # Guard: Check status code
        if status != 200:
            raise ValueError(f"Status code {status} is not 200")
        
        # Check for redirects
        location = headers.get('Location')
        if location:
            redirect_count += 1
            if redirect_count > max_redirects:
                raise ValueError("Too many redirects")
            
            # Parse the redirect location
            redirect_parsed = urllib.parse.urlparse(location)
            
            # Guard: Resolve the redirect location hostname
            redirect_hostname = redirect_parsed.hostname
            if not redirect_hostname:
                raise ValueError("Invalid redirect URL: missing hostname")
            
            try:
                redirect_ips = resolve_host(redirect_hostname)
            except Exception as e:
                raise ValueError(f"Failed to resolve redirect hostname {redirect_hostname}: {e}")
            
            # Guard: Check scheme, port, credentials, and public address
            if redirect_parsed.scheme != parsed_url.scheme:
                raise ValueError("Redirect scheme mismatch")
            
            if port != redirect_parsed.port:
                raise ValueError("Redirect port mismatch")
            
            # Check credentials (user info)
            if parsed_url.username or parsed_url.password:
                if not (redirect_parsed.username and redirect_parsed.password):
                    raise ValueError("Redirect loses credentials")
            
            # Check public address (IP)
            if ip_addresses:
                if not redirect_ips:
                    raise ValueError("Redirect loses IP address")
            
            # Resolve the redirect URL against the current URL
            # urllib.parse.urljoin handles the base URL resolution
            new_location = urllib.parse.urljoin(current_url, location)
            current_url = new_location
            
            # Re-parse to get the new scheme and port for the next iteration
            parsed_url = urllib.parse.urlparse(current_url)
        else:
            # No redirect, proceed to read body
            break
    
    # Guard: Check the final destination before reading the body
    final_scheme = parsed_url.scheme.lower()
    final_port = parsed_url.port
    
    if final_scheme != scheme or final_port != port:
        raise ValueError("Final destination scheme or port mismatch")
    
    # Read the response body
    if isinstance(body, bytes):
        return body.decode('utf-8')
    else:
        return str(body)
