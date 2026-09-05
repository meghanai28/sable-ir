import os
import tarfile


def _normalize_path(path: str) -> str:
    """Normalize a path to remove redundant separators and resolve . and .. components."""
    return os.path.normpath(path)


def _is_within_root(child: str, root: str) -> bool:
    """Check if child path is within root directory."""
    try:
        return os.path.commonpath([child, root]) == root
    except ValueError:
        return False


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to the specified destination path.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory for extraction.
        
    Returns:
        True if extraction completes successfully, False otherwise.
        
    Raises:
        ValueError: If the destination path escapes the intended root.
    """
    # Normalize input paths
    tar_path = _normalize_path(tar_path)
    dest_path = _normalize_path(dest_path)
    
    # Ensure destination exists as a directory
    if not os.path.isdir(dest_path):
        os.makedirs(dest_path, exist_ok=True)
    
    # Verify destination does not escape itself (e.g., if dest_path has ..)
    # After normalization, dest_path should be safe, but we double-check the resolved path
    resolved_dest = os.path.abspath(dest_path)
    
    # Validate tar_path exists
    if not os.path.isfile(tar_path):
        return False
    
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get the list of all members
            members = tar.getnames()
            
            # Validate each member before extraction
            for member in members:
                # Resolve the member's destination relative to dest_path
                member_path = os.path.join(dest_path, member)
                
                # Check if the member path escapes the root
                if not _is_within_root(member_path, resolved_dest):
                    raise ValueError(f"Member {member} would escape the destination root")
                
                # Check for .. in the member name itself (before joining)
                # This handles cases where the archive itself contains .. in names
                if '..' in member:
                    raise ValueError(f"Member {member} contains '..' which could escape root")
            
            # Extract the archive
            tar.extractall(path=dest_path)
            
            # Final safety check: verify no files were written outside dest_path
            # by checking if any created file is outside the intended root
            for root_dir, dirs, files in os.walk(dest_path):
                for file in files:
                    file_path = os.path.join(root_dir, file)
                    if not _is_within_root(file_path, resolved_dest):
                        raise ValueError(f"Extracted file {file_path} is outside destination root")
                        
                # Remove directories that are not under dest_path (though extractall usually respects this)
                # We ensure we don't leave stray directories
                for d in dirs:
                    dir_path = os.path.join(root_dir, d)
                    if not _is_within_root(dir_path, resolved_dest):
                        try:
                            os.rmdir(dir_path)
                        except OSError:
                            pass
            
            return True
            
    except Exception:
        return False
