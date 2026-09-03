import os
import tarfile
from os.path import normpath, join, dirname, sep

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    # Step 1: Resolve dest_path to safe_dest
    try:
        safe_dest = os.path.abspath(os.path.realpath(dest_path))
        safe_dest = normpath(safe_dest)
        # Append platform path separator for strict prefix matching
        safe_dest_prefix = safe_dest + sep
    except (OSError, ValueError):
        return False

    # Helper to check if a path is within safe_dest
    def is_inside_safe(path: str) -> bool:
        norm = normpath(path)
        if norm == safe_dest:
            return True
        if norm.startswith(safe_dest_prefix):
            # Ensure true path boundary match
            next_char = norm[len(safe_dest_prefix) - 1] if len(norm) > len(safe_dest_prefix) - 1 else ''
            # safe_dest_prefix already ends with sep, so we check that prefix match is exact
            return True
        return False

    # Helper to sanitize member names
    def sanitize_name(name: str) -> str:
        # Strip leading path separators
        sanitized = name.lstrip(sep)
        # On Windows, strip any drive letter
        if os.name == 'nt':
            if len(sanitized) >= 2 and sanitized[1] == ':':
                sanitized = sanitized[2:].lstrip(sep)
        return sanitized

    # Step 2 & 3: Open archive and validate all members
    try:
        tar = tarfile.open(tar_path, 'r:*')
    except (tarfile.TarError, OSError, IOError):
        return False

    try:
        members = tar.getmembers()
    except (tarfile.TarError, OSError, IOError):
        tar.close()
        return False

    # Validation pass
    validated_manifest = {}  # Maps member to (extract_path, target_path_or_none, member_type)
    path_to_member = {}  # Maps extract_path to member info for hard link validation
    symlink_paths = set()  # Track which paths are symlinks

    for member in members:
        # Sanitize member name
        sanitized = sanitize_name(member.name)

        # Compute extract_path
        extract_path = normpath(join(safe_dest, sanitized))

        # Validate extract_path is inside safe_dest
        if not is_inside_safe(extract_path):
            tar.close()
            return False

        # Ensure true path boundary match for nested paths
        if extract_path != safe_dest and not extract_path.startswith(safe_dest_prefix):
            tar.close()
            return False

        # Determine member type
        if member.issym():
            # Symbolic link
            link_target = member.linkname
            # Resolve link target relative to parent directory of extract_path
            link_parent = dirname(extract_path)
            resolved_target = normpath(join(link_parent, link_target))
            # On Windows, also need to handle absolute link targets
            if os.name == 'nt' and len(link_target) >= 2 and link_target[1] == ':':
                # Absolute path on Windows - reject as it could be outside
                if not is_inside_safe(resolved_target):
                    tar.close()
                    return False
            elif link_target.startswith(sep) or (os.name == 'nt' and link_target.startswith('/')):
                # Unix absolute or Windows forward slash absolute
                resolved_target = normpath(join(safe_dest, sanitize_name(link_target)))
            
            if not is_inside_safe(resolved_target):
                tar.close()
                return False
            
            validated_manifest[member] = (extract_path, resolved_target, 'symlink')
            symlink_paths.add(extract_path)

        elif member.islnk():
            # Hard link
            sanitized_link_name = sanitize_name(member.linkname)
            target_path = normpath(join(safe_dest, sanitized_link_name))
            
            if not is_inside_safe(target_path):
                tar.close()
                return False
            
            # Check that referenced member is not a symbolic link
            # We need to check against validated paths
            target_is_symlink = False
            for info, (ep, tp, mt) in validated_manifest.items():
                if ep == target_path and mt == 'symlink':
                    target_is_symlink = True
                    break
            
            if target_is_symlink:
                tar.close()
                return False
            
            validated_manifest[member] = (extract_path, target_path, 'hardlink')

        elif member.isdir():
            validated_manifest[member] = (extract_path, None, 'dir')

        elif member.isfile() or member.isreg():
            validated_manifest[member] = (extract_path, None, 'file')

        else:
            # Reject device nodes, FIFOs, and other non-standard types
            tar.close()
            return False

        # Track path to member mapping
        path_to_member[extract_path] = validated_manifest[member]

    # Additional hard link validation: check target exists in archive and is not symlink
    for member, (extract_path, target_path, mtype) in validated_manifest.items():
        if mtype == 'hardlink':
            if target_path not in path_to_member:
                tar.close()
                return False
            target_info = path_to_member[target_path]
            if target_info[2] == 'symlink':
                tar.close()
                return False

    # Step 4: Extraction pass in dependency order
    # Order: directories first, then files, then symlinks, then hardlinks

    # Separate by type
    dirs = []
    files = []
    symlinks = []
    hardlinks = []

    for member, (extract_path, target_path, mtype) in validated_manifest.items():
        if mtype == 'dir':
            dirs.append((member, extract_path))
        elif mtype == 'file':
            files.append((member, extract_path))
        elif mtype == 'symlink':
            symlinks.append((member, extract_path, target_path))
        elif mtype == 'hardlink':
            hardlinks.append((member, extract_path, target_path))

    # Sort directories by depth (parent dirs first)
    dirs.sort(key=lambda x: x[1].count(sep))

    # Sort files by depth
    files.sort(key=lambda x: x[1].count(sep))

    # Track successfully written file paths for hard link validation
    written_files = set()

    try:
        # Create directories
        for member, extract_path in dirs:
            # Create parent directories if needed, using safe path creation
            parent = dirname(extract_path)
            if parent != safe_dest and not os.path.exists(parent):
                # Use os.makedirs with exist_ok, but we need to be careful about symlinks
                # Create directories safely
                _safe_makedirs(parent, safe_dest)
            
            if not os.path.exists(extract_path):
                os.mkdir(extract_path)
            written_files.add(extract_path)

        # Extract regular files
        for member, extract_path in files:
            # Create parent directories safely
            parent = dirname(extract_path)
            if parent != safe_dest and not os.path.exists(parent):
                _safe_makedirs(parent, safe_dest)
            
            # Extract file using tarfile extraction with safety
            # Use os.open with O_NOFOLLOW equivalent to avoid symlink following
            source = tar.extractfile(member)
            if source is None:
                tar.close()
                return False
            
            try:
                # Open file descriptor safely
                fd = _safe_open(extract_path, safe_dest)
                if fd < 0:
                    source.close()
                    tar.close()
                    return False
                
                try:
                    # Read and write in chunks
                    while True:
                        chunk = source.read(65536)
                        if not chunk:
                            break
                        os.write(fd, chunk)
                finally:
                    os.close(fd)
            finally:
                source.close()
            
            written_files.add(extract_path)

        # Create symbolic links
        for member, extract_path, target_path in symlinks:
            # Create parent directories safely
            parent = dirname(extract_path)
            if parent != safe_dest and not os.path.exists(parent):
                _safe_makedirs(parent, safe_dest)
            
            # Create symlink with pre-validated target
            # On Windows, may need os.symlink with target_is_directory
            try:
                if os.name == 'nt':
                    # Determine if target is directory for Windows symlink
                    is_dir_target = False
                    # Check if target path in manifest is a directory
                    for info, (ep, tp, mt) in validated_manifest.items():
                        if ep == target_path and mt == 'dir':
                            is_dir_target = True
                            break
                    os.symlink(target_path, extract_path, target_is_directory=is_dir_target)
                else:
                    os.symlink(target_path, extract_path)
            except (OSError, IOError):
                tar.close()
                return False
            
            written_files.add(extract_path)

        # Create hard links
        for member, extract_path, target_path in hardlinks:
            # Ensure target has been written
            if target_path not in written_files:
                tar.close()
                return False
            
            # Create parent directories safely
            parent = dirname(extract_path)
            if parent != safe_dest and not os.path.exists(parent):
                _safe_makedirs(parent, safe_dest)
            
            try:
                os.link(target_path, extract_path)
            except (OSError, IOError):
                tar.close()
                return False
            
            written_files.add(extract_path)

    except (OSError, IOError, tarfile.TarError):
        tar.close()
        return False

    tar.close()
    return True


def _safe_makedirs(path: str, safe_dest: str) -> None:
    """Create directories safely without following symlinks in path components."""
    # Build path component by component, checking each is not a symlink
    components = []
    current = path
    while current != safe_dest and len(current) > len(safe_dest):
        components.append(current)
        parent = dirname(current)
        if parent == current:
            break
        current = parent
    
    components.reverse()
    
    for component in components:
        # Check if any existing path component is a symlink
        check_path = safe_dest
        for part in component[len(safe_dest)+1:].split(sep):
            check_path = join(check_path, part)
            if os.path.islink(check_path):
                raise OSError("Symlink encountered in path creation")
            if not os.path.exists(check_path):
                os.mkdir(check_path)


def _safe_open(path: str, safe_dest: str) -> int:
    """Open a file safely without following symlinks, returning file descriptor."""
    # On Unix, use O_NOFOLLOW | O_CREAT | O_WRONLY | O_TRUNC
    # On Windows, use different approach
    
    if os.name == 'posix':
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW
        try:
            return os.open(path, flags, 0o666)
        except (OSError, IOError):
            # If parent doesn't exist, try creating it
            parent = dirname(path)
            if parent != safe_dest and not os.path.exists(parent):
                _safe_makedirs(parent, safe_dest)
            return os.open(path, flags, 0o666)
    else:
        # Windows: check path components for symlinks manually
        # Build path and check no component is a symlink
        relative = path[len(safe_dest)+1:] if path.startswith(safe_dest) else path
        check_path = safe_dest
        parts = relative.split(sep)
        
        # Check all but last component
        for part in parts[:-1]:
            check_path = join(check_path, part)
            if os.path.islink(check_path):
                raise OSError("Symlink encountered in path")
        
        # For the final file, check if it exists as symlink
        if os.path.islink(path):
            raise OSError("Symlink encountered at target path")
        
        # Use regular open on Windows
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        try:
            return os.open(path, flags, 0o666)
        except (OSError, IOError):
            parent = dirname(path)
            if parent != safe_dest and not os.path.exists(parent):
                _safe_makedirs(parent, safe_dest)
            return os.open(path, flags, 0o666)
