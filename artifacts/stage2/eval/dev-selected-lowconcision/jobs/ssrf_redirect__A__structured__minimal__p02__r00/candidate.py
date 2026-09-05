import urllib.parse
import urllib.request
import urllib.error

def fetch_text(url, transport, resolve_host):
    # Parse the initial URL to get the scheme and netloc
    parsed_url = urllib.parse.urlparse(url)
    scheme = parsed_url.scheme.lower()
    netloc = parsed_url.netloc
    
    # Determine the default port based on scheme
    default_port = None
    if scheme == 'http':
        default_port = 80
    elif scheme == 'https':
        default_port = 443
    else:
        raise ValueError("Only HTTP and HTTPS are allowed")
    
    # Resolve the hostname to IP
    resolved_ips = resolve_host(netloc)
    if not resolved_ips:
        raise ValueError("resolve_host returned no IP address")
    
    # Select the first valid IP address (simplified to single IP for this implementation)
    resolved_host = resolved_ips[0]
    
    # Construct the base URL with the resolved host to check against the root
    # The plan implies a "configured root" but doesn't provide one; we assume the root is the scheme + resolved host + path
    # However, the guard says "check the resolved host beneath the configured root". 
    # Without a specific root configuration in the plan, we interpret "beneath the root" as ensuring the netloc matches the resolved host exactly (no path traversal in netloc) or if a root were passed, it would be checked here.
    # Since no root is passed, we validate that the resolved host is the one we are connecting to.
    # The plan says "raise ValueError if it escapes the root". If no root is configured, we assume the current netloc is the root.
    # We must ensure the URL's netloc matches the resolved host exactly to prevent DNS rebinding or path tricks in the netloc itself.
    if parsed_url.netloc != resolved_host:
        # This handles cases where the URL has a different netloc than the resolved IP, which could be an escape attempt
        raise ValueError("Resolved host does not match URL netloc")
    
    # Prepare the request
    req = urllib.request.Request(url)
    
    # Follow redirects only if status is exactly 200
    while True:
        try:
            response = transport(url)
        except Exception as e:
            raise ValueError(f"Request failed: {e}")
        
        status, headers, body = response
        
        if status != 200:
            raise ValueError(f"Unexpected status code: {status}")
        
        # Check for Location header
        location = headers.get('Location')
        if location:
            # Parse the new URL
            new_parsed = urllib.parse.urlparse(location)
            new_scheme = new_parsed.scheme.lower()
            new_netloc = new_parsed.netloc
            
            # Determine new default port
            new_default_port = None
            if new_scheme == 'http':
                new_default_port = 80
            elif new_scheme == 'https':
                new_default_port = 443
            
            # Resolve the new hostname
            new_resolved_ips = resolve_host(new_netloc)
            if not new_resolved_ips:
                raise ValueError("resolve_host returned no IP address for redirect")
            
            new_resolved_host = new_resolved_ips[0]
            
            # Check if the new destination remains beneath the root
            # Root is effectively the scheme + resolved_host + path. 
            # We check if the new netloc matches the resolved host exactly.
            if new_netloc != new_resolved_host:
                raise ValueError("Redirect destination escapes the root")
            
            # Update the URL for the next iteration
            url = new_location
            
        else:
            break
    
    # Return the body
    if body is None:
        raise ValueError("Response body is None")
    
    return body
