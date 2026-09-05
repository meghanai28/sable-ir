import os
import tarfile
import tempfile
import shutil

def _normalize_path(path: str) -> str:
    """Normalize a path to remove redundant separators and resolve . and .. if possible within the string."""
    return os.path.normpath(path)

def _is_inside_dest(dest: str, candidate: str) -> bool:
    """Check if candidate is inside dest, accounting for symlinks and relative components."""
    try:
        real_dest = os.path.realpath(dest)
        real_candidate = os.path.realpath(candidate)
        return real_candidate.startswith(real_dest + os.sep) or real_candidate == real_dest
    except (ValueError, OSError):
        return False

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory.
    
    Args:
        tar_path: Path to the tar archive.
        dest_path: Destination directory for extraction.
    
    Returns:
        True if extraction completes successfully, False otherwise.
        No files are written outside dest_path on failure.
    """
    try:
        # Normalize and validate dest_path
        dest_path = _normalize_path(dest_path)
        
        # Reject absolute paths
        if os.path.isabs(dest_path):
            raise ValueError("dest_path must be relative to the current working directory")
        
        # Create the destination directory if it doesn't exist
        os.makedirs(dest_path, exist_ok=True)
        
        # Resolve the real path of the destination to prevent escape via symlinks
        real_dest = os.path.realpath(dest_path)
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get all members before extracting
            members = tar.getmembers()
            
            # Validate each member before extraction
            for member in members:
                # Resolve the member's destination
                member_dest = os.path.join(dest_path, member.name)
                
                # Check for absolute paths in member names
                if os.path.isabs(member.name):
                    raise ValueError(f"Member name contains an absolute path: {member.name}")
                
                # Resolve the real path of the member destination
                # We need to resolve the link target if it's a symlink
                try:
                    if member.issym():
                        # Resolve the link target
                        link_target = os.path.join(dest_path, member.linkname)
                        # Normalize and resolve the link target
                        resolved_link = os.path.normpath(link_target)
                        # Ensure the resolved link is within the real destination
                        if not _is_inside_dest(real_dest, resolved_link):
                            raise ValueError(f"Symlink target escapes destination: {resolved_link}")
                    else:
                        # For regular files and directories, just check the normalized path
                        resolved_member = os.path.normpath(member_dest)
                        if not _is_inside_dest(real_dest, resolved_member):
                            raise ValueError(f"Member path escapes destination: {member.name}")
                except (ValueError, OSError) as e:
                    raise ValueError(f"Invalid path for member {member.name}: {e}")
            
            # Extract the archive
            tar.extractall(path=dest_path)
            
            return True
            
    except Exception as e:
        return False
