import urllib.parse
import ipaddress

def fetch_text(url, transport, resolve_host):
    def parse_url(url_string):
        parsed = urllib.parse.urlparse(url_string)
        scheme = parsed.scheme.lower()
        hostname = parsed.hostname
        port = parsed.port
        path = parsed.path if parsed.path else '/'
        query = parsed.query
        username = parsed.username
        password = parsed.password
        return scheme, hostname, port, path, query, username, password

    def validate_scheme_port(scheme, port):
        if scheme == 'http':
            if port is not None and port != 80:
                raise ValueError("Non-default port for HTTP")
        elif scheme == 'https':
            if port is not None and port != 443:
                raise ValueError("Non-default port for HTTPS")
        else:
            raise ValueError("Disallowed scheme")

    def validate_credentials(username, password):
        if username is not None or password is not None:
            raise ValueError("Embedded credentials not allowed")

    def validate_ip_address(ip_str):
        try:
            addr = ipaddress.ip_address(ip_str)
        except ValueError:
            raise ValueError("Invalid IP address")
        if addr.is_loopback:
            raise ValueError("Loopback address not allowed")
        if addr.is_link_local:
            raise ValueError("Link-local address not allowed")
        if addr.is_multicast:
            raise ValueError("Multicast address not allowed")
        if addr.is_reserved:
            raise ValueError("Reserved address not allowed")
        if addr.is_private:
            raise ValueError("Private address not allowed")
        if addr.version == 4:
            if addr.is_unspecified:
                raise ValueError("Unspecified address not allowed")
        else:
            if addr.is_unspecified:
                raise ValueError("Unspecified address not allowed")
        return True

    def validate_host(hostname):
        if hostname is None or hostname == '':
            raise ValueError("Missing hostname")
        ips = resolve_host(hostname)
        if not ips:
            raise ValueError("Host resolution failed")
        for ip in ips:
            validate_ip_address(ip)
        return True

    def build_url(scheme, hostname, port, path, query):
        netloc = hostname
        if port is not None:
            if (scheme == 'http' and port != 80) or (scheme == 'https' and port != 443):
                netloc = f"{hostname}:{port}"
        if query:
            return f"{scheme}://{netloc}{path}?{query}"
        return f"{scheme}://{netloc}{path}"

    def resolve_location(location, base_url):
        return urllib.parse.urljoin(base_url, location)

    def do_fetch(current_url, redirect_count):
        scheme, hostname, port, path, query, username, password = parse_url(current_url)
        validate_scheme_port(scheme, port)
        validate_credentials(username, password)
        validate_host(hostname)
        status, headers, body = transport(current_url)
        if status == 200:
            return body
        if 300 <= status < 400:
            if redirect_count >= 5:
                raise ValueError("Too many redirects")
            location = headers.get('Location')
            if location is None:
                raise ValueError("Missing Location header")
            new_url = resolve_location(location, current_url)
            scheme, hostname, port, path, query, username, password = parse_url(new_url)
            validate_scheme_port(scheme, port)
            validate_credentials(username, password)
            validate_host(hostname)
            return do_fetch(new_url, redirect_count + 1)
        raise ValueError(f"Unexpected status: {status}")

    return do_fetch(url, 0)
