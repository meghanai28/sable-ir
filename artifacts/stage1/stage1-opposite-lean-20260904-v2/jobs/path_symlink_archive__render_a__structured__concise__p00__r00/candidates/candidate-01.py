import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_path = os.path.realpath(os.path.abspath(dest_path))
    except (OSError, ValueError):
        return False

    if not os.path.isdir(dest_path):
        return False

    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
            
            # Pre-validate all members
            validated_members = []
            for member in members:
                # Validate member name/path
                member_path = _validate_member_path(member.name, dest_path)
                if member_path is None:
                    return False
                
                # Validate link targets if present
                if member.issym() or member.islnk():
                    target = member.linkname
                    if target is None:
                        return False
                    
                    # For symlinks, resolve target relative to the symlink's directory
                    if member.issym():
                        symlink_dir = os.path.dirname(member_path)
                        resolved_target = _resolve_link_target(target, symlink_dir, dest_path)
                    else:
                        # For hard links, target is another archive member
                        resolved_target = _validate_member_path(target, dest_path)
                    
                    if resolved_target is None:
                        return False
                
                validated_members.append((member, member_path))
            
            # All validation passed, now extract
            for member, member_path in validated_members:
                if member.issym() or member.islnk():
                    target = member.linkname
                    if member.issym():
                        symlink_dir = os.path.dirname(member_path)
                        resolved_target = _resolve_link_target(target, symlink_dir, dest_path)
                    else:
                        resolved_target = _validate_member_path(target, dest_path)
                    
                    # Create the symlink/hardlink directly
                    if member.issym():
                        os.symlink(target, member_path)
                    else:
                        # Hard link: need to ensure target exists first
                        # Since we process in order, target should exist if it's earlier in archive
                        # But tarfile extraction handles ordering, so we use extract for hard links
                        tf.extract(member, path=dest_path, set_attrs=False)
                        continue
                elif member.isdir():
                    os.makedirs(member_path, exist_ok=True)
                elif member.isfile():
                    # Ensure parent directory exists
                    parent_dir = os.path.dirname(member_path)
                    if parent_dir:
                        os.makedirs(parent_dir, exist_ok=True)
                    
                    # Extract file using tarfile to handle file content
                    with tf.extractfile(member) as fobj:
                        if fobj is None:
                            return False
                        with open(member_path, 'wb') as outfile:
                            outfile.write(fobj.read())
                    
                    # Set permissions if available
                    if member.mode is not None:
                        os.chmod(member_path, member.mode)
                else:
                    # Skip other types (fifo, device, etc.)
                    return False
            
            return True
            
    except (tarfile.TarError, OSError, IOError, ValueError):
        return False


def _validate_member_path(name: str, dest_path: str) -> str | None:
    if not name:
        return None
    
    # Reject absolute paths
    if os.path.isabs(name):
        return None
    
    # Reject explicit .. components
    parts = name.replace('\\', '/').split('/')
    for part in parts:
        if part == '..':
            return None
    
    # Normalize and check it's under dest_path
    try:
        full_path = os.path.realpath(os.path.join(dest_path, name))
    except (OSError, ValueError):
        return None
    
    # Ensure it's within dest_path
    try:
        os.path.relpath(full_path, dest_path)
    except ValueError:
        return None
    
    if not full_path.startswith(dest_path + os.sep) and full_path != dest_path:
        return None
    
    return full_path


def _resolve_link_target(target: str, symlink_dir: str, dest_path: str) -> str | None:
    if target is None:
        return None
    
    # Reject absolute paths that escape (absolute paths are always suspect)
    if os.path.isabs(target):
        # On some systems, absolute symlinks might be restricted
        # Normalize and check
        try:
            resolved = os.path.realpath(target)
        except (OSError, ValueError):
            return None
        
        # Only allow if it resolves within dest_path
        try:
            rel = os.path.relpath(resolved, dest_path)
        except ValueError:
            return None
        
        if rel.startswith('..'):
            return None
        
        if not resolved.startswith(dest_path + os.sep) and resolved != dest_path:
            return None
        
        return resolved
    
    # Relative target: resolve relative to symlink directory
    try:
        resolved = os.path.realpath(os.path.join(symlink_dir, target))
    except (OSError, ValueError):
        return None
    
    # Check for .. escape
    try:
        rel = os.path.relpath(resolved, dest_path)
    except ValueError:
        return None
    
    if rel.startswith('..'):
        return None
    
    if not resolved.startswith(dest_path + os.sep) and resolved != dest_path:
        return None
    
    return resolved
