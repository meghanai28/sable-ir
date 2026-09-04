import os
import tarfile
from typing import Optional


def _resolve_path(path: str, dest_path: str) -> Optional[str]:
    """Normalize path and return absolute path if under dest_path, else None."""
    try:
        abs_dest = os.path.abspath(os.path.realpath(dest_path))
        # Use realpath to resolve any symlinks in the path itself
        abs_path = os.path.abspath(os.path.realpath(path))
        # Check if path is within dest_path
        if os.path.commonpath([abs_path, abs_dest]) != abs_dest:
            return None
        return abs_path
    except (ValueError, OSError):
        return None


def _resolve_link_target(link_target: str, dest_path: str, member_dir: str) -> Optional[str]:
    """Resolve a symlink/hardlink target relative to member's directory, ensure it stays under dest_path."""
    try:
        abs_dest = os.path.abspath(os.path.realpath(dest_path))
        # Join with the directory containing the link
        full_target = os.path.join(member_dir, link_target)
        # Normalize: resolve .. etc. Don't follow symlinks here (that's checked at creation time)
        abs_target = os.path.abspath(os.path.normpath(full_target))
        # Check if target is within dest_path
        if os.path.commonpath([abs_target, abs_dest]) != abs_dest:
            return None
        return abs_target
    except (ValueError, OSError):
        return None


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    # Validate dest_path exists and is a directory
    if not os.path.isdir(dest_path):
        return False
    
    abs_dest = os.path.abspath(os.path.realpath(dest_path))
    
    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
            
            # First pass: validate all member paths and link targets
            validated_members = []
            for member in members:
                # Determine the intended extraction path for this member
                member_path = os.path.join(dest_path, member.name)
                resolved_member = _resolve_path(member_path, dest_path)
                
                if resolved_member is None:
                    return False
                
                # For symlinks and hardlinks, validate the link target
                if member.issym() or member.islnk():
                    # Get the directory containing this member
                    member_dir = os.path.dirname(resolved_member)
                    target = member.linkname
                    
                    # Resolve target relative to member's directory
                    resolved_target = _resolve_link_target(target, dest_path, member_dir)
                    
                    if resolved_target is None:
                        return False
                    
                    # Additional check: for symlinks, also verify the link target itself
                    # doesn't escape when fully resolved (including following symlinks)
                    # We check what the target would resolve to if created
                    if member.issym():
                        # Check if the normalized target path stays within dest
                        # The target string itself might contain .. sequences
                        if os.path.isabs(target):
                            # Absolute symlink target: must be under dest
                            abs_target = _resolve_path(target, dest_path)
                            if abs_target is None:
                                return False
                        # else relative target was already checked above
                
                validated_members.append((member, resolved_member))
            
            # Second pass: extract all members
            for member, resolved_member in validated_members:
                # Extract to a temporary location or use extractfile then write manually
                # to ensure we control the exact path
                
                if member.isdir():
                    os.makedirs(resolved_member, exist_ok=True)
                    # Set mode if needed
                    try:
                        os.chmod(resolved_member, member.mode)
                    except OSError:
                        pass
                    
                elif member.isfile():
                    # Ensure parent directory exists
                    parent = os.path.dirname(resolved_member)
                    os.makedirs(parent, exist_ok=True)
                    
                    # Extract file content
                    with tf.extractfile(member) as fsrc:
                        if fsrc is None:
                            return False
                        with open(resolved_member, 'wb') as fdst:
                            while True:
                                chunk = fsrc.read(65536)
                                if not chunk:
                                    break
                                fdst.write(chunk)
                    
                    # Set permissions
                    try:
                        os.chmod(resolved_member, member.mode)
                    except OSError:
                        pass
                    
                elif member.issym():
                    # Ensure parent directory exists
                    parent = os.path.dirname(resolved_member)
                    os.makedirs(parent, exist_ok=True)
                    
                    # Create symlink
                    target = member.linkname
                    try:
                        os.symlink(target, resolved_member)
                    except OSError:
                        return False
                    
                elif member.islnk():
                    # Hard link: target must exist (will be created in order or already exists)
                    # Find the resolved target path
                    target_name = member.linkname
                    # The link target in tar is relative to archive root
                    target_path = os.path.join(dest_path, target_name)
                    resolved_target = _resolve_path(target_path, dest_path)
                    
                    if resolved_target is None:
                        return False
                    
                    # Ensure parent directory exists
                    parent = os.path.dirname(resolved_member)
                    os.makedirs(parent, exist_ok=True)
                    
                    # Create hard link
                    try:
                        os.link(resolved_target, resolved_member)
                    except OSError:
                        # Target might not exist yet; tar archives usually order properly
                        # but we need to handle this - try to find if target was already extracted
                        return False
                    
                else:
                    # Skip other types (FIFO, device, etc.) for safety
                    pass
            
            return True
            
    except (tarfile.TarError, OSError, IOError):
        return False
