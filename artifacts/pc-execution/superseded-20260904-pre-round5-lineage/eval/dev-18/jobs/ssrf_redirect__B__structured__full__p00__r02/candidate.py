import socket
import urllib.parse
import urllib.request
from typing import Tuple, Optional

def fetch_text(url: str, transport: callable, resolve_host: callable) -> str:
    """
    Fetch text from a URL with strict security guards against absolute redirects and DNS rebinding.
    
    Args:
        url: The initial URL to fetch.
        transport: A function(url) -> (status, headers, body) tuple.
        resolve_host: A function(hostname) -> list of textual IP addresses.
    
    Returns:
        The body of the 200 response as a string.
    
    Raises:
        ValueError: If the request is disallowed (absolute URL, non-resolvable host, 
                    redirect to different scheme/port, or redirect to non-matching IP).
    """
    # Parse the initial URL
    parsed_url = urllib.parse.urlparse(url)
    
    # Guard: Reject absolute URLs
    if parsed_url.scheme in ('http', 'https'):
        raise ValueError("Absolute URLs are disallowed")
    
    # Guard: Resolve and check the initial destination
    hostname = parsed_url.hostname
    if not hostname:
        raise ValueError("Invalid URL: missing hostname")
    
    try:
        ips = resolve_host(hostname)
        if not ips:
            raise ValueError("Host does not resolve to a finite IP address")
        
        # Guard: Check if the current host's public address matches the requested hostname's resolution
        # Note: In a real scenario, we would have a list of allowed public IPs for the current host.
        # Here we assume the resolve_host function returns the correct IPs for the hostname we are checking.
        # The critical check is that we don't redirect to an IP that doesn't belong to the current host.
        # Since we start with 'url', we resolve it. If it redirects, we resolve the new host.
        # We must ensure the new host resolves to an IP that matches the DNS entry for the current host's public address.
        # However, without a global registry of "current host's public address", we rely on the fact that
        # the initial URL's host is the one we are allowed to access.
        # The plan says: "raise ValueError if ... resolves to an IP address that does not match the DNS entry for the current host's public address"
        # This implies a context of a known public IP. We will assume the initial URL's resolved IPs are the "current host's public address".
        
        current_host_ips = set(ips)
    except Exception:
        raise ValueError("Invalid URL")
    
    current_scheme = parsed_url.scheme
    current_port = parsed_url.port or (80 if current_scheme == 'http' else 443)
    current_path = parsed_url.path
    
    # Limit redirects to 5 hops
    redirect_count = 0
    max_redirects = 5
    
    while True:
        # Make the transport request
        try:
            # Use urllib.request to handle the transport, but we need to extract status, headers, body manually or via a wrapper
            # Since transport is a black box, we simulate the request logic carefully.
            # However, the plan says transport(url) returns (status, headers, body).
            # We must call transport with the current URL.
            status, headers, body = transport(url)
        except Exception as e:
            raise ValueError(f"Transport error: {e}")
        
        # Guard: Check status
        if status != 200:
            raise ValueError(f"Unexpected status code: {status}")
        
        # Guard: Check for Location header (redirect)
        location_header = headers.get('Location')
        if location_header:
            redirect_count += 1
            if redirect_count > max_redirects:
                raise ValueError("Maximum redirect hops exceeded")
            
            # Parse the redirect URL
            redirect_parsed = urllib.parse.urlparse(location_header)
            
            # Guard: Stop if no scheme
            if not redirect_parsed.scheme:
                raise ValueError("Redirect URL has no scheme")
            
            # Guard: Check for different scheme or port
            if redirect_parsed.scheme != current_scheme:
                raise ValueError("Redirect to different scheme")
            
            redirect_port = redirect_parsed.port
            if redirect_port and redirect_port != current_port:
                raise ValueError("Redirect to different port")
            
            # Guard: Resolve the new hostname
            new_hostname = redirect_parsed.hostname
            if not new_hostname:
                raise ValueError("Redirect URL has no hostname")
            
            try:
                new_ips = resolve_host(new_hostname)
                if not new_ips:
                    raise ValueError("Redirect host does not resolve to a finite IP address")
            except Exception:
                raise ValueError("Invalid redirect URL")
            
            # Guard: Check if the resolved destination IP matches the DNS entry for the current host's public address
            # We compare the set of IPs of the new hostname with the set of IPs of the current hostname.
            # If they don't match exactly (or overlap significantly in a way that implies a different host), we reject.
            # The strict interpretation of "does not match" usually means if the new host resolves to an IP that is NOT in the allowed set of the current host.
            # Assuming the 'current_host_ips' set represents the allowed IPs for the current host.
            if not (new_ips & current_host_ips):
                raise ValueError("Redirect to IP address that does not match the DNS entry for the current host's public address")
            
            # Update current state for the next iteration
            current_scheme = redirect_parsed.scheme
            current_port = redirect_port or (80 if current_scheme == 'http' else 443)
            current_path = redirect_parsed.path
            url = redirect_parsed.geturl()
        
        else:
            # No redirect, break loop
            break
    
    # Return the body
    return body
