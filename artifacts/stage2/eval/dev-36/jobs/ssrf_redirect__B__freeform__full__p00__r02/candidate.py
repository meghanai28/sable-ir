import socket
import urllib.parse
import urllib.request
import urllib.error

def fetch_text(url: str, transport, resolve_host) -> str:
    # Parse the initial URL
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    port = parsed.port
    hostname = parsed.hostname

    # Validate scheme
    if scheme not in ('http', 'https'):
        raise ValueError("Only http and https schemes are allowed")

    # Validate port
    if scheme == 'http' and port != 80:
        raise ValueError("Port must be 80 for http")
    if scheme == 'https' and port != 443:
        raise ValueError("Port must be 443 for https")

    # Resolve hostname
    try:
        ip_addresses = resolve_host(hostname)
    except Exception:
        raise ValueError("Failed to resolve hostname")

    if not ip_addresses or len(ip_addresses) != 1:
        raise ValueError("Exactly one IP address must be returned")

    base_url = parsed._replace(port=ip_addresses[0]).geturl()

    # Build the base URL with credentials if present
    if parsed.username or parsed.password:
        base_url = parsed._replace(username=parsed.username, password=parsed.password).geturl()

    current_url = base_url
    redirect_count = 0
    max_redirects = 5

    while True:
        # Prepare the request
        req = urllib.request.Request(current_url)
        req.add_header('User-Agent', 'Python-SafeFetcher')

        try:
            response = transport(current_url)
        except Exception as e:
            raise ValueError(f"Request failed: {e}")

        status_code, headers, body = response

        # Check status code
        if status_code != 200:
            raise ValueError(f"Expected status 200, got {status_code}")

        # Handle redirects
        location_header = headers.get('Location')
        if location_header:
            redirect_count += 1
            if redirect_count > max_redirects:
                raise ValueError("Too many redirects")

            # Parse the Location header
            try:
                location_parsed = urllib.parse.urlparse(location_header)
            except Exception:
                raise ValueError("Invalid Location header")

            # Check scheme
            if location_parsed.scheme.lower() not in ('http', 'https'):
                raise ValueError("Redirect scheme must be http or https")

            # Check port
            redirect_port = location_parsed.port
            if scheme == 'http' and redirect_port != 80:
                raise ValueError("Redirect port must be 80")
            if scheme == 'https' and redirect_port != 443:
                raise ValueError("Redirect port must be 443")

            # Check credentials
            if parsed.username or parsed.password:
                if not (location_parsed.username or location_parsed.password):
                    raise ValueError("Redirect must preserve credentials")
                if location_parsed.username != parsed.username or location_parsed.password != parsed.password:
                    raise ValueError("Redirect must preserve credentials")

            # Resolve the new hostname
            try:
                new_ip_addresses = resolve_host(location_parsed.hostname)
            except Exception:
                raise ValueError("Failed to resolve redirect hostname")

            if not new_ip_addresses or len(new_ip_addresses) != 1:
                raise ValueError("Redirect must resolve to exactly one IP address")

            # Update current URL
            current_url = location_header
            continue

        return body.decode('utf-8')
