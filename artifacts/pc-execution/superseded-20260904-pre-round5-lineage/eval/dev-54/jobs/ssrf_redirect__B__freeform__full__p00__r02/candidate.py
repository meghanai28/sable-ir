import socket
import urllib.parse
import urllib.request
import urllib.error

def fetch_text(url: str, transport, resolve_host) -> str:
    # Parse the initial URL to extract scheme, netloc, and path
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme
    netloc = parsed.netloc
    path = parsed.path
    
    # Validate scheme
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    # Determine the port based on scheme and default to None if not specified
    port = None
    if scheme == 'http':
        port = 80
    elif scheme == 'https':
        port = 443
    
    # Resolve the initial hostname
    initial_host = resolve_host(netloc)
    if not initial_host:
        raise ValueError("Failed to resolve hostname.")
    
    # Function to construct a new URL from the current URL and a Location header
    def construct_redirect_url(current_url: str, location_header: str) -> str:
        # Parse the current URL to get scheme, netloc, path, query, fragment
        current_parsed = urllib.parse.urlparse(current_url)
        
        # Parse the Location header
        location_parsed = urllib.parse.urlparse(location_header)
        
        # If the Location header is absolute, use it as is
        if location_parsed.scheme:
            return location_header
        
        # If relative, construct the new URL
        # Keep the same scheme, netloc, and credentials
        new_parsed = current_parsed._replace(
            scheme=current_parsed.scheme,
            netloc=current_parsed.netloc,
            path=location_parsed.path,
            query=location_parsed.query,
            fragment=location_parsed.fragment
        )
        return new_parsed.geturl()
    
    # Track redirect hops
    redirect_count = 0
    current_url = url
    
    # Loop to handle redirects
    while True:
        # Use the transport function to get the response
        status, headers, body = transport(current_url)
        
        # Check for redirect
        if 'location' in headers:
            location_value = headers['location'].strip()
            new_url = construct_redirect_url(current_url, location_value)
            
            # Check redirect limit
            redirect_count += 1
            if redirect_count > 5:
                raise ValueError("Too many redirects.")
            
            current_url = new_url
            continue
        
        # Check status code
        if status != 200:
            raise ValueError("Non-200 status code received.")
        
        # Return the body
        return body.decode('utf-8') if isinstance(body, bytes) else body
