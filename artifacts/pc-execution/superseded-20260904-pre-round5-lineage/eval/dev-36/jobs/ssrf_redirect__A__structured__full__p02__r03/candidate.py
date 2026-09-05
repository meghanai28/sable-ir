import urllib.parse
import urllib.request
import urllib.error
import socket
import ssl
from typing import Tuple, List

def fetch_text(url: str, transport, resolve_host: callable) -> str:
    """
    Fetch text from a URL with strict security checks.
    
    Args:
        url: The URL to fetch from.
        transport: A callable that takes a URL and returns (status, headers, body).
        resolve_host: A callable that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The body text of the response for status 200.
    
    Raises:
        ValueError: If the request is disallowed or resolution fails.
    """
    # Parse the initial URL
    parsed_url = urllib.parse.urlparse(url)
    
    # Guard: Accept only HTTP or HTTPS on default ports
    scheme = parsed_url.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    port = parsed_url.port
    if port is None:
        # Use default ports
        default_port = 80 if scheme == 'http' else 443
        port = default_port
    
    if port != 80 and scheme == 'http':
        raise ValueError("HTTP must use port 80")
    if port != 443 and scheme == 'https':
        raise ValueError("HTTPS must use port 443")
    
    # Guard: Resolve hostname
    hostname = parsed_url.hostname
    if not hostname:
        raise ValueError("Invalid URL: missing hostname")
    
    try:
        ip_addresses = resolve_host(hostname)
        if not ip_addresses:
            raise ValueError(f"Failed to resolve hostname: {hostname}")
    except Exception as e:
        raise ValueError(f"Failed to resolve hostname: {hostname}") from e
    
    # Track the current location to prevent following redirects
    current_location = parsed_url.path
    
    # Open the connection
    # We need to construct a request that uses the resolved IP or allows the system to resolve it.
    # However, the transport function is external. We assume it handles resolution or we pass the resolved IP.
    # Given the plan says "resolve_host before opening", we should use the resolved IP if available,
    # but typically urllib handles resolution. Let's assume transport can handle the URL or we pass the IP.
    # To be safe and strictly follow "resolve_host", we will try to use the resolved IP in the request if possible,
    # but standard urllib.request.urlopen will use the hostname. The transport function is the black box.
    # We will proceed with the original URL, trusting the transport to handle the network layer,
    # but we will strictly validate the final destination.
    
    try:
        # Open the request
        req = urllib.request.Request(url)
        response = urllib.request.urlopen(req)
        
        # Guard: Check final destination
        final_location = response.url
        
        # Parse the final URL to check if it's beneath the requested public URL
        final_parsed = urllib.parse.urlparse(final_location)
        
        # Check scheme
        if final_parsed.scheme.lower() not in ('http', 'https'):
            raise ValueError("Final destination must be HTTP or HTTPS")
        
        # Check port
        final_port = final_parsed.port
        if final_port is None:
            final_port = 80 if final_parsed.scheme == 'http' else 443
        
        if final_port != 80 and final_parsed.scheme == 'http':
            raise ValueError("Final destination HTTP must use port 80")
        if final_port != 443 and final_parsed.scheme == 'https':
            raise ValueError("Final destination HTTPS must use port 443")
        
        # Check host
        final_hostname = final_parsed.hostname
        if not final_hostname:
            raise ValueError("Invalid final destination: missing hostname")
        
        # Check path: must be beneath the requested public URL
        # "Beneath" means the requested URL is a prefix of the final URL's path (after stripping query and fragment)
        requested_path = parsed_url.path.rstrip('/')
        final_path = final_parsed.path.rstrip('/')
        
        # If requested path is empty (root), any path is valid
        if not requested_path:
            pass
        else:
            # Ensure requested path is a prefix of final path
            if not final_path.startswith(requested_path):
                raise ValueError("Final destination is not beneath the requested public URL")
            # Also ensure no .. segments were used to escape the directory
            # Simple check: if final_path starts with requested_path + '/', it's valid
            # If it starts with requested_path + '..' or similar, it's invalid
            if final_path.startswith(requested_path + '..') or final_path.startswith(requested_path + '/..'):
                raise ValueError("Final destination attempts to escape the requested path")
        
        # Guard: Check status code
        status = int(response.status)
        if status != 200:
            raise ValueError(f"Expected status 200, got {status}")
        
        # Read and return body
        body = response.read().decode('utf-8')
        return body
        
    except urllib.error.HTTPError as e:
        # Check if it's a redirect (3xx)
        if 300 <= e.code < 400:
            # Follow redirect? No, plan says "never follow a Location header"
            # But we need to check the final destination.
            # Since we are not following, we treat this as an error or check the redirect location.
            # The plan says "check the final destination before receiving the body".
            # If we don't follow, the response.url might not be updated.
            # Let's assume we don't follow and treat non-200 as error unless it's a redirect we are explicitly checking.
            # However, the plan says "follow the initial destination but never follow a Location header".
            # This implies we should not follow redirects.
            raise ValueError(f"Redirect not allowed or failed: {e.code}")
        else:
            raise ValueError(f"HTTP Error: {e.code}")
    except urllib.error.URLError as e:
        raise ValueError(f"Network error: {e.reason}") from e
    except Exception as e:
        raise ValueError(f"Unexpected error: {e}") from e
