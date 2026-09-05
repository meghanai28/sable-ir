import socket
import urllib.parse
import urllib.request
import urllib.error

def fetch_text(url: str, transport, resolve_host) -> str:
    # Parse the URL to extract components
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    port = parsed.port
    host = parsed.hostname
    path = parsed.path
    query = parsed.query
    fragment = parsed.fragment

    # Validate scheme
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")

    # Validate port
    if port is not None:
        if scheme == 'http' and port != 80:
            raise ValueError("HTTP must use port 80.")
        if scheme == 'https' and port != 443:
            raise ValueError("HTTPS must use port 443.")

    # Resolve host
    if not resolve_host(host):
        raise ValueError("resolve_host must return at least one IP address.")

    # Build the full URL for transport
    full_url = parsed._replace(path=path, query=query, fragment=fragment).geturl()

    # Initial request
    while True:
        status, headers, body = transport(full_url)

        # Check status code
        if status != 200:
            raise ValueError(f"Unexpected status code: {status}")

        # Check for redirects
        if 'location' in headers.lower():
            redirect_url = headers['location']
            redirect_parsed = urllib.parse.urlparse(redirect_url)

            # Check for dangerous schemes
            if redirect_parsed.scheme.lower() in ('javascript', 'data'):
                raise ValueError("Redirect to dangerous scheme (javascript or data) is not allowed.")

            # Check scheme and port consistency
            if redirect_parsed.scheme != scheme:
                raise ValueError("Redirect must preserve the scheme.")
            if port is not None and redirect_parsed.port != port:
                raise ValueError("Redirect must preserve the port.")

            # Resolve the new host
            new_host = redirect_parsed.hostname
            if not resolve_host(new_host):
                raise ValueError("resolve_host must return at least one IP address.")

            # Update the URL
            new_url = redirect_parsed._replace(path=redirect_parsed.path, query=redirect_parsed.query, fragment=redirect_parsed.fragment).geturl()
            full_url = new_url
            continue
        else:
            return body.decode('utf-8') if isinstance(body, bytes) else body
