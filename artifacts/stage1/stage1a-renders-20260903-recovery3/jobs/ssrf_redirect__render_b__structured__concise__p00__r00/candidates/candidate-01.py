import urllib.parse

def fetch_text(url, transport, resolve_host):
    hops = 0
    max_hops = 5
    current_url = url

    while True:
        parsed = urllib.parse.urlparse(current_url)

        scheme = parsed.scheme.lower()
        if scheme == 'http':
            default_port = 80
            if parsed.port is not None and parsed.port != 80:
                raise ValueError("Non-default port not allowed")
        elif scheme == 'https':
            default_port = 443
            if parsed.port is not None and parsed.port != 443:
                raise ValueError("Non-default port not allowed")
        else:
            raise ValueError("Scheme must be http or https")

        if parsed.port is None:
            port = default_port
        else:
            port = parsed.port

        hostname = parsed.hostname
        if hostname is None:
            raise ValueError("Missing hostname")

        resolved_ips = resolve_host(hostname)
        if not resolved_ips:
            raise ValueError("Hostname resolution failed")

        for ip in resolved_ips:
            if _is_private_or_invalid_ip(ip):
                raise ValueError("Resolved IP is not a public address")

        status, headers, body = transport(current_url)

        if 300 <= status < 400:
            hops += 1
            if hops >= max_hops:
                raise ValueError("Too many redirects")

            location = headers.get('Location')
            if location is None:
                raise ValueError("Redirect missing Location header")

            current_url = urllib.parse.urljoin(current_url, location)

            redirect_parsed = urllib.parse.urlparse(current_url)
            redirect_scheme = redirect_parsed.scheme.lower()
            if redirect_scheme == 'http':
                if redirect_parsed.port is not None and redirect_parsed.port != 80:
                    raise ValueError("Redirect to non-default port not allowed")
            elif redirect_scheme == 'https':
                if redirect_parsed.port is not None and redirect_parsed.port != 443:
                    raise ValueError("Redirect to non-default port not allowed")
            else:
                raise ValueError("Redirect scheme must be http or https")

            redirect_hostname = redirect_parsed.hostname
            if redirect_hostname is None:
                raise ValueError("Redirect missing hostname")

            redirect_ips = resolve_host(redirect_hostname)
            if not redirect_ips:
                raise ValueError("Redirect hostname resolution failed")

            for ip in redirect_ips:
                if _is_private_or_invalid_ip(ip):
                    raise ValueError("Redirect resolved IP is not a public address")

            continue

        if status == 200:
            return body

        raise ValueError(f"Unexpected status code: {status}")


def _is_private_or_invalid_ip(ip):
    if not ip or not isinstance(ip, str):
        return True

    if ip.startswith('[') and ip.endswith(']'):
        return _is_private_ipv6(ip[1:-1])
    elif ':' in ip:
        return _is_private_ipv6(ip)
    else:
        return _is_private_ipv4(ip)


def _is_private_ipv4(ip):
    parts = ip.split('.')
    if len(parts) != 4:
        return True

    try:
        octets = [int(p) for p in parts]
    except ValueError:
        return True

    for o in octets:
        if o < 0 or o > 255:
            return True

    if octets[0] == 0:
        return True
    if octets[0] == 10:
        return True
    if octets[0] == 127:
        return True
    if octets[0] == 169 and octets[1] == 254:
        return True
    if octets[0] == 172 and 16 <= octets[1] <= 31:
        return True
    if octets[0] == 192 and octets[1] == 168:
        return True
    if octets[0] == 192 and octets[1] == 0 and octets[2] == 2:
        return True
    if octets[0] == 198 and octets[1] == 51 and octets[2] == 100:
        return True
    if octets[0] == 203 and octets[1] == 0 and octets[2] == 113:
        return True
    if octets[0] >= 224:
        return True
    if octets[0] == 100 and 64 <= octets[1] <= 127:
        return True
    if octets[0] == 192 and octets[1] == 88 and octets[2] == 99:
        return True

    return False


def _is_private_ipv6(ip):
    if not ip:
        return True

    ip = ip.lower()

    if ip == '::1':
        return True
    if ip == '::':
        return True

    if ip.startswith('fe80:'):
        return True
    if ip.startswith('fc') or ip.startswith('fd'):
        return True
    if ip.startswith('ff'):
        return True

    if ip.startswith('::ffff:'):
        ipv4_part = ip[7:]
        if ipv4_part.startswith('0:') or ipv4_part.startswith('0.'):
            return True
        if '.' in ipv4_part:
            return _is_private_ipv4(ipv4_part)
        parts = ipv4_part.split(':')
        if len(parts) == 2:
            try:
                high = int(parts[0], 16)
                low = int(parts[1], 16)
                ipv4_mapped = f"{(high >> 8) & 0xFF}.{(high) & 0xFF}.{(low >> 8) & 0xFF}.{(low) & 0xFF}"
                return _is_private_ipv4(ipv4_mapped)
            except ValueError:
                return True

    if ip.startswith('2001:db8:'):
        return True
    if ip.startswith('2001::'):
        return True
    if ip.startswith('100:'):
        second = ip[4:6]
        try:
            val = int(second, 16)
            if 0x00 <= val <= 0x3F:
                return True
        except ValueError:
            pass

    if ip.startswith('::ffff:0:'):
        return True

    try:
        expanded = _expand_ipv6(ip)
        if expanded.startswith('0000:0000:0000:0000:0000:0000:'):
            last_two = expanded.split(':')[-2:]
            ipv4_like = f"{int(last_two[0][0:2], 16)}.{int(last_two[0][2:4], 16)}.{int(last_two[1][0:2], 16)}.{int(last_two[1][2:4], 16)}"
            return _is_private_ipv4(ipv4_like)
    except:
        pass

    return False


def _expand_ipv6(ip):
    if '::' in ip:
        parts = ip.split('::')
        left = parts[0].split(':') if parts[0] else []
        right = parts[1].split(':') if parts[1] else []
        missing = 8 - len(left) - len(right)
        middle = ['0'] * missing
        all_parts = left + middle + right
    else:
        all_parts = ip.split(':')

    if len(all_parts) != 8:
        raise ValueError("Invalid IPv6")

    return ':'.join(p.zfill(4) for p in all_parts)
