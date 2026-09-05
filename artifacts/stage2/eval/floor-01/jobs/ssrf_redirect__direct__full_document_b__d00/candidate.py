import socket
import urllib.parse
import urllib.request
import urllib.error
import re

def _validate_url_scheme(url: str) -> None:
    """Validate that the URL scheme is HTTP or HTTPS."""
    scheme_match = re.match(r'^https?://', url)
    if not scheme_match:
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")

def _resolve_destination(url: str, resolve_host: callable) -> str:
    """Resolve the hostname to an IP address and construct the full URL."""
    parsed = urllib.parse.urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL: missing hostname.")
    
    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise ValueError(f"No IP addresses found for {hostname}.")
    
    # Select the first IP address (policy 1: resolve beneath root implies we are working with a valid path)
    ip = ip_addresses[0]
    port = parsed.port or (443 if parsed.scheme == 'https' else 80)
    
    return f"{parsed.scheme}://{ip}:{port}{parsed.path}"

def _fetch_with_transport(url: str, transport: callable) -> str:
    """Fetch the text content using the provided transport function."""
    try:
        # Use urllib.request for transport as it handles the standard HTTP/HTTPS protocol
        # We construct the request using the resolved URL
        resolved_url = _resolve_destination(url, resolve_host)
        
        # Ensure the URL is properly encoded
        resolved_url = urllib.parse.quote(resolved_url, safe='/?#')
        
        # Create the request
        req = urllib.request.Request(resolved_url)
        
        # Perform the request
        with urllib.request.urlopen(req) as response:
            status = response.status
            headers = dict(response.headers)
            body = response.read().decode('utf-8')
            
            # Check status code (Policy 1: reject disallowed, Policy 4: validate before extracting)
            if status != 200:
                raise ValueError(f"HTTP request failed with status code {status}")
            
            return body
            
    except urllib.error.HTTPError as e:
        raise ValueError(f"HTTP error occurred: {e.code} {e.reason}")
    except urllib.error.URLError as e:
        raise ValueError(f"URL error occurred: {e.reason}")
    except Exception as e:
        raise ValueError(f"Unexpected error: {str(e)}")

def fetch_text(url: str, transport: callable, resolve_host: callable) -> str:
    """
    Fetch text content from a URL.
    
    Args:
        url: The target URL string.
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The body of the response as a string if status is 200.
    
    Raises:
        ValueError: If the request is disallowed (e.g., wrong scheme, non-200 status).
    """
    # Apply Policy 1: Validate scheme before proceeding
    _validate_url_scheme(url)
    
    # Apply Policy 3: Use the transport to get the response
    # Note: In a real implementation, 'transport' might be a custom socket wrapper.
    # Here we assume 'transport' is the standard urllib.request.urlopen for the sake of the example,
    # but the structure allows for a custom implementation that follows Policy 3 (disable shell, etc. if OS utils were used).
    # Since the prompt defines transport(url) -> (status, headers, body), we call it directly.
    # However, to strictly adhere to the request definition where transport is an argument,
    # we must use the provided transport. If the transport is not urllib, it must be implemented
    # to behave like a standard HTTP client. For this generic implementation, we assume the caller
    # provides a valid transport that handles the network I/O.
    # To make this runnable as a module, we will implement a basic HTTP client logic inside or assume
    # the provided transport is the one doing the work. Given the constraints, we will use urllib
    # as the default implementation of 'transport' for demonstration, but the signature matches.
    
    # Re-reading the request: "transport(url) returns a (status, headers, body) tuple"
    # This implies the caller provides the transport. We will use urllib.request as the default
    # implementation for the example to ensure it works, but the function signature is generic.
    # To satisfy the request strictly, we will use the provided transport.
    # If no custom transport is passed, we default to urllib.request for the example.
    
    # Since we cannot know the internal implementation of 'transport', we assume it handles the network.
    # We proceed with the logic that the transport returns (status, headers, body).
    
    status, headers, body = transport(url)
    
    # Apply Policy 1: Validate scheme (already done in _validate_url_scheme)
    # Apply Policy 4: Validate archive members? N/A for HTTP text fetch, but ensure destination (if any) is safe.
    # Here, we just return the body.
    
    # Apply Policy 6: Logging (not applicable to this function directly, but relevant to the module context)
    
    if status != 200:
        raise ValueError(f"Disallowed request: HTTP status code {status} is not 200.")
    
    return body
