import ipaddress
import re
import urllib.parse

def fetch_text(url, transport, resolve_host):
    max_redirects = 5
    hop_count = 0
    current_url = url

    def is_public_ip(ip_str):
        try:
            addr = ipaddress.ip_address(ip_str)
            return not (
                addr.is_private
                or addr.is_loopback
                or addr.is_link_local
                or addr.is_multicast
                or addr.is_reserved
                or addr.is_unspecified
                or (isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is None and addr.is_site_local)
            )
        except ValueError:
            return False

    def validate_and_resolve(parsed):
        scheme = parsed.scheme.lower()
        if scheme not in ('http', 'https'):
            raise ValueError("Only HTTP and HTTPS schemes are allowed")

        hostname = parsed.hostname
        if hostname is None:
            raise ValueError("URL must have a hostname")

        port = parsed.port
        if scheme == 'http' and port is not None and port != 80:
            raise ValueError("HTTP must use default port 80")
        if scheme == 'https' and port is not None and port != 443:
            raise ValueError("HTTPS must use default port 443")

        if '@' in parsed.netloc:
            raise ValueError("Credentials in URL are not allowed")

        if re.search(r'[^\x00-\x7F]', hostname):
            try:
                import idna
                hostname = idna.encode(hostname).decode('ascii')
            except ImportError:
                raise ValueError("Internationalized domain names require idna module")
            except Exception:
                raise ValueError("Invalid internationalized domain name")

        try:
            ipaddress.ip_address(hostname)
            is_ip = True
        except ValueError:
            is_ip = False

        if is_ip:
            if not is_public_ip(hostname):
                raise ValueError("IP address must be public")
            return hostname, hostname
        else:
            ips = resolve_host(hostname)
            if not ips:
                raise ValueError("Hostname could not be resolved")
            for ip in ips:
                if not is_public_ip(ip):
                    raise ValueError("Resolved IP address must be public")
            return hostname, ips[0]

    def make_url(parsed, hostname):
        scheme = parsed.scheme.lower()
        netloc = hostname
        if parsed.port is not None:
            if scheme == 'http' and parsed.port != 80:
                netloc += ':' + str(parsed.port)
            elif scheme == 'https' and parsed.port != 443:
                netloc += ':' + str(parsed.port)
        else:
            if scheme == 'http':
                netloc += ':80'
            else:
                netloc += ':443'
        return urllib.parse.urlunparse((
            scheme,
            netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))

    def validate_url(url_str):
        try:
            parsed = urllib.parse.urlparse(url_str)
        except Exception:
            raise ValueError("Invalid URL")

        if not parsed.scheme or not parsed.netloc:
            raise ValueError("Invalid URL structure")

        hostname, resolved_ip = validate_and_resolve(parsed)
        validated_url = make_url(parsed, resolved_ip)
        return validated_url, parsed, hostname, resolved_ip

    validated_url, parsed, hostname, resolved_ip = validate_url(current_url)

    while True:
        if hop_count > max_redirects:
            raise ValueError("Too many redirects")

        status, headers, body = transport(validated_url)

        if status == 200:
            return body

        if 300 <= status < 400:
            hop_count += 1
            if hop_count > max_redirects:
                raise ValueError("Too many redirects")

            location = None
            for key, value in headers.items() if isinstance(headers, dict) else headers:
                if key.lower() == 'location':
                    location = value
                    break

            if location is None:
                raise ValueError("Redirect response missing Location header")

            current_url = urllib.parse.urljoin(current_url, location)

            validated_url, parsed, hostname, resolved_ip = validate_url(current_url)
            continue

        raise ValueError(f"Unexpected HTTP status: {status}")
