import ipaddress
import urllib.parse

def fetch_text(url, transport, resolve_host):
    max_redirects = 5
    redirect_count = 0
    current_url = url

    def validate_hostname(hostname):
        if not hostname:
            raise ValueError("Empty hostname")
        if hostname.startswith('.') or hostname.endswith('.'):
            test_host = hostname.strip('.')
            if not test_host:
                raise ValueError("Invalid hostname")
        else:
            test_host = hostname
        if len(test_host) > 253:
            raise ValueError("Hostname too long")
        labels = test_host.split('.')
        for label in labels:
            if not label:
                raise ValueError("Empty label in hostname")
            if len(label) > 63:
                raise ValueError("Label too long")
            if label.startswith('-') or label.endswith('-'):
                raise ValueError("Invalid label start/end")
            for ch in label:
                if not (ch.isalnum() or ch == '-'):
                    raise ValueError("Invalid character in hostname")
        return True

    def is_public_ip(ip_str):
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            return False
        if ip.is_loopback:
            return False
        if ip.is_private:
            return False
        if ip.is_link_local:
            return False
        if ip.is_multicast:
            return False
        if ip.is_reserved:
            return False
        if ip.is_unspecified:
            return False
        if hasattr(ip, 'is_global') and not ip.is_global:
            if ip.version == 4:
                if not ip.is_private and not ip.is_loopback and not ip.is_link_local and not ip.is_multicast and not ip.is_reserved and not ip.is_unspecified:
                    pass
                else:
                    return False
            else:
                return False
        if ip.version == 6:
            if ip.ipv4_mapped is not None:
                mapped = ipaddress.ip_address(str(ip.ipv4_mapped))
                if mapped.is_loopback or mapped.is_private or mapped.is_link_local or mapped.is_multicast or mapped.is_reserved or mapped.is_unspecified:
                    return False
                if hasattr(mapped, 'is_global') and not mapped.is_global:
                    if not (not mapped.is_private and not mapped.is_loopback and not mapped.is_link_local and not mapped.is_multicast and not mapped.is_reserved and not mapped.is_unspecified):
                        return False
        return True

    def validate_url(url_to_validate):
        try:
            parsed = urllib.parse.urlparse(url_to_validate)
        except Exception:
            raise ValueError("URL parse error")

        scheme = parsed.scheme.lower()
        if scheme not in ('http', 'https'):
            raise ValueError("Invalid scheme")

        default_port = 80 if scheme == 'http' else 443

        netloc = parsed.netloc
        if '@' in netloc:
            raise ValueError("Credentials not allowed")

        if netloc.startswith('['):
            bracket_end = netloc.find(']')
            if bracket_end == -1:
                raise ValueError("Invalid IPv6 literal")
            host_part = netloc[:bracket_end + 1]
            port_part = netloc[bracket_end + 1:]
        else:
            if ':' in netloc:
                last_colon = netloc.rfind(':')
                host_part = netloc[:last_colon]
                port_part = netloc[last_colon:]
            else:
                host_part = netloc
                port_part = ''

        if port_part:
            if not port_part.startswith(':'):
                raise ValueError("Invalid port format")
            try:
                port_num = int(port_part[1:])
            except ValueError:
                raise ValueError("Invalid port")
            if port_num != default_port:
                raise ValueError("Non-default port not allowed")
        else:
            pass

        hostname = host_part.strip('[]')

        if not hostname:
            raise ValueError("Empty hostname")

        validate_hostname(hostname)

        try:
            ipaddress.ip_address(hostname)
            is_ip_literal = True
        except ValueError:
            is_ip_literal = False

        if is_ip_literal:
            if not is_public_ip(hostname):
                raise ValueError("Non-public IP address")
        else:
            resolved_ips = resolve_host(hostname)
            if not resolved_ips:
                raise ValueError("Host resolution failed")
            for ip in resolved_ips:
                if not is_public_ip(ip):
                    raise ValueError("Non-public IP address")

        reconstructed = urllib.parse.urlunparse((
            scheme,
            hostname + (':' + str(default_port) if False else ''),
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))

        if port_part:
            netloc_for_rebuild = hostname + ':' + str(default_port)
        else:
            netloc_for_rebuild = hostname

        normalized_url = urllib.parse.urlunparse((
            scheme,
            netloc_for_rebuild,
            parsed.path,
            parsed.params,
            parsed.query,
            ''
        ))

        return normalized_url

    def resolve_location(base_url, location):
        if not location:
            raise ValueError("Missing Location header")
        try:
            absolute = urllib.parse.urljoin(base_url, location)
        except Exception:
            raise ValueError("Location resolution failed")
        return absolute

    current_url = validate_url(current_url)

    while True:
        status, headers, body = transport(current_url)

        if status == 200:
            return body

        if 300 <= status < 400:
            redirect_count += 1
            if redirect_count > max_redirects:
                raise ValueError("Too many redirects")

            if isinstance(headers, dict):
                location = headers.get('Location') or headers.get('location')
            elif isinstance(headers, (list, tuple)):
                location = None
                for name, value in headers:
                    if name.lower() == 'location':
                        location = value
                        break
            else:
                location = None

            if not location:
                raise ValueError("Missing Location header")

            current_url = resolve_location(current_url, location)
            current_url = validate_url(current_url)
            continue

        raise ValueError("Unsupported HTTP status")
