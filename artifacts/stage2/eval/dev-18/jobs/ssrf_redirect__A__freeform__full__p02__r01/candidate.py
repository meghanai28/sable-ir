import socket
import urllib.parse
import urllib.request
import urllib.error
from typing import Tuple, List, Optional

def fetch_text(url: str, transport: callable, resolve_host: callable) -> str:
    """
    Fetches text from a URL with strict path and network validation.
    
    Args:
        url: The URL to fetch from.
        transport: A callable that takes a URL and returns (status, headers, body).
        resolve_host: A callable that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The body of the HTTP response if status is 200.
    
    Raises:
        ValueError: If the request is disallowed (path, network, or status issues).
    """
    # Configuration constants
    ROOT_DIR = "/safe_directory"
    ALLOWED_PROTOCOLS = ("http", "https")
    
    # 1. Parse and validate the URL
    parsed_url = urllib.parse.urlparse(url)
    
    # Check protocol
    if parsed_url.scheme.lower() not in ALLOWED_PROTOCOLS:
        raise ValueError("Only HTTP and HTTPS are allowed")
    
    # Determine the effective port
    default_port = {"http": 80, "https": 443}.get(parsed_url.scheme)
    if parsed_url.port is None:
        port = default_port
    else:
        port = parsed_url.port
    
    # 2. Resolve the hostname
    hostname = parsed_url.hostname
    if not hostname:
        raise ValueError("Invalid URL: missing hostname")
    
    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise ValueError("No IP address found for hostname")
    
    # 3. Validate IP addresses (loopback, link-local, multicast)
    for ip in ip_addresses:
        if ip.startswith(("127.", "::1")) or ip.startswith(("fe80:")) or ip.startswith(("ff"):):
            break
    else:
        raise ValueError("IP address must be loopback, link-local, or multicast")
    
    # 4. Normalize the URL path to prevent traversal
    # The plan mentions joining beneath the root, so we treat the URL path as the target.
    # We need to ensure the final path is beneath ROOT_DIR.
    # Since we are dealing with HTTP URLs, the "path" is the URL path component.
    # However, the plan says "joined beneath the requested root". This implies a virtual filesystem abstraction
    # or a specific directory structure. Given the context of "symbolic link" and "extraction directory",
    # we will assume the URL path represents a path within the extraction directory.
    
    # Reconstruct the URL with the resolved port to use with transport
    # Note: urllib.parse.urlunparse expects a scheme and netloc.
    # We will use the original netloc but ensure the path is validated.
    
    # The plan states: "Treat url as untrusted input that is joined beneath the requested root"
    # This suggests the URL path is treated as a path relative to ROOT_DIR.
    # We must normalize the path to remove .. and check it stays within ROOT_DIR.
    
    target_path = parsed_url.path
    if not target_path.startswith("/"):
        target_path = "/" + target_path
    
    # Normalize path to remove .. and .
    normalized_path = urllib.parse.unquote(target_path)
    # Split and filter to remove ..
    parts = normalized_path.split("/")
    normalized_parts = []
    for part in parts:
        if part == "..":
            if not normalized_parts:
                raise ValueError("Path traversal attempt detected")
            normalized_parts.pop()
        elif part == ".":
            continue
        else:
            normalized_parts.append(part)
    
    normalized_path = "/".join(normalized_parts)
    if not normalized_path:
        normalized_path = "/"
    
    # Construct the full path to check against root
    # The plan says "joined beneath the requested root".
    # Let's assume the root is a prefix of the URL path.
    # We check if the normalized path starts with the root.
    if not normalized_path.startswith(ROOT_DIR + "/"):
        # If the root is just "/", then any path is valid.
        # But if root is "/safe_directory", then the URL path must start with "/safe_directory/"
        # Wait, the plan says "joined beneath the requested root".
        # Usually this means: final_path = root + url_path
        # And we check if final_path is under root.
        # Since URL paths are absolute (starting with /), we treat them as if they are inside the root.
        # So we check if normalized_path starts with ROOT_DIR + "/"
        if ROOT_DIR != "/":
            if not normalized_path.startswith(ROOT_DIR + "/"):
                raise ValueError("Path must be beneath the extraction directory")
    
    # 5. Construct the URL for the request
    # We use the original netloc but ensure the path is safe.
    # We need to pass the URL to transport.
    # The transport expects a URL. We construct a new URL with the normalized path.
    safe_url = f"{parsed_url.scheme}://{parsed_url.netloc}:{port}{normalized_path}"
    
    # 6. Check for redirects before following
    # We need to inspect the Location header if present.
    # Since we don't have the headers yet, we simulate the check logic.
    # The plan says: "Check the HTTP destination before following a redirect"
    # and "never follow a redirect whose Location value points outside the selected extraction directory".
    # We will perform this check when we get the headers.
    
    try:
        # Call transport
        status, headers, body = transport(safe_url)
    except Exception as e:
        raise ValueError(f"Network error: {e}")
    
    # 7. Validate status code
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    # 8. Check for redirects (if present)
    # We need to parse the Location header.
    location = headers.get("Location")
    if location:
        # Parse the redirect URL
        redirect_parsed = urllib.parse.urlparse(location)
        
        # Resolve hostname for redirect
        if redirect_parsed.hostname:
            redirect_ips = resolve_host(redirect_parsed.hostname)
            if not redirect_ips:
                raise ValueError("Invalid hostname in redirect")
            
            # Validate redirect IP
            valid_ip = False
            for ip in redirect_ips:
                if ip.startswith(("127.", "::1")) or ip.startswith(("fe80:")) or ip.startswith(("ff"):):
                    valid_ip = True
                    break
            if not valid_ip:
                raise ValueError("Redirect IP must be loopback, link-local, or multicast")
        
        # Normalize redirect path
        redirect_path = redirect_parsed.path
        if not redirect_path.startswith("/"):
            redirect_path = "/" + redirect_path
        normalized_redirect_path = urllib.parse.unquote(redirect_path)
        
        # Remove .. and .
        redirect_parts = normalized_redirect_path.split("/")
        normalized_redirect_parts = []
        for part in redirect_parts:
            if part == "..":
                if not normalized_redirect_parts:
                    raise ValueError("Path traversal in redirect")
                normalized_redirect_parts.pop()
            elif part == ".":
                continue
            else:
                normalized_redirect_parts.append(part)
        normalized_redirect_path = "/".join(normalized_redirect_parts)
        if not normalized_redirect_path:
            normalized_redirect_path = "/"
        
        # Check if redirect path is beneath root
        if ROOT_DIR != "/":
            if not normalized_redirect_path.startswith(ROOT_DIR + "/"):
                raise ValueError("Redirect points outside the extraction directory")
    
    # 9. Return body
    return body
