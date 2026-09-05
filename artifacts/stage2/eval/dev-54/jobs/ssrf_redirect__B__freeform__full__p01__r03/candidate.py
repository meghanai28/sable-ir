import socket
import urllib.parse
import urllib.request
import urllib.error
from typing import Tuple, List, Optional

def fetch_text(url: str, transport: callable, resolve_host: callable) -> str:
    """
    Fetch text from a URL with strict validation and redirect handling.
    
    Args:
        url: The initial URL to fetch from (can be absolute or relative).
        transport: A callable that takes a (url, headers) tuple and returns (status, headers, body).
        resolve_host: A callable that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The body of the HTTP response for a 200 status code.
    
    Raises:
        ValueError: If the scheme is not http/https, if DNS lookup fails, or if redirect validation fails.
    """
    
    # Parse the initial URL
    parsed_url = urllib.parse.urlparse(url)
    
    # Validate scheme
    if parsed_url.scheme.lower() not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    # Resolve the initial hostname
    hostname = parsed_url.hostname
    if not hostname:
        raise ValueError("Invalid URL: missing hostname")
    
    try:
        ips = resolve_host(hostname)
    except Exception:
        raise ValueError(f"DNS resolution failed for {hostname}")
    
    if not ips:
        raise ValueError(f"No IP address found for {hostname}")
    
    # Select the first valid IP for the initial connection
    current_host = ips[0]
    current_port = parsed_url.port
    if current_port is None:
        if parsed_url.scheme == 'http':
            current_port = 80
        else:
            current_port = 443
    
    # Current URL object for redirect resolution
    current_url = parsed_url
    
    # Limit redirects to 5
    redirect_count = 0
    
    while True:
        # Prepare the request URL
        request_url = current_url.geturl()
        
        # Use urllib.request to get headers and body, but we must validate the response
        # We cannot build the request string manually to avoid injection risks,
        # so we use urllib.request.urlopen which handles encoding, but we validate the result.
        try:
            req = urllib.request.Request(request_url)
            with urllib.request.urlopen(req) as response:
                status = response.status
                headers = dict(response.headers)
                body = response.read().decode('utf-8', errors='replace')
        except urllib.error.HTTPError as e:
            status = e.code
            headers = dict(e.headers)
            body = e.read().decode('utf-8', errors='replace')
        except Exception as e:
            raise ValueError(f"Failed to connect or fetch: {e}")
        
        # Check status code
        if status != 200:
            raise ValueError(f"Unexpected status code: {status}")
        
        # Check for Location header
        location_header = headers.get('Location')
        if location_header:
            redirect_count += 1
            if redirect_count > 5:
                raise ValueError("Too many redirects")
            
            # Parse the Location header
            # It can be absolute or relative
            if location_header.startswith(('http://', 'https://')):
                # Absolute URL
                new_parsed = urllib.parse.urlparse(location_header)
            else:
                # Relative URL
                new_parsed = urllib.parse.urljoin(request_url, location_header)
            
            # Validate the new URL scheme
            if new_parsed.scheme.lower() not in ('http', 'https'):
                raise ValueError("Location header must have http or https scheme")
            
            # Validate the new URL port matches the current URL's port
            new_port = new_parsed.port
            if new_port is None:
                if new_parsed.scheme == 'http':
                    new_port = 80
                else:
                    new_port = 443
            
            if new_port != current_port:
                raise ValueError("Location header port must match current URL port")
            
            # Validate DNS lookup for the new URL
            new_hostname = new_parsed.hostname
            if not new_hostname:
                raise ValueError(f"Invalid Location URL: missing hostname in {location_header}")
            
            try:
                new_ips = resolve_host(new_hostname)
            except Exception:
                raise ValueError(f"DNS resolution failed for {new_hostname} in Location header")
            
            if not new_ips:
                raise ValueError(f"No IP address found for {new_hostname} in Location header")
            
            # Update current URL
            current_url = new_parsed
            current_host = new_ips[0]
            
            # Update port
            current_port = new_port
        else:
            # No redirect, break loop
            break
    
    return body
