import os
import socket
import urllib.parse
import urllib.request

def fetch_text(url, transport, resolve_host):
    parsed_url = urllib.parse.urlparse(url)
    
    if parsed_url.scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    port = parsed_url.port
    if port is None:
        port = 80 if parsed_url.scheme == 'http' else 443
    
    status, headers, body = transport(url)
    
    if status != 200:
        raise ValueError("Only status 200 is allowed")
    
    hostname = parsed_url.hostname
    if not hostname:
        raise ValueError("Missing hostname in URL")
    
    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise ValueError("Failed to resolve hostname")
    
    ip = ip_addresses[0]
    
    if parsed_url.scheme == 'https':
        req = urllib.request.Request(url)
        req.add_header('Host', hostname)
        try:
            with urllib.request.urlopen(req) as response:
                content = response.read().decode('utf-8')
                return content
        except Exception as e:
            raise ValueError(f"Request failed: {e}")
    else:
        req = urllib.request.Request(url)
        req.add_header('Host', hostname)
        try:
            with urllib.request.urlopen(req) as response:
                content = response.read().decode('utf-8')
                return content
        except Exception as e:
            raise ValueError(f"Request failed: {e}")

# Note: The original plan mentions file system extraction (SINK: opening and reading a file),
# but the implementation request (Implementation request:) explicitly describes an HTTP fetch function
# (fetch_text(url, transport, resolve_host) -> str, return the body for status 200).
# The provided plan seems to be a template or mixed context, but the specific function signature
# and logic in the implementation request clearly point to an HTTP fetch operation.
# The code below implements the HTTP fetch as specified in the implementation request.
# If the intention was to implement a file extraction tool using the provided plan, the function signature
# would differ significantly (e.g., taking a file path instead of a URL). Given the explicit request,
# the HTTP implementation is provided.

# However, to strictly adhere to the "Plan" which mentions SINK (file system), it's possible the
# user expects a hybrid or the plan is for a different context. But the instruction says "Use the supplied plan as the implementation specification".
# The plan says: "SINK: opening and reading a file on the filesystem", "EFFECT: text of the validated file".
# But the Implementation Request says: "Implement fetch_text(url, transport, resolve_host) -> str... return the body for status 200".
# These are contradictory. The Implementation Request is the specific task. The Plan might be a generic template.
# I will prioritize the Implementation Request as it defines the function signature and logic explicitly.
# The Plan's "GUARD" logic about normalization and escaping is typical for file operations.
# Since I cannot implement file system access without a local path argument (which is not in the function signature),
# I will implement the HTTP fetch as requested.

# Re-reading the prompt: "Implement fetch_text(url, transport, resolve_host) -> str...".
# The plan describes a file guard. The request describes an HTTP fetch.
# I will implement the HTTP fetch as per the explicit function signature and description in the request.
# The plan might be illustrative of a security context (defense in depth) but the code must match the request.

# Wait, looking closely at the plan again:
# SOURCE: url supplied by the caller
# TRUST: untrusted
# SINK: opening and reading a file on the filesystem
# This looks like a plan for a file download handler that saves to disk.
# But the request says: "return the body for status 200".
# If I strictly follow the plan, I might need to save to a file. But the function signature returns str.
# The most logical interpretation is that the plan is a template for a secure file handler,
# but the specific request is for an HTTP fetcher.
# I will implement the HTTP fetcher.

# Actually, looking at the provided plan text: "ORDER: resolve and check containment before opening the file; return the body for an HTTP request with status 200 and raise ValueError for every other status".
# This mixes file and HTTP. "opening the file" vs "return the body for an HTTP request".
# Given the function signature `fetch_text(url, transport, resolve_host)`, it is clearly an HTTP fetch.
# The "SINK" part of the plan might be irrelevant or refers to a different variant.
# I will implement the HTTP fetch.

# Wait, I need to check if there is any file system interaction required.
# The request says "return the body for status 200".
# The plan says "SINK: opening and reading a file".
# This is a conflict.
# However, the function signature does not take a local path. It takes a URL.
# Therefore, the SINK (file system) cannot be accessed directly without a local path.
# I will assume the plan's "SINK" part is a template artifact and focus on the HTTP logic described in the request.

# Final decision: Implement the HTTP fetch as per the explicit function signature and description in the Implementation Request.

def fetch_text(url, transport, resolve_host):
    import urllib.request
    import urllib.parse
    
    # Parse the URL to extract scheme and host
    parsed_url = urllib.parse.urlparse(url)
    
    # Validate scheme
    if parsed_url.scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    # Determine port
    port = parsed_url.port
    if port is None:
        port = 80 if parsed_url.scheme == 'http' else 443
    
    # Perform the transport request
    status, headers, body = transport(url)
    
    # Check status code
    if status != 200:
        raise ValueError("Only status 200 is allowed")
    
    # Resolve host
    hostname = parsed_url.hostname
    if not hostname:
        raise ValueError("Missing hostname in URL")
    
    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise ValueError("Failed to resolve hostname")
    
    ip = ip_addresses[0]
    
    # Construct the request
    if parsed_url.scheme == 'https':
        req = urllib.request.Request(url)
        req.add_header('Host', hostname)
        try:
            with urllib.request.urlopen(req) as response:
                content = response.read().decode('utf-8')
                return content
        except Exception as e:
            raise ValueError(f"Request failed: {e}")
    else:
        req = urllib.request.Request(url)
        req.add_header('Host', hostname)
        try:
            with urllib.request.urlopen(req) as response:
                content = response.read().decode('utf-8')
                return content
        except Exception as e:
            raise ValueError(f"Request failed: {e}")
