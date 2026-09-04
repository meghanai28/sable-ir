import urllib.parse

_DEFAULT_PORTS = {"http": 80, "https": 443}
_MAX_REDIRECTS = 5


def _validate_scheme_port(url):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Scheme must be http or https")
    port = parsed.port
    if port is None:
        port = _DEFAULT_PORTS[parsed.scheme]
    if port != _DEFAULT_PORTS[parsed.scheme]:
        raise ValueError("Non-default port not allowed")
    return parsed


def _validate_host_addresses(hostname, resolve_host):
    if not hostname:
        raise ValueError("Empty hostname")
    try:
        addresses = resolve_host(hostname)
    except Exception:
        raise ValueError("Host resolution failed")
    if not addresses:
        raise ValueError("No addresses resolved")
    for addr in addresses:
        _validate_public_address(addr)
    return addresses


def _validate_public_address(addr):
    # IPv4 validation
    if "." in addr and ":" not in addr:
        parts = addr.split(".")
        if len(parts) != 4:
            raise ValueError("Invalid IPv4 address")
        try:
            octets = [int(p) for p in parts]
        except ValueError:
            raise ValueError("Invalid IPv4 address")
        for o in octets:
            if not (0 <= o <= 255):
                raise ValueError("Invalid IPv4 address")
        # Reject loopback
        if octets[0] == 127:
            raise ValueError("Loopback address not allowed")
        # Reject link-local
        if octets[0] == 169 and octets[1] == 254:
            raise ValueError("Link-local address not allowed")
        # Reject private ranges
        if octets[0] == 10:
            raise ValueError("Private address not allowed")
        if octets[0] == 172 and 16 <= octets[1] <= 31:
            raise ValueError("Private address not allowed")
        if octets[0] == 192 and octets[1] == 168:
            raise ValueError("Private address not allowed")
        # Reject multicast
        if 224 <= octets[0] <= 239:
            raise ValueError("Multicast address not allowed")
        # Reject reserved/documentation
        if octets[0] == 192 and octets[1] == 0 and octets[2] == 2:
            raise ValueError("Documentation address not allowed")
        if octets[0] == 198 and octets[1] == 51 and octets[2] == 100:
            raise ValueError("Documentation address not allowed")
        if octets[0] == 203 and octets[1] == 0 and octets[2] == 113:
            raise ValueError("Documentation address not allowed")
        # Reject broadcast
        if all(o == 255 for o in octets):
            raise ValueError("Broadcast address not allowed")
        return
    # IPv6 validation
    if ":" in addr:
        # Handle zone index
        if "%" in addr:
            addr = addr.split("%")[0]
        # Handle IPv4-mapped
        if "." in addr:
            last_colon = addr.rfind(":")
            ipv4_part = addr[last_colon + 1:]
            _validate_public_address(ipv4_part)
            addr = addr[:last_colon + 1] + "0:0"
        # Expand :: notation
        if "::" in addr:
            if addr.count("::") > 1:
                raise ValueError("Invalid IPv6 address")
            parts = addr.split("::")
            left = parts[0].split(":") if parts[0] else []
            right = parts[1].split(":") if parts[1] else []
            missing = 8 - len(left) - len(right)
            if missing < 0:
                raise ValueError("Invalid IPv6 address")
            hextets = left + ["0"] * missing + right
        else:
            hextets = addr.split(":")
        if len(hextets) != 8:
            raise ValueError("Invalid IPv6 address")
        try:
            values = []
            for h in hextets:
                if len(h) > 4:
                    raise ValueError("Invalid IPv6 address")
                v = int(h, 16)
                values.append(v)
        except ValueError:
            raise ValueError("Invalid IPv6 address")
        for v in values:
            if not (0 <= v <= 0xFFFF):
                raise ValueError("Invalid IPv6 address")
        # Reject loopback
        if values == [0, 0, 0, 0, 0, 0, 0, 1]:
            raise ValueError("Loopback address not allowed")
        # Reject unspecified
        if all(v == 0 for v in values):
            raise ValueError("Unspecified address not allowed")
        # Reject IPv4-mapped loopback (already handled above but check IPv6 prefix)
        if values[0] == 0xFF02 or values[0] == 0xFF01:
            raise ValueError("Multicast address not allowed")
        # Reject site-local (deprecated but check)
        if values[0] == 0xFEC0:
            raise ValueError("Site-local address not allowed")
        # Reject unique local
        if (values[0] & 0xFE00) == 0xFC00:
            raise ValueError("Unique local address not allowed")
        # Reject link-local
        if (values[0] & 0xFFC0) == 0xFE80:
            raise ValueError("Link-local address not allowed")
        # Reject multicast
        if (values[0] & 0xFF00) == 0xFF00:
            raise ValueError("Multicast address not allowed")
        return
    raise ValueError("Unknown address format")


def _resolve_location(location, base_url):
    parsed_base = urllib.parse.urlparse(base_url)
    parsed_loc = urllib.parse.urlparse(location)
    # Handle relative URLs
    if not parsed_loc.scheme:
        # Relative URL
        if location.startswith("//"):
            # Protocol-relative
            resolved = urllib.parse.urlunparse((
                parsed_base.scheme,
                location[2:],
                "",
                "",
                "",
                ""
            ))
        elif location.startswith("/"):
            # Absolute path
            netloc = parsed_base.netloc
            if parsed_base.username is not None:
                # Strip credentials from base
                netloc = parsed_base.hostname
                if parsed_base.port:
                    netloc += ":" + str(parsed_base.port)
            resolved = urllib.parse.urlunparse((
                parsed_base.scheme,
                netloc,
                location,
                "",
                "",
                ""
            ))
        elif location.startswith("?"):
            # Query only
            resolved = urllib.parse.urlunparse((
                parsed_base.scheme,
                parsed_base.netloc,
                parsed_base.path,
                "",
                parsed_loc.query,
                ""
            ))
        elif location.startswith("#"):
            # Fragment only - treat as same URL
            resolved = base_url
        else:
            # Relative path
            base_path = parsed_base.path
            if "/" in base_path:
                base_path = base_path.rsplit("/", 1)[0] + "/"
            else:
                base_path = "/"
            new_path = urllib.parse.urljoin(base_path, location)
            netloc = parsed_base.netloc
            if parsed_base.username is not None:
                netloc = parsed_base.hostname
                if parsed_base.port:
                    netloc += ":" + str(parsed_base.port)
            resolved = urllib.parse.urlunparse((
                parsed_base.scheme,
                netloc,
                new_path,
                "",
                parsed_loc.query,
                ""
            ))
    else:
        resolved = location
    return resolved


def _strip_credentials(url):
    parsed = urllib.parse.urlparse(url)
    if parsed.username is not None or parsed.password is not None:
        netloc = parsed.hostname
        if parsed.port:
            netloc += ":" + str(parsed.port)
        url = urllib.parse.urlunparse((
            parsed.scheme,
            netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))
    return url


def fetch_text(url, transport, resolve_host):
    visited = set()
    current_url = _strip_credentials(url)
    for hop in range(_MAX_REDIRECTS + 1):
        # Validate scheme and port
        parsed = _validate_scheme_port(current_url)
        # Check for credential stripping consistency
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Credentials not allowed in URL")
        # Extract hostname
        hostname = parsed.hostname
        if not hostname:
            raise ValueError("No hostname in URL")
        # Validate resolved addresses
        _validate_host_addresses(hostname, resolve_host)
        # Prevent redirect loops
        normalized = urllib.parse.urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            "",
            parsed.query,
            ""
        ))
        if normalized in visited:
            raise ValueError("Redirect loop detected")
        visited.add(normalized)
        # Make transport call
        status, headers, body = transport(current_url)
        # Handle redirects
        if 300 <= status < 400:
            if hop >= _MAX_REDIRECTS:
                raise ValueError("Too many redirects")
            location = headers.get("Location") or headers.get("location")
            if not location:
                raise ValueError("Redirect without Location header")
            current_url = _resolve_location(location, current_url)
            current_url = _strip_credentials(current_url)
            continue
        # Final status check
        if status == 200:
            return body
        raise ValueError(f"Unexpected status: {status}")
    raise ValueError("Too many redirects")
