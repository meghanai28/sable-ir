import re
import ipaddress
from urllib.parse import urlparse, urljoin

def fetch_text(url, transport, resolve_host):
    def parse_url(url_str):
        parsed = urlparse(url_str)
        scheme = parsed.scheme.lower()
        hostname = parsed.hostname
        port = parsed.port
        path = parsed.path if parsed.path else '/'
        query = '?' + parsed.query if parsed.query else ''
        username = parsed.username
        password = parsed.password
        return scheme, hostname, port, path, query, username, password

    def validate_scheme_port(scheme, port):
        if scheme == 'http':
            if port is not None and port != 80:
                raise ValueError
            return 80
        elif scheme == 'https':
            if port is not None and port != 443:
                raise ValueError
            return 443
        else:
            raise ValueError

    def validate_credentials(username, password):
        if username is not None or password is not None:
            raise ValueError

    def validate_hostname(hostname):
        if hostname is None or hostname == '':
            raise ValueError
        if len(hostname) > 253:
            raise ValueError
        labels = hostname.split('.')
        for label in labels:
            if label == '':
                continue
            if len(label) > 63:
                raise ValueError
            if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$', label):
                raise ValueError

    def validate_ip_address(ip_str):
        try:
            addr = ipaddress.ip_address(ip_str)
        except ValueError:
            raise ValueError
        if addr.version == 4:
            if addr.is_private or addr.is_loopback or addr.is_reserved or addr.is_multicast or addr.is_unspecified:
                raise ValueError
            octets = str(addr).split('.')
            first_octet = int(octets[0])
            if first_octet == 0 or first_octet == 10 or (first_octet == 100 and 64 <= int(octets[1]) <= 127) or (first_octet == 127) or (first_octet == 169 and int(octets[1]) == 254) or (first_octet == 172 and 16 <= int(octets[1]) <= 31) or (first_octet == 192 and int(octets[1]) == 0 and int(octets[2]) == 2) or (first_octet == 192 and int(octets[1]) == 88 and int(octets[2]) == 99) or (first_octet == 192 and int(octets[1]) == 168) or (first_octet == 198 and (int(octets[1]) == 18 or int(octets[1]) == 19)) or (first_octet == 198 and int(octets[1]) == 51 and int(octets[2]) == 100) or (first_octet == 203 and int(octets[1]) == 0 and int(octets[2]) == 113) or first_octet >= 224:
                raise ValueError
        elif addr.version == 6:
            if addr.is_private or addr.is_loopback or addr.is_reserved or addr.is_multicast or addr.is_unspecified or addr.ipv4_mapped or addr.ipv4_compatible:
                raise ValueError
            if str(addr).lower().startswith('fc') or str(addr).lower().startswith('fd'):
                raise ValueError
            if str(addr).lower().startswith('fe80') or str(addr).lower().startswith('fec0'):
                raise ValueError
            if str(addr).lower().startswith('ff'):
                raise ValueError
            if str(addr) == '::1' or str(addr) == '::':
                raise ValueError
            if addr.ipv4_mapped:
                raise ValueError

    def resolve_and_validate(hostname):
        validate_hostname(hostname)
        try:
            ips = resolve_host(hostname)
        except Exception:
            raise ValueError
        if not ips:
            raise ValueError
        if isinstance(ips, str):
            ips = [ips]
        ips = list(ips)
        if not ips:
            raise ValueError
        for ip in ips:
            validate_ip_address(ip)
        return ips

    def build_url(scheme, hostname, port, path, query):
        default_port = 80 if scheme == 'http' else 443
        netloc = hostname
        if port is not None and port != default_port:
            netloc = f"{hostname}:{port}"
        return f"{scheme}://{netloc}{path}{query}"

    def process_url(url_str, redirect_count):
        scheme, hostname, port, path, query, username, password = parse_url(url_str)
        validate_scheme_port(scheme, port)
        validate_credentials(username, password)
        resolve_and_validate(hostname)
        request_url = build_url(scheme, hostname, port, path, query)
        return request_url, scheme, hostname

    redirect_count = 0
    current_url = url

    while True:
        request_url, scheme, hostname = process_url(current_url, redirect_count)

        try:
            status, headers, body = transport(request_url)
        except Exception:
            raise ValueError

        if status == 200:
            return body

        if 300 <= status < 400:
            if redirect_count >= 5:
                raise ValueError

            location = None
            if isinstance(headers, dict):
                for key in headers:
                    if key.lower() == 'location':
                        location = headers[key]
                        break
            elif isinstance(headers, (list, tuple)):
                for header in headers:
                    if isinstance(header, (list, tuple)) and len(header) >= 2:
                        if header[0].lower() == 'location':
                            location = header[1]
                            break
                    elif isinstance(header, str):
                        parts = header.split(':', 1)
                        if len(parts) == 2 and parts[0].strip().lower() == 'location':
                            location = parts[1].strip()
                            break

            if location is None:
                raise ValueError

            try:
                new_url = urljoin(current_url, location)
            except Exception:
                raise ValueError

            try:
                parsed_new = urlparse(new_url)
                if not parsed_new.scheme or not parsed_new.hostname:
                    raise ValueError
            except Exception:
                raise ValueError

            redirect_count += 1
            current_url = new_url
            continue

        raise ValueError
