import socket
import urllib.parse
import urllib.request
import urllib.error

def fetch_text(url: str, transport, resolve_host) -> str:
    # Parse the input URL to check scheme and components
    parsed = urllib.parse.urlparse(url)
    
    # Validate scheme: must be exactly http:// or https://
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Disallowed request: invalid scheme")
    
    # Check if the URL is absolute
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("Disallowed request: must be absolute URL")
    
    # Extract the host from the original URL
    original_host = parsed.netloc.split(':')[0]
    
    # Resolve the original hostname
    resolved_original = resolve_host(original_host)
    if not resolved_original:
        raise ValueError("Disallowed request: no IP address found for original host")
    
    # Call transport to get the response
    try:
        response = transport(url)
    except Exception as e:
        raise ValueError(f"Transport error: {str(e)}")
    
    status, headers, body = response
    
    # Check status code: must be exactly 200
    if status != 200:
        raise ValueError("Disallowed request: status code is not 200")
    
    # Parse the final destination (URL passed to transport)
    final_parsed = urllib.parse.urlparse(url)
    
    # Check if the final destination is absolute and begins with http:// or https://
    if not final_parsed.scheme or final_parsed.scheme not in ('http', 'https'):
        raise ValueError("Disallowed request: final destination must be absolute http/https URL")
    
    # Resolve the final destination's hostname
    final_host = final_parsed.netloc.split(':')[0]
    resolved_final = resolve_host(final_host)
    if not resolved_final:
        raise ValueError("Disallowed request: no IP address found for final destination")
    
    # Return the body
    return body
