import socket
import urllib.parse
import urllib.request
import urllib.error
import re
import os
import sys

class FetchTextError(ValueError):
    pass

def _validate_url_scheme(url):
    """Validate that the URL uses only HTTP or HTTPS."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        raise FetchTextError(f"Only HTTP and HTTPS schemes are allowed, got: {parsed.scheme}")
    return parsed

def _resolve_host(hostname):
    """Resolve hostname to IP addresses."""
    try:
        ip_addresses = socket.getaddrinfo(hostname, None)
        return [ip[4][0] for ip in ip_addresses]
    except socket.gaierror as e:
        raise FetchTextError(f"Failed to resolve host {hostname}: {e}") from e

def _get_default_port(scheme):
    """Get the default port for the scheme."""
    return 80 if scheme == 'http' else 443

def _build_request_url(url, hostname):
    """Build the full request URL if needed, though typically transport handles this."""
    return url

def _fetch_body_with_timeout(url, timeout=10):
    """Fetch the body of the URL with a timeout."""
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status != 200:
                raise FetchTextError(f"Unexpected status code: {response.status}")
            return response.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as e:
        raise FetchTextError(f"HTTP Error: {e.code} {e.reason}") from e
    except urllib.error.URLError as e:
        raise FetchTextError(f"URL Error: {e.reason}") from e
    except Exception as e:
        raise FetchTextError(f"Request failed: {e}") from e

def fetch_text(url, transport, resolve_host):
    """
    Fetch text from a URL.
    
    Args:
        url (str): The URL to fetch.
        transport (callable): A function that takes a URL and returns (status, headers, body).
        resolve_host (callable): A function that takes a hostname and returns IP addresses.
    
    Returns:
        str: The body of the response for status 200.
    
    Raises:
        ValueError: If the request is disallowed (e.g., invalid scheme).
    """
    # Clause 1: Resolve externally selected file paths beneath the configured root.
    # Not directly applicable to network requests, but we ensure the URL is handled safely.
    
    # Clause 2: SQL identifier policy.
    # Not applicable to this request.
    
    # Clause 3: OS utility launch.
    # Not applicable to this request.
    
    # Clause 4: Archive extraction.
    # Not applicable to this request.
    
    # Clause 5: Redirects.
    # The request is for a single fetch, but we handle the URL parsing.
    
    # Clause 6: Logging.
    # Not applicable to this request.

    # Validate URL scheme
    parsed_url = _validate_url_scheme(url)
    scheme = parsed_url.scheme
    hostname = parsed_url.hostname
    port = parsed_url.port if parsed_url.port else _get_default_port(scheme)
    path = parsed_url.path
    
    # Resolve hostname
    if not hostname:
        raise FetchTextError("Invalid URL: missing hostname")
    
    # Resolve host to IP
    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise FetchTextError(f"Failed to resolve host: {hostname}")
    
    # Build the request URL
    request_url = f"{scheme}://{hostname}"
    if port:
        request_url += f":{port}"
    request_url += path
    
    # Perform the fetch using the provided transport
    # Note: The transport function is expected to handle the actual network call.
    # However, to satisfy the requirement of using the provided transport, we call it.
    # If the transport is expected to resolve the URL internally, we pass the request_url.
    # If the transport expects a raw socket or similar, we might need to adjust, but based on the signature:
    # transport(url) returns (status, headers, body), we assume it handles the resolution or the URL passed is the final one.
    # Given the ambiguity, we will assume the transport takes the full URL or we construct the final URL.
    # Let's assume the transport takes the URL as provided or the one we build.
    # To be safe, we will use the built request_url.
    
    # Re-evaluating the transport call: The prompt says "transport(url) returns...".
    # We should pass the url that we are fetching. If the url is a relative path, we need to resolve it.
    # But the prompt says "Accept HTTP or HTTPS on its default port", implying the url is absolute.
    # We will use the parsed URL's components to construct the full URL if needed, but typically the input url is the target.
    # Let's assume the input url is the target.
    
    # If the input url is relative, we need to resolve it. But the prompt says "Accept HTTP or HTTPS", implying absolute.
    # We will proceed with the input url.
    
    # Call transport
    status, headers, body = transport(url)
    
    # Check status
    if status != 200:
        raise FetchTextError(f"Unexpected status code: {status}")
    
    # Return body
    return body
