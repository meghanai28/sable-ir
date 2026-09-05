import socket
import urllib.parse
from typing import Tuple, Any, List

def fetch_text(url: str, transport: Any, resolve_host: Any) -> str:
    """
    Fetch text from a URL using the provided transport and host resolver.
    
    Args:
        url: The URL to fetch.
        transport: A callable that takes a URL and returns (status, headers, body).
        resolve_host: A callable that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string for status code 200.
    
    Raises:
        ValueError: If the scheme is not http/https, no IP is found, or redirect rules are violated.
    """
    # Parse the initial URL
    parsed_url = urllib.parse.urlparse(url)
    
    # GUARD: Check scheme
    if parsed_url.scheme.lower() not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    # GUARD: Resolve initial hostname
    initial_host = parsed_url.hostname
    if not initial_host:
        raise ValueError("Invalid URL: missing hostname.")
    
    ip_addresses = resolve_host(initial_host)
    if not ip_addresses:
        raise ValueError(f"No IP address found for {initial_host}.")
    
    current_url = url
    current_scheme = parsed_url.scheme
    current_port = parsed_url.port or (443 if current_scheme == 'https' else 80)
    current_netloc = parsed_url.netloc
    
    # Follow redirects (at most 5)
    redirect_count = 0
    max_redirects = 5
    
    while redirect_count < max_redirects:
        # Use the first available IP to make the request
        ip = ip_addresses[0]
        # Construct the request URL with IP to avoid DNS issues in some transport implementations
        # We need to handle port and netloc carefully
        if current_port == 80 and current_scheme == 'http':
            request_url = f"http://{ip}" + current_url[len("http://"):]
        elif current_port == 443 and current_scheme == 'https':
            request_url = f"https://{ip}" + current_url[len("https://"):]
        else:
            # Custom port
            if current_scheme == 'http':
                request_url = f"http://{ip}:{current_port}" + current_url[len("http://"):]
            else:
                request_url = f"https://{ip}:{current_port}" + current_url[len("https://"):]
        
        # Call transport
        status, headers, body = transport(request_url)
        
        if status != 200:
            # If not 200, check for redirect
            if 'location' in headers.lower():
                location_value = headers['location'].strip()
                
                # Parse the redirect URL
                redirect_parsed = urllib.parse.urlparse(location_value)
                
                # GUARD: Check redirect rules
                # 1. Same scheme but different port
                if redirect_parsed.scheme.lower() == current_scheme:
                    redirect_port = redirect_parsed.port or (443 if redirect_parsed.scheme == 'https' else 80)
                    if redirect_port != current_port:
                        raise ValueError("Redirect to different port not allowed.")
                
                # 2. Missing credentials (scheme://host)
                # If the redirect URL has a scheme but no netloc, or netloc is empty
                if not redirect_parsed.netloc:
                    raise ValueError("Redirect URL missing credentials (host).")
                
                # 3. Non-public DNS entry (handled by resolve_host returning empty list, 
                # but we check here if the resolved host of the redirect is not in our IP list? 
                # The plan says "points to a non-public DNS entry". Since we use resolve_host 
                # on the initial URL, we assume resolve_host handles the check. 
                # However, if the redirect host is different, we must resolve it.
                # The plan implies we resolve the redirect host. If resolve_host returns empty, raise.
                
                # Resolve the redirect hostname
                redirect_host = redirect_parsed.hostname
                if not redirect_host:
                    raise ValueError("Invalid redirect URL: missing hostname.")
                
                redirect_ips = resolve_host(redirect_host)
                if not redirect_ips:
                    raise ValueError(f"Non-public DNS entry for redirect host {redirect_host}.")
                
                # Update current URL and state for next iteration
                current_url = location_value
                current_scheme = redirect_parsed.scheme
                current_port = redirect_parsed.port or (443 if redirect_parsed.scheme == 'https' else 80)
                current_netloc = redirect_parsed.netloc
                
                # Re-resolve the host for the next iteration (though we already have IPs)
                # We need to resolve the new host again to get the IPs for the next request
                ip_addresses = redirect_ips
                redirect_count += 1
                continue
            else:
                raise ValueError(f"Unexpected status code: {status}")
        else:
            # Status 200, return body
            return body
    else:
        raise ValueError("Too many redirects.")
