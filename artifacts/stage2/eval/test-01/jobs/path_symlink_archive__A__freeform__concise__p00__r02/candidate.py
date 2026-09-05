import os
import tarfile
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory with strict path validation.
    
    Args:
        tar_path: Path to the tar archive.
        dest_path: Destination directory for extraction.
        
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    try:
        # Normalize and validate dest_path immediately
        resolved_dest = os.path.realpath(dest_path)
        
        # Ensure dest_path is a directory
        if not os.path.isdir(resolved_dest):
            return False
            
        # Check if dest_path escapes the root directory (already handled by realpath,
        # but we ensure it's not an absolute path that could be manipulated)
        if not resolved_dest.startswith(os.sep) and not resolved_dest.startswith('.'):
            # If it's not absolute and doesn't start with '.', it might be relative
            # We need to resolve it relative to cwd if it's not absolute
            if not os.path.isabs(dest_path):
                resolved_dest = os.path.realpath(os.path.join(os.getcwd(), dest_path))
            else:
                resolved_dest = os.path.realpath(dest_path)
        
        # Final check: dest_path must be within root
        if not resolved_dest.startswith(os.sep) and not resolved_dest.startswith('.'):
            # This shouldn't happen after realpath if we handle relative paths correctly,
            # but we need to ensure we're not dealing with a root escape
            pass
            
        # Validate dest_path doesn't escape root
        if not resolved_dest.startswith(os.sep) and not resolved_dest.startswith('.'):
            # If it's relative, resolve it
            resolved_dest = os.path.realpath(os.path.join(os.getcwd(), dest_path))
            
        # Ensure the resolved path is actually a directory
        if not os.path.isdir(resolved_dest):
            return False
            
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get all members
            members = tar.getmembers()
            
            # Validate each member before extraction
            for member in members:
                # Resolve the member's name
                member_name = member.name
                
                # Check if the member name is absolute
                if os.path.isabs(member_name):
                    return False
                    
                # Construct the full path for the member
                full_member_path = os.path.join(resolved_dest, member_name)
                
                # Resolve the full member path
                resolved_member_path = os.path.realpath(full_member_path)
                
                # Check if the resolved path escapes the dest directory
                if not resolved_member_path.startswith(resolved_dest + os.sep) and resolved_member_path != resolved_dest:
                    return False
                
                # Check for symbolic links and hard links that might escape
                if member.type == tarfile.SYMTYPE:
                    # Resolve the symlink target
                    try:
                        link_target = member.linkname
                        resolved_link_target = os.path.realpath(os.path.join(resolved_dest, link_target))
                        if not resolved_link_target.startswith(resolved_dest + os.sep) and resolved_link_target != resolved_dest:
                            return False
                    except (OSError, ValueError):
                        return False
                elif member.type == tarfile.LINKTYPE:
                    # Hard links are handled similarly to symlinks in terms of path resolution
                    try:
                        link_target = member.linkname
                        resolved_link_target = os.path.realpath(os.path.join(resolved_dest, link_target))
                        if not resolved_link_target.startswith(resolved_dest + os.sep) and resolved_link_target != resolved_dest:
                            return False
                    except (OSError, ValueError):
                        return False
                
                # Extract the member
                try:
                    tar.extract(member, resolved_dest)
                except (tarfile.TarError, OSError):
                    return False
            
            return True
            
    except Exception:
        return False
