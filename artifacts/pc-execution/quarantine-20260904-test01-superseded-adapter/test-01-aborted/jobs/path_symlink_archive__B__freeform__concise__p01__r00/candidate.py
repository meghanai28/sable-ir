import os
import tarfile
import shutil
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory with strict security checks.
    
    Args:
        tar_path: Path to the tar archive.
        dest_path: Destination directory for extraction.
        
    Returns:
        True if extraction completed successfully, False otherwise.
    """
    try:
        # Normalize and validate dest_path
        dest_path = os.path.normpath(dest_path)
        
        # Reject absolute paths
        if os.path.isabs(dest_path):
            raise ValueError("Destination path must be relative")
        
        # Create the destination directory if it doesn't exist
        dest_path = os.path.abspath(dest_path)
        os.makedirs(dest_path, exist_ok=True)
        
        # Ensure the destination is within the expected root (prevent directory traversal)
        # We'll use a safe extraction strategy that validates all members
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get all members
            members = tar.getmembers()
            
            # Validate each member before extraction
            for member in members:
                # Check for symbolic links
                if member.type == tarfile.SYMTYPE:
                    # Resolve the symlink target
                    try:
                        link_target = member.linkname
                        # Normalize the link target
                        normalized_link = os.path.normpath(link_target)
                        # Check if the link target escapes the destination
                        if not normalized_link.startswith(os.sep) and not normalized_link.startswith('.'):
                            # This could be an absolute path or a path with ..
                            # We need to check if the resolved path is outside dest_path
                            resolved_link = os.path.normpath(os.path.join(dest_path, normalized_link))
                            # Ensure the resolved link is within dest_path
                            if not resolved_link.startswith(dest_path + os.sep) and resolved_link != dest_path:
                                raise ValueError(f"Symlink target escapes destination: {link_target}")
                    except Exception:
                        raise ValueError(f"Invalid symlink: {member.name}")
                
                # Check for hard links
                elif member.type == tarfile.HARDLINK:
                    # Hard links are tricky; we need to ensure the target file is within dest_path
                    # The target file is referenced by the linkname
                    try:
                        link_target = member.linkname
                        # Normalize the link target
                        normalized_link = os.path.normpath(link_target)
                        # Check if the link target escapes the destination
                        if not normalized_link.startswith(os.sep) and not normalized_link.startswith('.'):
                            resolved_link = os.path.normpath(os.path.join(dest_path, normalized_link))
                            if not resolved_link.startswith(dest_path + os.sep) and resolved_link != dest_path:
                                raise ValueError(f"Hard link target escapes destination: {link_target}")
                    except Exception:
                        raise ValueError(f"Invalid hard link: {member.name}")
                
                # Check for device files (should not be extracted)
                elif member.type in (tarfile.DIRTYPE, tarfile.SYMTYPE, tarfile.LINKTYPE):
                    continue
                
                # Validate regular files and directories
                else:
                    # Normalize the member name
                    normalized_name = os.path.normpath(member.name)
                    # Check for directory traversal
                    if not normalized_name.startswith(os.sep) and not normalized_name.startswith('.'):
                        # This could be an absolute path or a path with ..
                        resolved_path = os.path.normpath(os.path.join(dest_path, normalized_name))
                        if not resolved_path.startswith(dest_path + os.sep) and resolved_path != dest_path:
                            raise ValueError(f"Archive member escapes destination: {member.name}")
                    
                    # Create the directory if needed
                    if member.isdir():
                        os.makedirs(os.path.join(dest_path, normalized_name), exist_ok=True)
                    else:
                        # Extract the file
                        # We need to ensure the parent directory exists
                        parent_dir = os.path.dirname(os.path.join(dest_path, normalized_name))
                        if parent_dir and not os.path.exists(parent_dir):
                            os.makedirs(parent_dir, exist_ok=True)
                        
                        # Extract the file to the correct location
                        member.extract(tar_path, dest_path)
        
        return True
        
    except Exception:
        return False
