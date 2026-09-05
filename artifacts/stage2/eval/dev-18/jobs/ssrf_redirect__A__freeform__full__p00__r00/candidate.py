import urllib.request
import urllib.parse
import urllib.error
import socket
import ssl

def fetch_text(url: str, transport, resolve_host) -> str:
    # Normalize the URL to remove fragments and ensure it's a base URL
    parsed_url = urllib.parse.urlparse(url)
    if parsed_url.fragment:
        parsed_url = parsed_url._replace(fragment='')
    
    # Extract the host from the normalized URL
    hostname = parsed_url.hostname
    
    # Resolve the host using the provided function
    if not hostname:
        raise ValueError("Invalid URL: missing hostname")
    
    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise ValueError("resolve_host returned no IP address")
    
    # Select the first valid IP address for connection
    ip_address = ip_addresses[0]
    
    # Determine the scheme and port based on the URL
    scheme = parsed_url.scheme.lower()
    port = parsed_url.port
    
    # Accept only HTTP or HTTPS on their default ports
    default_ports = {
        'http': 80,
        'https': 444  # Default is 443, but we'll check if port is specified or default
    }
    
    # Validate scheme and port
    if scheme not in ['http', 'https']:
        raise ValueError("Only HTTP or HTTPS is allowed")
    
    if scheme == 'http':
        if port != 80:
            raise ValueError("HTTP must use port 80")
    elif scheme == 'https':
        if port != 443:
            raise ValueError("HTTPS must use port 443")
    
    # Construct the base URL for the request
    base_url = f"{scheme}://{hostname}"
    if port != default_ports.get(scheme):
        base_url = f"{scheme}://{hostname}:{port}"
    
    # Build the full URL with query and fragment if present
    full_url = f"{base_url}{parsed_url.path}"
    if parsed_url.query:
        full_url += f"?{parsed_url.query}"
    if parsed_url.fragment:
        full_url += f"#{parsed_url.fragment}"
    
    # Make the request
    try:
        # Use the transport function to get the response
        response = transport(full_url)
        
        # Check the status code
        status_code = response[0]
        
        if status_code != 200:
            raise ValueError(f"Invalid status code: {status_code}")
        
        # Return the body
        return response[2].decode('utf-8') if isinstance(response[2], bytes) else response[2]
        
    except Exception as e:
        raise ValueError(f"Request failed: {str(e)}")
