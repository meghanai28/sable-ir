import urllib.parse

def fetch_text(url, transport, resolve_host):
    def is_public_address(ip_str):
        parts = ip_str.split('.')
        if len(parts) != 4:
            return False
        try:
            octets = [int(p) for p in parts]
        except ValueError:
            return False
        if not all(0 <= o <= 255 for o in octets):
            return False
        if octets[0] == 0:
            return False
        if octets[0] == 10:
            return False
        if octets[0] == 172 and 16 <= octets[1] <= 31:
            return False
        if octets[0] == 192 and octets[1] == 168:
            return False
        if octets[0] == 127:
            return False
        if octets[0] == 169 and octets[1] == 254:
            return False
        if octets[0] >= 224:
            return False
        return True

    def validate_url(target_url):
        parsed = urllib.parse.urlparse(target_url)
        scheme = parsed.scheme.lower()
        if scheme not in ('http', 'https'):
            raise ValueError("Invalid scheme")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Credentials not allowed")
        hostname = parsed.hostname
        if hostname is None:
            raise ValueError("Missing hostname")
        if hostname.startswith('[') and hostname.endswith(']'):
            raise ValueError("IPv6 not supported")
        port = parsed.port
        if scheme == 'http':
            if port is not None and port != 80:
                raise ValueError("Invalid port for HTTP")
        else:
            if port is not None and port != 443:
                raise ValueError("Invalid port for HTTPS")
        try:
            ip_addresses = resolve_host(hostname)
        except Exception:
            raise ValueError("DNS resolution failed")
        if not ip_addresses:
            raise ValueError("No DNS results")
        for ip in ip_addresses:
            if not is_public_address(ip):
                raise ValueError("Non-public address")
        return parsed

    current_url = url
    validate_url(current_url)
    hop_count = 0

    while True:
        status, headers, body = transport(current_url)
        if status == 200:
            return body
        if status in (301, 302, 307, 308):
            hop_count += 1
            if hop_count > 5:
                raise ValueError("Too many redirects")
            location = headers.get('Location')
            if location is None:
                raise ValueError("Missing Location header")
            current_url = urllib.parse.urljoin(current_url, location)
            validate_url(current_url)
            continue
        raise ValueError("Unexpected status")
