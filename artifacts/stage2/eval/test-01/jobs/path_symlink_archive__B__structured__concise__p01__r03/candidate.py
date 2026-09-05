import os
import tarfile
import shutil
import tempfile


def _normalize_path(path: str) -> str:
    """Normalize a path to an absolute path, resolving .. and . components."""
    return os.path.normpath(os.path.abspath(path))


def _is_safe_path(base: str, target: str) -> bool:
    """Check if target is safely within base directory."""
    try:
        return target.startswith(os.path.normpath(base) + os.sep) or target == os.path.normpath(base)
    except (ValueError, TypeError):
        return False


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to the specified destination path.
    
    Returns True if extraction completes successfully, False otherwise.
    No archive members are written outside dest_path if validation fails.
    """
    # Normalize paths immediately to prevent path traversal attacks
    normalized_tar = _normalize_path(tar_path)
    normalized_dest = _normalize_path(dest_path)
    
    # Validate tar_path exists and is a file
    if not os.path.isfile(normalized_tar):
        return False
    
    # Validate dest_path is a directory
    if not os.path.isdir(normalized_dest):
        return False
    
    # Create a temporary directory for safe extraction
    with tempfile.TemporaryDirectory() as temp_extract_dir:
        try:
            # Open the tar file
            with tarfile.open(normalized_tar, 'r:*') as tar:
                # Get list of members before extraction
                members = tar.getnames()
                
                # Validate each member to ensure no path traversal
                for member in members:
                    # Resolve the member's path relative to the temporary directory
                    # This simulates where the file would be extracted
                    target_path = os.path.normpath(os.path.join(temp_extract_dir, member))
                    
                    # Check if the target escapes the temporary directory
                    if not _is_safe_path(temp_extract_dir, target_path):
                        return False
                
                # Extract the archive to the temporary directory
                tar.extractall(temp_extract_dir)
                
                # Now move the extracted files to the destination
                # We need to be careful with symlinks and directory structures
                for root, dirs, files in os.walk(temp_extract_dir):
                    # Remove the temporary directory tree
                    shutil.rmtree(root, ignore_errors=True)
                    
                    # Create corresponding directories in destination
                    rel_path = os.path.relpath(root, temp_extract_dir)
                    dest_dir = os.path.join(normalized_dest, rel_path)
                    os.makedirs(dest_dir, exist_ok=True)
                    
                    # Copy files
                    for file in files:
                        src_file = os.path.join(root, file)
                        dst_file = os.path.join(dest_dir, file)
                        
                        # Handle symlinks
                        if os.path.islink(src_file):
                            link_target = os.readlink(src_file)
                            # Resolve the link target relative to the source file's directory
                            # to prevent path traversal via symlinks
                            link_target_resolved = os.path.normpath(os.path.join(os.path.dirname(src_file), link_target))
                            # Check if the resolved link target escapes the destination
                            if not _is_safe_path(normalized_dest, link_target_resolved):
                                return False
                            # Create the symlink in destination
                            os.symlink(link_target_resolved, dst_file)
                        else:
                            # Copy the file
                            shutil.copy2(src_file, dst_file)
                
                # Clean up the temporary directory
                shutil.rmtree(temp_extract_dir, ignore_errors=True)
                
                return True
                
        except (tarfile.TarError, IOError, OSError):
            return False
